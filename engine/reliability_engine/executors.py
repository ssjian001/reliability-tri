"""三类执行器（01 §3.1）：declarative_expr / lookup_curve / script_plugin。
统一入口 run_rule(rule, inputs) → Finding 数据（execution_status + 判定 + 计算过程）。
状态机优先级（01 §7.1）：DATA_GAP > NOT_APPLICABLE > SKIPPED_PRECONDITION > CONFLICT_UNRESOLVED > PASS/FAIL。
"""
from __future__ import annotations

import importlib
import json
import math
import pathlib
import re

from .dsl import DSLEvaluator, validate as dsl_validate
from .measured import MeasuredParam, from_dict
from .units import UnitEngine, UnitError

EXEC_DECL = "declarative_expr"
EXEC_CURVE = "lookup_curve"
EXEC_PLUGIN = "script_plugin"
RULE_TYPES = {EXEC_DECL, EXEC_CURVE, EXEC_PLUGIN}

STATUS_PASS, STATUS_FAIL = "PASS", "FAIL"
STATUS_GAP, STATUS_NA = "DATA_GAP", "NOT_APPLICABLE"
STATUS_SKIP, STATUS_CONFLICT, STATUS_ERROR = "SKIPPED_PRECONDITION", "CONFLICT_UNRESOLVED", "ERROR"


class _ExprEnv(dict):
    """缺变量返回 NaN 哨兵：让求值先完成，状态机再判 DATA_GAP。"""
    def __missing__(self, key):
        return float("nan")


def _expr_ok(expr: str, variables: list[str]) -> str | None:
    try:
        dsl_validate(expr, variables)
        return None
    except ValueError as e:
        return str(e)


def eval_preconditions(rule: dict, values: dict[str, float], evaluator: DSLEvaluator):
    """返回 (status|None, notes)。preconditions: [{expr, on_fail}]。"""
    notes = []
    for pre in rule.get("preconditions") or []:
        expr, on_fail = pre["expr"], pre.get("on_fail", STATUS_SKIP)
        try:
            ok = evaluator.with_values(values).evaluate(expr, list(values))
        except Exception as e:
            return STATUS_GAP, notes + [f"precondition 求值失败: {e}"]
        if not ok:
            return on_fail, notes + [f"precondition 不满足: {expr}"]
    return None, notes


def run_declarative(rule: dict, engine: UnitEngine, inputs: dict, unit_dim: dict) -> dict:
    variables = [i["name"] for i in rule.get("inputs", [])]
    expr = rule["expression"]
    try:
        dsl_validate(expr, variables)
    except ValueError as e:
        return {"execution_status": STATUS_ERROR, "reasons": [f"DSL 违规: {e}"], "info": {}}
    values, missing = {}, []
    for spec in rule.get("inputs", []):
        name = spec["name"]
        mp = inputs.get(name)
        if mp is None:
            missing.append(name); continue
        values[name] = mp.decl(spec["unit"]).decl_value  # 声明单位口径（表达式常量同口径）
    if missing:
        return {"execution_status": STATUS_GAP, "reasons": [f"缺失输入: {', '.join(missing)}"], "info": {}}
    ev = DSLEvaluator(values)
    status, pre_notes = eval_preconditions(rule, values, ev)
    if status:
        return {"execution_status": status, "reasons": pre_notes, "info": {}}
    try:
        result = ev.evaluate(expr, variables)
    except ZeroDivisionError:
        return {"execution_status": STATUS_ERROR, "reasons": ["DIV_BY_ZERO"], "info": {}}
    except Exception as e:
        return {"execution_status": STATUS_ERROR, "reasons": [f"求值异常: {e}"], "info": {}}
    verdict = bool(result)
    margins = {}
    for tname, tspec in (rule.get("thresholds") or {}).items():
        if "variants" in tspec:
            margins[tname] = {"variants": tspec["variants"], "source_ref": tspec.get("source_ref")}
        else:
            margins[tname] = tspec
    return {"execution_status": STATUS_PASS if verdict else STATUS_FAIL,
            "reasons": pre_notes, "info": {"result": result, "thresholds": margins}}


def _log_log_linear(table: list[dict], x_key: str, y_key: str, target_x: float, x_value: float) -> float:
    """双对数线性插值：在 (log x_key, log y_key) 空间插值出 target_x 对应的 y。
    table 行形如 {x_key: v, y_key: v}。越界（out of table）抛 ValueError（curve_out_of_bounds=error）。"""
    pts = []
    for row in table:
        try:
            pts.append((float(row[x_key]), float(row[y_key])))
        except (KeyError, TypeError, ValueError):
            continue
    if not pts:
        raise ValueError("曲线表为空或字段不匹配")
    pts.sort()
    xs = [p[0] for p in pts]
    tx = math.log10(target_x) if target_x > 0 else None
    if tx is None or tx < math.log10(min(xs)) - 1e-12 or tx > math.log10(max(xs)) + 1e-12:
        raise ValueError(f"目标 x={target_x} 超出曲线范围 [{min(xs)}, {max(xs)}]")
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]; x1, y1 = pts[i + 1]
        if x0 <= target_x <= x1 and x1 > x0:
            lx0, lx1, ltx = math.log10(x0), math.log10(x1), math.log10(target_x)
            ly = math.log10(y0) + (math.log10(y1) - math.log10(y0)) * (ltx - lx0) / (lx1 - lx0)
            return 10 ** ly
    return pts[-1][1]


