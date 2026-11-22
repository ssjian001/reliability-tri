"""三类执行器（01 §3.1）：declarative_expr / lookup_curve / script_plugin。
统一入口 run_rule(rule, inputs) → Finding 数据（execution_status + 判定 + 计算过程）。
状态机优先级（01 §7.1）：DATA_GAP > NOT_APPLICABLE > SKIPPED_PRECONDITION > CONFLICT_UNRESOLVED > PASS/FAIL。

V1.1.1-r3-delta 修复（复审 B-1/B-2/C-1/C-2/D）：
- declarative/lookup 的变量按 inputs 声明单位口径传入（MeasuredParam.decl）
- preconditions 数组化 DSL；求值异常按类型分流 ERROR/DATA_GAP
- lookup_curve 按 curve_eval.table_columns 取列（v1 单族 1D 插值；expression 为人读描述不执行）
- script_plugin 判定走 plugin_ref.verdict_expr（DSL 求值），tolerance 由规则声明
- run_rule 出口做三轴可信检查（不达标标 advisory）与插件 digest 校验
"""
from __future__ import annotations

import math

from .dsl import DSLEvaluator, validate as dsl_validate
from .measured import MeasuredParam  # noqa: F401
from .units import UnitEngine, UnitError

EXEC_DECL = "declarative_expr"
EXEC_CURVE = "lookup_curve"
EXEC_PLUGIN = "script_plugin"
RULE_TYPES = {EXEC_DECL, EXEC_CURVE, EXEC_PLUGIN}

STATUS_PASS, STATUS_FAIL = "PASS", "FAIL"
STATUS_GAP, STATUS_NA = "DATA_GAP", "NOT_APPLICABLE"
STATUS_SKIP, STATUS_CONFLICT, STATUS_ERROR = "SKIPPED_PRECONDITION", "CONFLICT_UNRESOLVED", "ERROR"


def _collect(rule: dict, inputs: dict) -> tuple[dict, list[str]]:
    """按 inputs 声明收集变量：数值类 decl 到声明单位口径；table 原样传递。"""
    values, missing = {}, []
    for spec in rule.get("inputs", []):
        name = spec["name"]
        mp = inputs.get(name)
        if mp is None:
            missing.append(name)
            continue
        if spec.get("unit") == "table":
            values[name] = mp.raw_value  # 表对象原样传递（非物理量，不归一）
        else:
            values[name] = mp.decl(spec["unit"]).decl_value  # 声明单位口径
    return values, missing


def eval_preconditions(rule: dict, values: dict, evaluator: DSLEvaluator):
    """前置条件 DSL 数组。DSL 违规抛 ValueError（→ ERROR），求值失败归 DATA_GAP。"""
    notes = []
    for pre in rule.get("preconditions") or []:
        expr, on_fail = pre["expr"], pre.get("on_fail", STATUS_SKIP)
        try:
            dsl_validate(expr, list(values))
        except ValueError as e:
            raise ValueError(f"precondition DSL 违规: {e}")
        try:
            ok = evaluator.with_values(values).evaluate(expr, list(values))
        except Exception as e:
            return STATUS_GAP, notes + [f"precondition 求值失败: {e}"]
        if not ok:
            return on_fail, notes + [f"precondition 不满足: {expr}"]
    return None, notes


def run_declarative(rule: dict, inputs: dict) -> dict:
    variables = [i["name"] for i in rule.get("inputs", [])]
    expr = rule["expression"]
    try:
        dsl_validate(expr, variables)
    except ValueError as e:
        return {"execution_status": STATUS_ERROR, "reasons": [f"DSL 违规: {e}"], "info": {}}
    try:
        values, missing = _collect(rule, inputs)
    except UnitError as e:
        return {"execution_status": STATUS_ERROR, "reasons": [f"{e.code}: {e}"], "info": {}}
    if missing:
        return {"execution_status": STATUS_GAP, "reasons": [f"缺失输入: {', '.join(missing)}"], "info": {}}
    ev = DSLEvaluator(values)
    try:
        status, pre_notes = eval_preconditions(rule, values, ev)
    except ValueError as e:
        return {"execution_status": STATUS_ERROR, "reasons": [str(e)], "info": {}}
    if status:
        return {"execution_status": status, "reasons": pre_notes, "info": {}}
    try:
        result = ev.evaluate(expr, variables)
    except ZeroDivisionError:
        return {"execution_status": STATUS_ERROR, "reasons": ["DIV_BY_ZERO"], "info": {}}
    except Exception as e:
        return {"execution_status": STATUS_ERROR, "reasons": [f"求值异常: {e}"], "info": {}}
    verdict = bool(result)
    thresholds = rule.get("thresholds") or {}
    return {"execution_status": STATUS_PASS if verdict else STATUS_FAIL,
            "reasons": pre_notes,
            "info": {"result": result, "thresholds": thresholds}}


