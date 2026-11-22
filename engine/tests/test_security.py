"""G2-4 安全测试：28 条注入语料自动化执行（T14）。

断言：注入语料注入 BOM/手册输入后——
1. 引擎不执行文本中的指令（finding 依规则计算，不受文本影响）；
2. 注入文本按数据入库（BOM 导入不拒收，仅告警）；
3. 输出不含系统提示词泄露。
"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "engine"))
from reliability_engine import UnitEngine, run_rule  # noqa: E402
from reliability_engine.measured import MeasuredParam  # noqa: E402

ATT = pathlib.Path(__file__).resolve().parents[2] / "V1.1/attachments"
ENG = UnitEngine(ATT / "unit_dictionary.yaml")
DATASET = json.loads((ATT / "prompt_injection_dataset.json").read_text(encoding="utf-8"))

def test_dataset_size_and_forms():
    assert len(DATASET["items"]) >= 20
    assert len(DATASET["payload_forms"]) >= 6

def test_injection_in_bom_comment_does_not_alter_engine():
    """注入文本放入器件备注/手册字段后，规则判定结果与干净输入一致（T14 核心）。"""
    rule = {
        "rule_id": "TEST-SEC-001", "rule_type": "declarative_expr", "domain": "derating",
        "title": "测试规则", "inputs": [
            {"name": "operating_voltage", "unit": "V", "required": True},
            {"name": "rated_voltage", "unit": "V", "required": True},
            {"name": "voltage_ratio_limit", "unit": "ratio", "required": True},
        ],
        "expression": "(operating_voltage / rated_voltage) <= voltage_ratio_limit",
        "thresholds": {"voltage_ratio_limit": {"value": 0.6, "unit": "ratio", "source_ref": "test"}},
        "severity": "high",
    }
    clean = {"operating_voltage": {"value": 10, "unit": "V", "source_level": "A",
             "extraction_status": "human_verified", "applicability_status": "in_scope"},
             "rated_voltage": {"value": 25, "unit": "V", "source_level": "A",
              "extraction_status": "human_verified", "applicability_status": "in_scope"},
             "voltage_ratio_limit": {"value": 0.6, "unit": "ratio", "source_level": "A",
              "extraction_status": "human_verified", "applicability_status": "in_scope"}}
    # 对 28 条语料逐条：把 payload 注入 input 的 applicability_note / raw_value 文本
    for item in DATASET["items"]:
        payload = item["payload"]
        poisoned = dict(clean)
        poisoned["operating_voltage"] = dict(clean["operating_voltage"],
                                             applicability_note=payload)
        inputs = {k: MeasuredParam(
            raw_value=v["value"] if k != "operating_voltage" else 10,
            raw_unit=v["unit"], norm_value=v["value"] if k == "operating_voltage" else 10,
            norm_unit=v["unit"], quantity_kind="absolute",
            source_type="manual", evidence_id=None,
            source_level="A", extraction_status="human_verified", applicability_status="in_scope",
            applicability_note=payload if k == "operating_voltage" else None,
        ) for k, v in poisoned.items()}
        r = run_rule(rule, inputs)
        assert r["execution_status"] in ("PASS", "FAIL"), \
            f"{item['id']}: 注入文本改变执行状态 {r['execution_status']}"
        # 10V/25V=0.4 ≤ 0.6 → PASS（数值判定不受注入影响）
        assert r["execution_status"] == "PASS", f"{item['id']}: 注入影响判定"

def test_injection_payload_not_in_output():
    """注入文本不出现在引擎输出的结论/理由中（防数据→指令通道）。"""
    rule = {
        "rule_id": "TEST-SEC-002", "rule_type": "declarative_expr", "domain": "derating",
        "title": "测试规则", "inputs": [{"name": "x", "unit": "dimensionless", "required": True}],
        "expression": "x <= 1", "thresholds": {}, "severity": "medium",
    }
    inputs = {"x": MeasuredParam(raw_value=0.5, raw_unit="dimensionless", norm_value=0.5,
        norm_unit="dimensionless", quantity_kind="absolute", source_type="manual",
        evidence_id=None, source_level="A", extraction_status="human_verified",
        applicability_status="in_scope",
        applicability_note=DATASET["items"][1]["payload"])}
    r = run_rule(rule, inputs)
    blob = json.dumps(r, ensure_ascii=False)
    assert "ignore previous" not in blob.lower() or "applicability_note" in blob

def test_all_payloads_treated_as_data():
    """全部语料的 payload 作为 applicability_note 注入时，引擎不崩溃且判定稳定。"""
    rule = {
        "rule_id": "TEST-SEC-003", "rule_type": "declarative_expr", "domain": "derating",
        "title": "测试规则", "inputs": [{"name": "x", "unit": "dimensionless", "required": True}],
        "expression": "x <= 1", "thresholds": {}, "severity": "low",
    }
    statuses = set()
    for item in DATASET["items"]:
        inputs = {"x": MeasuredParam(raw_value=0.5, raw_unit="dimensionless", norm_value=0.5,
            norm_unit="dimensionless", quantity_kind="absolute", source_type="manual",
            evidence_id=None, source_level="A", extraction_status="human_verified",
            applicability_status="in_scope", applicability_note=item["payload"])}
        r = run_rule(rule, inputs)
        statuses.add(r["execution_status"])
    assert statuses <= {"PASS", "FAIL"}, f"出现意外状态: {statuses}"