def run_lookup_curve(rule: dict, engine: UnitEngine, inputs: dict, unit_dim: dict) -> dict:
    variables = [i["name"] for i in rule.get("inputs", [])]
    values, missing = {}, []
    for spec in rule.get("inputs", []):
        name = spec["name"]
        mp = inputs.get(name)
        if mp is None:
            missing.append(name); continue
        if spec.get("unit") == "table" or unit_dim.get(name) == "table":
            values[name] = mp.raw_value  # table 原样传递
        else:
            values[name] = mp.decl(spec["unit"]).decl_value  # 声明单位口径
    if missing:
        return {"execution_status": STATUS_GAP, "reasons": [f"缺失输入: {', '.join(missing)}"], "info": {}}
    ev = DSLEvaluator(values)
    status, pre_notes = eval_preconditions(rule, values, ev)
    if status:
        return {"execution_status": status, "reasons": pre_notes, "info": {}}
    ce = rule["curve_eval"]
    table_name = next((v for v in variables if v.startswith("soa") or "table" in v), variables[-1])
    table = values.get(table_name)
    if not isinstance(table, list):
        return {"execution_status": STATUS_ERROR, "reasons": [f"曲线表 {table_name} 不是列表"], "info": {}}
    try:
        limit_id = _log_log_linear(table, "pulse_width_ms", "max_id", values["pulse_width_ms"], values["peak_vds"])
    except ValueError as e:
        return {"execution_status": STATUS_ERROR, "reasons": [f"曲线越界: {e}"], "info": {}}
    dt = values["case_temp"] - ce["temp_derating_delta_ref_c"]
    factor = 1 - dt / ce["temp_derating_delta_max_c"]
    margin = ce["safety_margin_ratio"]
    limit = limit_id * factor * margin
    verdict = values["peak_id"] <= limit
    return {"execution_status": STATUS_PASS if verdict else STATUS_FAIL,
            "reasons": pre_notes,
            "info": {"soa_limit_id_raw": limit_id, "temp_factor": factor, "safety_margin": margin,
                     "limit_id_after": limit, "peak_id": values["peak_id"]}}


PLUGIN_REGISTRY: dict[str, dict] = {}


def register_plugin(module: str, entry_func: str, func, version: str, digest: str):
    """受控注册表：只允许显式注册的白名单插件（01 §3.1）。"""
    PLUGIN_REGISTRY[f"{module}.{entry_func}"] = {
        "func": func, "version": version, "digest": digest,
    }


def run_script_plugin(rule: dict, engine: UnitEngine, inputs: dict, unit_dim: dict) -> dict:
    ref = rule["plugin_ref"]
    key = f"{ref['module']}.{ref['entry_func']}"
    reg = PLUGIN_REGISTRY.get(key)
    if reg is None:
        return {"execution_status": STATUS_ERROR,
                "reasons": [f"插件未注册: {key}（白名单外禁止动态导入）"], "info": {}}
    values, missing = {}, []
    for spec in rule.get("inputs", []):
        name = spec["name"]
        mp = inputs.get(name)
        if mp is None:
            missing.append(name); continue
        values[name] = mp.decl(spec["unit"]).decl_value  # 声明单位口径（插件按模板语义消费 °C/h/A）
    if missing:
        return {"execution_status": STATUS_GAP, "reasons": [f"缺失输入: {', '.join(missing)}"], "info": {}}
    ev = DSLEvaluator(values)
    status, pre_notes = eval_preconditions(rule, values, ev)
    if status:
        return {"execution_status": status, "reasons": pre_notes, "info": {}}
    params = {}
    for k, v in (ref.get("params") or {}).items():
        if isinstance(v, dict) and "value" in v:
            params[k] = v["value"]
        else:
            params[k] = v
    outputs_spec = {o["name"]: o for o in rule.get("outputs_exposed", [])}
    try:
        out = reg["func"](values, params)
    except Exception as e:
        return {"execution_status": STATUS_ERROR, "reasons": [f"插件异常: {e}"], "info": {}}
    exposed = {k: out[k] for k in rule.get("outputs_exposed_named", []) if k in out}
    exposed = {k: out[k] for k in (rule.get("outputs_exposed_named") or list(outputs_spec)) if k in out}
    # 判定：预测寿命 ≥ 目标寿命 / safety_factor（由 params/inputs 语义决定，标准做法：比较 exposed 与阈值）
    verdict = None
    reasons = []
    lt = values.get("product_lifetime_target")
    life = out.get("predicted_life_hours")
    factor = (ref.get("params") or {}).get("life_safety_factor", {})
    sf = factor.get("value", 1.2) if isinstance(factor, dict) else 1.2
    if life is not None and lt is not None:
        verdict = life >= lt * sf
        reasons.append(f"预测寿命 {life:.0f}h vs 目标 {lt}h×{sf}")
    return {"execution_status": (STATUS_PASS if verdict else STATUS_FAIL) if verdict is not None else STATUS_ERROR,
            "reasons": reasons + pre_notes,
            "info": {"outputs": out, "tolerance_rel": 0.01}}


def run_rule(rule: dict, inputs: dict[str, MeasuredParam], engine: UnitEngine) -> dict:
    """统一入口。inputs: 变量名 → MeasuredParam（已按 unit_dictionary 归一）。"""
    rt = rule.get("rule_type")
    unit_dim = {i["name"]: ("table" if i.get("unit") == "table" else None) for i in rule.get("inputs", [])}
    if rt == EXEC_DECL:
        return run_declarative(rule, engine, inputs, unit_dim)
    if rt == EXEC_CURVE:
        return run_lookup_curve(rule, engine, inputs, unit_dim)
    if rt == EXEC_PLUGIN:
        return run_script_plugin(rule, engine, inputs, unit_dim)
    return {"execution_status": STATUS_ERROR, "reasons": [f"未知 rule_type: {rt}"], "info": {}}