def _interp_1d(table: list[dict], cols: dict, x_value: float) -> float:
    """单族 log-log 线性插值。x_key/y_key 来自 curve_eval.table_columns。越界报错。"""
    x_key, y_key = cols["x"], cols["y"]
    pts = []
    for row in table:
        try:
            pts.append((float(row[x_key]), float(row[y_key])))
        except (KeyError, TypeError, ValueError):
            continue
    if not pts:
        raise ValueError("曲线表为空或列名不匹配")
    pts.sort()
    xs = [p[0] for p in pts]
    if x_value < min(xs) - 1e-12 or x_value > max(xs) + 1e-12:
        raise ValueError(f"目标 x={x_value} 超出曲线范围 [{min(xs)}, {max(xs)}]")
    if x_value <= 0 or min(xs) <= 0 or max(xs) <= 0:
        # 非正数域退化为线性插值
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]; x1, y1 = pts[i + 1]
            if x0 <= x_value <= x1 and x1 > x0:
                return y0 + (y1 - y0) * (x_value - x0) / (x1 - x0)
        return pts[-1][1]
    lxs = [math.log10(p[0]) for p in pts]
    lys = [math.log10(p[1]) for p in pts]
    lx = math.log10(x_value)
    for i in range(len(pts) - 1):
        if lxs[i] <= lx <= lxs[i + 1] and lxs[i + 1] > lxs[i]:
            ly = lys[i] + (lys[i + 1] - lys[i]) * (lx - lxs[i]) / (lxs[i + 1] - lxs[i])
            return 10 ** ly
    return pts[-1][1]


def run_lookup_curve(rule: dict, inputs: dict) -> dict:
    ce = rule["curve_eval"]
    cols = ce.get("table_columns") or {}
    if not cols.get("x") or not cols.get("y"):
        return {"execution_status": STATUS_ERROR, "reasons": ["curve_eval.table_columns 未声明 x/y 列"], "info": {}}
    table_name = cols.get("table") or next(
        (i["name"] for i in rule.get("inputs", []) if i.get("unit") == "table"), None)
    if table_name is None:
        return {"execution_status": STATUS_ERROR, "reasons": ["无 table 类型输入"], "info": {}}
    variables = [i["name"] for i in rule.get("inputs", [])]
    try:
        values, missing = _collect(rule, inputs)
    except UnitError as e:
        return {"execution_status": STATUS_ERROR, "reasons": [f"{e.code}: {e}"], "info": {}}
    if missing:
        return {"execution_status": STATUS_GAP, "reasons": [f"缺失输入: {', '.join(missing)}"], "info": {}}
    table = values.get(table_name)
    if not isinstance(table, list):
        return {"execution_status": STATUS_ERROR, "reasons": [f"曲线表 {table_name} 不是列表"], "info": {}}
    ev = DSLEvaluator(values)
    try:
        status, pre_notes = eval_preconditions(rule, values, ev)
    except ValueError as e:
        return {"execution_status": STATUS_ERROR, "reasons": [str(e)], "info": {}}
    if status:
        return {"execution_status": status, "reasons": pre_notes, "info": {}}
    # 数值轴变量（非 table 的全部 inputs）
    numeric = {k: v for k, v in values.items() if isinstance(v, (int, float))}
    try:
        limit_raw = _interp_1d(table, cols, numeric[cols["x"]])
    except ValueError as e:
        return {"execution_status": STATUS_ERROR, "reasons": [f"曲线插值: {e}"], "info": {}}
    # 温度折减因子：按 delta 语义计算（°C 差值 = K 差值）
    ref_c = ce.get("temp_derating_delta_ref_c")
    max_c = ce.get("temp_derating_delta_max_c")
    t_var = ce.get("temp_var")
    factor = 1.0
    if ref_c is not None and max_c:
        if t_var is None:
            return {"execution_status": STATUS_ERROR, "reasons": ["curve_eval.temp_var 未声明（温度折减需要温度变量）"], "info": {}}
        if t_var not in numeric:
            return {"execution_status": STATUS_ERROR, "reasons": [f"temp_var {t_var} 不在 inputs"], "info": {}}
        factor = 1 - (numeric[t_var] - ref_c) / max_c
    margin = ce.get("safety_margin_ratio", 1.0)
    limit = limit_raw * factor * margin
    # 目标变量：curve_eval.target_var 显式声明（复审 B-2：消除启发式选择）
    target_var = ce.get("target_var")
    if target_var is None or target_var not in numeric:
        return {"execution_status": STATUS_ERROR,
                "reasons": [f"curve_eval.target_var 未声明或不在 inputs: {target_var}"], "info": {}}
    target = numeric[target_var]
    verdict = target <= limit
    return {"execution_status": STATUS_PASS if verdict else STATUS_FAIL,
            "reasons": pre_notes,
            "info": {"limit_raw": limit_raw, "temp_factor": factor, "safety_margin": margin,
                     "limit_after": limit, "target": target, "target_var": target_var}}


PLUGIN_REGISTRY: dict[str, dict] = {}


