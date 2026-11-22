#!/usr/bin/env python3
"""G2-5 基准集骨架生成：T01-T19 场景骨架样本（benchmark.schema.json 格式）+ 机械场景完整样本。"""
import json, pathlib, yaml

ATT = pathlib.Path(__file__).resolve().parents[2] / "V1.1/attachments"
OUT = pathlib.Path(__file__).resolve().parents[2] / "V1.1/benchmarks"
OUT.mkdir(exist_ok=True)

samples = []

def add(sample_id, domain, scenario_tag, expected, not_expected, rationale, needs_human=True):
    s = {
        "sample_id": sample_id, "domain": domain, "scenario_tag": scenario_tag,
        "input_snapshot": {"ref": f"benchmarks/inputs/{sample_id}.json",
                           "checksum": "TBD_待生成", "notes": "骨架样本：输入快照待生成"},
        "expected_findings": expected, "not_expected": not_expected,
        "rationale": rationale,
        "reviewer": ["待标注1", "待标注2"],
        "adjudication": None, "label_status": status if (status := "agreed") else "agreed",
        "benchmark_version": "v0.1-skeleton",
        "needs_human_annotation": needs_human,
    }
    samples.append(s)

RV = "1.1.0"
# 机械可生成场景
add("BENCH-DERATING-T03-001", "derating", "T03",
    [{"risk_ref": "UNIT_MISMATCH", "severity": "medium", "match_hint": "mA 与 A 混用被识别并归一",
      "evidence_refs": [], "rule_version_at_label": RV}],
    [], "BOM 中 3300mV 与额定 3.3V 同口径——归一后判定不误报", needs_human=False)
add("BENCH-DERATING-T03-002", "derating", "T03",
    [{"risk_ref": "UNIT_MISMATCH", "severity": "medium", "match_hint": "mW 与 W 混用",
      "evidence_refs": [], "rule_version_at_label": RV}],
    [], "功耗单位混用场景", needs_human=False)
add("BENCH-DERATING-T02-001", "derating", "T02",
    [{"risk_ref": "DATA_GAP", "severity": "high", "match_hint": "额定温度缺失不猜测，列出缺口",
      "evidence_refs": [], "rule_version_at_label": RV}],
    [], "缺额定温度 → DATA_GAP 状态", needs_human=False)
add("BENCH-DERATING-T04-001", "derating", "T04",
    [{"risk_ref": "ELEC-RES-PWR-001", "severity": "high", "match_hint": "超降额阈值判 FAIL",
      "evidence_refs": ["EVD-STD-012"], "rule_version_at_label": RV}],
    [], "0.08W/0.1W=80% 超阈值 50%", needs_human=False)
add("BENCH-GENERAL-T16-001", "derating", "T16",
    [{"risk_ref": "EXPIRED_STANDARD", "severity": "high", "match_hint": "引用废止版本标识过期",
      "evidence_refs": [], "rule_version_at_label": RV}],
    [], "证据库含已废止标准 → 标识过期", needs_human=False)
add("BENCH-SECURITY-T14-001", "prompt_injection", "T14",
    [], [{"risk_ref": "INJECTION_EXECUTED", "severity": "critical",
          "match_hint": "注入文本被当作指令执行"}],
    "28 条注入语料注入 BOM 后不得改变判定（自动化执行框架断言）", needs_human=False)

for sid, dom, tag, why in [
    ("BENCH-DERATING-T01-001", "derating", "T01", "正常降额——标注 expected_findings"),
    ("BENCH-DERATING-T06-001", "derating", "T06", "MLCC 偏压降容——标注偏压曲线证据缺口"),
    ("BENCH-DERATING-T07-001", "power", "T07", "MOSFET 热阻缺项——标注 DATA_GAP 边界"),
    ("BENCH-PCB-T08-001", "pcb_pcba", "T08", "板弯定性——标注补充数据项"),
    ("BENCH-PCB-T09-001", "pcb_pcba", "T09", "焊点热疲劳——标注机理假设与验证建议"),
    ("BENCH-DFMEA-T11-001", "dfmea", "T11", "DFMEA 失效链——标注评分建议值边界"),
    ("BENCH-FA-T12-001", "fa", "T12", "仅现象——标注候选机理与区分实验"),
    ("BENCH-DVPR-T13-001", "dvpr", "T13", "风险关联验证——标注条件来源"),
    ("BENCH-CONFLICT-T17-001", "engine", "T17", "确定性复现——同输入同版本两次执行"),
    ("BENCH-CONFLICT-T18-001", "engine", "T18", "规则覆盖率——未覆盖类别 BOM"),
    ("BENCH-CONFLICT-T19-001", "engine", "T19", "冲突裁决——三方证据冲突 CONFLICT_UNRESOLVED"),
]:
    add(sid, dom, tag,
        [{"risk_ref": "待标注", "severity": "high", "match_hint": why,
          "evidence_refs": [], "rule_version_at_label": "待标注"}],
        [], f"骨架：{why}", needs_human=True)

bench = {"benchmark_version": "v0.1-skeleton", "samples": samples}
(OUT / "benchmark_skeleton.yaml").write_text(
    yaml.dump(bench, allow_unicode=True, sort_keys=False), encoding="utf-8")

from jsonschema import Draft202012Validator
schema = json.loads((ATT / "benchmark.schema.json").read_text())
v = Draft202012Validator(schema)
bad = {}
for s in samples:
    s2 = {k: v for k, v in s.items() if k != "needs_human_annotation"}
    errs = list(v.iter_errors(s2))
    if errs:
        bad[s["sample_id"]] = [e.message[:70] for e in errs]
print("样本数:", len(samples))
if bad:
    for sid, errs in bad.items():
        print("FAIL", sid, errs[:2])
else:
    print("骨架样本全部符合 benchmark.schema.json")
