"""G2-4 安全测试：28 条注入语料（输入侧 + 输出侧防护断言）。

新引擎适配（V1.1.1-G1 RuleExecutor）：inputs 用原生 {value, unit} 契约；
注入文本进 applicability_note（数据通道）后——判定不受影响、状态稳定。
"""
import json
import pathlib
import sys

from reliability_engine import RuleExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
ATT = pathlib.Path(__file__).resolve().parents[1] / "V1.1/attachments"
DATASET = json.loads((ATT / "prompt_injection_dataset.json").read_text(encoding="utf-8"))
EXEC = RuleExecutor()

RULE = {
    "rule_id": "TEST-SEC-001", "rule_type": "declarative_expr", "domain": "derating",
    "title": "注入回归测试规则",
    "inputs": [
        {"name": "operating_voltage", "unit": "V", "required": True, "source": "ComponentStress"},
        {"name": "rated_voltage", "unit": "V", "required": True, "source": "Component.rated_params"},
        {"name": "voltage_ratio_limit", "unit": "ratio", "required": True, "source": "Thresholds"},
    ],
    "expression": "(operating_voltage / rated_voltage) <= voltage_ratio_limit",
    "severity": "high",
}

CLEAN = {"operating_voltage": {"value": 10, "unit": "V"},
         "rated_voltage": {"value": 25, "unit": "V"},
         "voltage_ratio_limit": {"value": 0.6, "unit": "ratio"}}


def test_dataset_size_and_forms():
    assert len(DATASET["items"]) >= 20
    assert len(DATASET["payload_forms"]) >= 6


def test_injection_does_not_alter_verdict():
    """28 条语料逐条注入 applicability_note：10/25=0.4≤0.6 判 PASS 不受影响。"""
    for item in DATASET["items"]:
        inputs = {k: {**v, "applicability_note": item["payload"]} if k == "operating_voltage" else dict(v)
                  for k, v in CLEAN.items()}
        r = EXEC.execute(RULE, inputs)
        assert r["status"] == "pass", f"{item['id']}: 注入改变判定 → {r}"


def test_all_payloads_stable_and_no_leak():
    """全语料状态稳定；输出 JSON 不含系统提示词泄露特征。"""
    statuses = set()
    for item in DATASET["items"]:
        inputs = {k: {**v, "applicability_note": item["payload"]} for k, v in CLEAN.items()}
        r = EXEC.execute(RULE, inputs)
        statuses.add(r["status"])
        blob = json.dumps(r, ensure_ascii=False).lower()
        assert "system prompt" not in blob
    assert statuses == {"pass"}, f"状态漂移: {statuses}"
