from __future__ import annotations
from .dsl import evaluate_expression
from .curves import lookup_curve, CurveRepository
from .units import Quantity
from .plugins import PluginRegistry
from .errors import RuleEngineError, EvaluationError

class RuleExecutor:
    def __init__(self, plugins: PluginRegistry | None=None, curves: CurveRepository | None=None):
        self.plugins=plugins or PluginRegistry(); self.curves=curves or CurveRepository()

    def execute(self, rule: dict, inputs: dict) -> dict:
        rid=rule.get("rule_id","UNSPECIFIED")
        try:
            values=_normalize_inputs(rule,inputs)
            pre=rule.get("preconditions")
            if pre and evaluate_expression(pre,values) is not True:
                return {"rule_id":rid,"status":"skipped","result":None,"error_code":"PRECONDITION_NOT_MET"}
            kind=rule.get("rule_type")
            if kind in ("expression","declarative_expr"):
                result=evaluate_expression(rule["expression"],values)
                if not isinstance(result,bool): raise EvaluationError("Expression rule must return boolean")
                return {"rule_id":rid,"status":"pass" if result else "fail","result":result,"error_code":None}
            if kind=="lookup_curve":
                cfg=rule.get("curve",{})
                if cfg:
                    x=_quantity(values[cfg["input"]]); pts=[(_quantity(p[0]),_quantity(p[1])) for p in cfg["points"]]
                    y=lookup_curve(x,pts,extrapolation=cfg.get("extrapolation","error"))
                    return {"rule_id":rid,"status":"pass","result":{"value":y.value,"dimension":y.dimension,"unit":y.display_unit},"error_code":None}
                cfg=rule["curve_eval"]
                extra={"safety_margin_ratio":Quantity.of(cfg.get("safety_margin_ratio",1),"ratio")}
                if cfg.get("temp_derating_factor"):
                    extra["temp_derating_factor"]=evaluate_expression(cfg["temp_derating_factor"],{**values,**extra})
                def lookup(table_id,x,y):
                    return self.curves.lookup_max_id(table_id,x,y,out_of_bounds=cfg.get("curve_out_of_bounds","error"))
                result=evaluate_expression(cfg["expression"],{**values,**extra},{"lookup_max_id":lookup})
                if not isinstance(result,bool): raise EvaluationError("Curve envelope expression must return boolean")
                return {"rule_id":rid,"status":"pass" if result else "fail","result":result,"error_code":None}
            if kind=="script_plugin":
                pref=rule["plugin_ref"]
                plugin_id=(pref.get("module","")+"::"+pref.get("entry_func","")) if isinstance(pref,dict) else str(pref)
                payload={k:_json_value(v) for k,v in values.items()}
                if isinstance(pref,dict): payload["plugin_params"]=pref.get("params",{})
                result=self.plugins.execute(plugin_id,payload)
                exposed=rule.get("outputs_exposed",[])
                missing=[name for name in exposed if name not in result]
                if missing: raise EvaluationError(f"PLUGIN_OUTPUT_MISSING: {missing}",code="PLUGIN_OUTPUT_MISSING")
                plugin_status=result.get("status","pass")
                if plugin_status not in ("pass","fail"): raise EvaluationError("PLUGIN_INVALID_STATUS",code="PLUGIN_INVALID_STATUS")
                return {"rule_id":rid,"status":plugin_status,"result":result,"error_code":None}
            raise EvaluationError(f"Unsupported rule_type: {kind}")
        except RuleEngineError as e:
            return {"rule_id":rid,"status":"error","result":None,"error_code":e.code,"message":str(e)}
        except KeyError as e:
            return {"rule_id":rid,"status":"error","result":None,"error_code":"INPUT_MISSING","message":f"Missing field: {e}"}

def _normalize_inputs(rule, values):
    declared=rule.get("inputs",[])
    specs={x.get("name"):x for x in declared if isinstance(x,dict) and x.get("name")}
    out={}
    for name,value in values.items():
        spec=specs.get(name,{})
        unit=spec.get("unit")
        if isinstance(value,dict) and "value" in value:
            out[name]=Quantity.of(value["value"],value.get("unit",unit or "1"))
        elif unit and unit!="table" and isinstance(value,(int,float)) and not isinstance(value,bool):
            out[name]=Quantity.of(value,unit)
        else: out[name]=value
    return out

def _quantity(v):
    if isinstance(v,Quantity): return v
    if isinstance(v,dict) and "value" in v: return Quantity.of(v["value"],v.get("unit","1"))
    if isinstance(v,(int,float)) and not isinstance(v,bool): return Quantity.of(v)
    raise EvaluationError("Expected numeric quantity")
def _json_value(v):
    if isinstance(v,Quantity): return {"value":v.value,"dimension":v.dimension,"unit":"SI"}
    return v
