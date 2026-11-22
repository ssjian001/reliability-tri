"""G1 规则引擎回归测试：三模板全用例 + 温度双轨手算 + 状态机。"""
import pathlib, sys

import pytest, yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine"))
from reliability_engine import UnitEngine, run_rule, register_plugin  # noqa: E402
from reliability_engine.plugins.ecap_arrhenius_v1 import evaluate_ecap_lifetime  # noqa: E402
from reliability_engine.measured import MeasuredParam  # noqa: E402

ATT = ROOT / "V1.1/attachments"
ENG = UnitEngine(ATT / "unit_dictionary.yaml")
RULES = {r["rule_id"]: r for r in yaml.safe_load((ATT / "rule_templates.yaml").read_text(encoding="utf-8"))}
register_plugin("reliability_calc.capacitors.ecap_arrhenius_v1", "evaluate_ecap_lifetime",
                evaluate_ecap_lifetime, "v1", "sha256:local-dev")

MOCK_SOA = [{"pulse_width_ms": 10, "max_id": 10.0}, {"pulse_width_ms": 100, "max_id": 6.0},
            {"pulse_width_ms": 1000, "max_id": 4.0}]

def build_inputs(rule, test_inputs):
    out = {}
    for spec in rule["inputs"]:
        name = spec["name"]
        if name not in test_inputs:
            continue
        v, unit = test_inputs[name], spec["unit"]
        if unit == "table":
            out[name] = MeasuredParam(raw_value=MOCK_SOA, raw_unit="table", norm_value=0, norm_unit="table",
                quantity_kind="absolute", source_type="datasheet", evidence_id=None,
                source_level="A", extraction_status="human_verified", applicability_status="in_scope")
            continue
        out[name] = MeasuredParam(raw_value=v, raw_unit=unit, norm_value=0, norm_unit=unit,
            quantity_kind=spec.get("quantity_kind", "absolute"), source_type="manual", evidence_id=None,
            source_level="A", extraction_status="human_verified", applicability_status="in_scope")
    return out

@pytest.mark.parametrize("rid", list(RULES))
def test_template_cases(rid):
    rule = RULES[rid]
    for tc in rule["tests"]:
        result = run_rule(rule, build_inputs(rule, tc["inputs"]))
        expected = tc.get("expected_status", "PASS" if tc.get("expected_pass") else "FAIL")
        assert result["execution_status"] == expected, (tc["name"], result)
        if expected == "PASS" and "expected_outputs" in tc:
            outs = result["info"].get("outputs", {})
            for k, v in tc["expected_outputs"].items():
                assert abs(outs[k] - v) / abs(v) <= tc.get("tolerance_rel", 0.001), (k, outs[k])

def test_temperature_dual_track():
    """复审 P0-2 修复验证：25/85/150℃ 三组折减因子手算一致；absolute/delta 分离。"""
    for c, want in [(25, 1.00), (85, 0.52), (150, 0.00)]:
        n_abs = ENG.normalize(c, "degC", "absolute")
        n_delta = ENG.normalize(c - 25, "degC_delta", "delta")
        assert abs(n_abs.value - (c + 273.15)) < 1e-9
        assert abs(1 - n_delta.value / 125 - want) < 1e-9

def test_state_machine_precedence():
    """复审 P0-3：DATA_GAP > NOT_APPLICABLE > SKIPPED_PRECONDITION > PASS/FAIL。"""
    rule = RULES["ELEC-RES-PWR-001"]
    # DATA_GAP：缺输入
    r = run_rule(rule, {})
    assert r["execution_status"] == "DATA_GAP"
    # NOT_APPLICABLE > SKIPPED：applicability 由框架判定，此处验 SKIPPED 优先于 FAIL
    r = run_rule(rule, build_inputs(rule, {"power_dissipation": 0.04, "rated_power_70c": 0.1,
        "local_ambient_temp": 85, "derating_ratio_limit": 0.5}))
    assert r["execution_status"] == "SKIPPED_PRECONDITION"

def test_conflict_unresolved_in_status_model():
    """复审 P0-4：CONFLICT_UNRESOLVED 在状态模型中可表达（ Finding 层字段）。"""
    from reliability_engine.executors import STATUS_CONFLICT
    assert STATUS_CONFLICT == "CONFLICT_UNRESOLVED"

def test_string_numeric_and_invalid_value():
    """r5 回归（复审 P0-C2R）：数字字符串合法；非数值 → ERROR(INVALID_VALUE) 而非裸抛。"""
    rule = RULES["ELEC-RES-PWR-001"]
    inputs = build_inputs(rule, {"power_dissipation": 0.05, "rated_power_70c": 0.1,
                                 "local_ambient_temp": 55, "derating_ratio_limit": 0.5})
    inputs["power_dissipation"].raw_value = "0.05"
    inputs["power_dissipation"].decl_value = None
    r = run_rule(rule, inputs)
    assert r["execution_status"] == "PASS"
    inputs["power_dissipation"].raw_value = "55x"
    r = run_rule(rule, inputs)
    assert r["execution_status"] == "ERROR"
    assert any("INVALID_VALUE" in s for s in r["reasons"])

def test_syntax_error_returns_error_not_raise():
    """r5 回归（复审 P0-B1R）：DSL 语法错（AND 大写）→ ERROR，不裸抛。"""
    rule = dict(RULES["ELEC-RES-PWR-001"])
    rule["expression"] = "power_dissipation > 0 AND local_ambient_temp <= 70"
    inputs = build_inputs(rule, {"power_dissipation": 0.05, "rated_power_70c": 0.1,
                                 "local_ambient_temp": 55, "derating_ratio_limit": 0.5})
    r = run_rule(rule, inputs)
    assert r["execution_status"] == "ERROR"
    assert any("DSL" in s for s in r["reasons"])

def test_digest_mismatch_returns_error():
    """r5 回归（复审 C-3）：plugin digest 不匹配 → ERROR。"""
    rule = dict(RULES["ELEC-ECAP-LIFE-003"])
    rule["plugin_ref"] = dict(rule["plugin_ref"], digest="sha256:wrong")
    inputs = build_inputs(rule, {"ripple_current_rms": 0.5, "esr_at_freq": 0.1,
                                 "thermal_resistance_ca": 40, "local_ambient_temp": 65,
                                 "rated_max_temp": 105, "rated_endurance_hours": 2000,
                                 "product_lifetime_target": 20000})
    r = run_rule(rule, inputs)
    assert r["execution_status"] == "ERROR"
    assert any("digest" in s for s in r["reasons"])

def test_verdict_expr_ecap():
    """r5 回归（复审 C-1）：verdict_expr DSL 判定（85℃ 寿命不足 → FAIL 正确）。"""
    rule = RULES["ELEC-ECAP-LIFE-003"]
    inputs = build_inputs(rule, {"ripple_current_rms": 0.5, "esr_at_freq": 0.1,
                                 "thermal_resistance_ca": 40, "local_ambient_temp": 85,
                                 "rated_max_temp": 105, "rated_endurance_hours": 2000,
                                 "product_lifetime_target": 20000})
    r = run_rule(rule, inputs)
    assert r["execution_status"] == "FAIL"