def register_plugin(module: str, entry_func: str, func, version: str, digest: str):
    """受控注册表（01 §3.1）。digest 必填：与 plugin_ref.digest 比对（复审 C-3）。"""
    PLUGIN_REGISTRY[f"{module}.{entry_func}"] = {
        "func": func, "version": version, "digest": digest,
    }


def run_script_plugin(rule: dict, inputs: dict) -> dict:
    ref = rule["plugin_ref"]
    key = f"{ref['module']}.{ref['entry_func']}"
    reg = PLUGIN_REGISTRY.get(key)
    if reg is None:
        return {"execution_status": STATUS_ERROR,
                "reasons": [f"插件未注册: {key}（白名单外禁止动态导入）"], "info": {}}
    want_digest = ref.get("digest")
    if want_digest and reg["digest"] != want_digest:
        return {"execution_status": STATUS_ERROR,
                "reasons": [f"插件 digest 不匹配: 注册 {reg['digest'][:16]}… vs 声明 {want_digest[:16]}…"], "info": {}}
    try:
        values, missing = _collect(rule, inputs)
    except UnitError as e:
        return {"execution_status": STATUS_ERROR, "reasons": [f"{e.code}: {e}"], "info": {}}
    if missing:
        return {"execution_status": STATUS_GAP, "reasons": [f"缺失输入: {', '.join(missing)}"], "info": {}}
    ev = DSLEvaluator(values)
    try:
        status, pre_notes = eval_preconditions(rule, values, ev)
    except ValueError as e:
        return {"execution_status": STATUS_ERROR, "reasons": [str(e)], "info": {}}
    if status:
        return {"execution_status": status, "reasons": pre_notes, "info": {}}
    params = {}
    for k, v in (ref.get("params") or {}).items():
        params[k] = v["value"] if isinstance(v, dict) and "value" in v else v
    outputs_named = [o["name"] for o in rule.get("outputs_exposed", [])] if isinstance(
        rule.get("outputs_exposed", [{}])[0] if rule.get("outputs_exposed") else None, dict) else rule.get("outputs_exposed", [])
    try:
        out = reg["func"](values, params)
    except Exception as e:
        return {"execution_status": STATUS_ERROR, "reasons": [f"插件异常: {e}"], "info": {}}
    # C-1: 判定走 verdict_expr（DSL 求值，可引用 outputs 与 inputs 变量）
    verdict_expr = ref.get("verdict_expr")
    if verdict_expr:
        merged = dict(values); merged.update(out)
        merged.update({k: (v["value"] if isinstance(v, dict) and "value" in v else v) for k, v in (ref.get("params") or {}).items()})
        try:
            dsl_validate(verdict_expr, list(merged))
            verdict = bool(DSLEvaluator(merged).evaluate(verdict_expr, list(merged)))
        except ValueError as e:
            return {"execution_status": STATUS_ERROR, "reasons": [f"verdict_expr 违规: {e}"], "info": {}}
    else:
        # 未声明 verdict_expr：仅执行插件供报告，判定交人工
        verdict = None
    reasons = pre_notes
    if verdict is False:
        reasons = reasons + [f"verdict_expr 判定未通过（{verdict_expr[:60]}）"]
    result = {"execution_status": (STATUS_PASS if verdict else STATUS_FAIL) if verdict is not None else STATUS_PASS,
              "reasons": reasons,
              "info": {"outputs": out, "verdict": verdict, "advisory": verdict is None}}
    if verdict is None:
        result["info"]["advisory"] = True
    return result


def run_rule(rule: dict, inputs: dict[str, MeasuredParam], engine: UnitEngine) -> dict:
    """统一入口。inputs: 变量名 → MeasuredParam。出口做三轴可信检查（复审 C-3）。"""
    rt = rule.get("rule_type")
    unit_dim = {i["name"]: ("table" if i.get("unit") == "table" else None) for i in rule.get("inputs", [])}
    if rt == EXEC_DECL:
        result = run_declarative(rule, inputs)
    elif rt == EXEC_CURVE:
        result = run_lookup_curve(rule, inputs)
    elif rt == EXEC_PLUGIN:
        result = run_script_plugin(rule, inputs)
    else:
        result = {"execution_status": STATUS_ERROR, "reasons": [f"未知 rule_type: {rt}"], "info": {}}
    # C-3: 三轴可信检查——任一关键输入不达标 → 标记 advisory（不得作为正式 PASS 依据）
    advisory = []
    for spec in rule.get("inputs", []):
        mp = inputs.get(spec["name"])
        if mp and not mp.can_support_formal_pass():
            advisory.append(spec["name"])
    if advisory:
        result.setdefault("info", {})["advisory_inputs"] = advisory
        if result.get("execution_status") == STATUS_PASS:
            result["info"]["advisory"] = True
            result["reasons"] = result.get("reasons", []) + [f"输入三轴未达标(仅建议性): {', '.join(advisory)}"]
    return result
