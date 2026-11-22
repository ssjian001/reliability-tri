#!/usr/bin/env python3
"""Validate V1.1.1 machine-readable assets. Requires PyYAML and jsonschema."""
from pathlib import Path
import json
import sys
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1] / "V1.1"
ATT = ROOT / "attachments"

def load_json(name):
    return json.loads((ATT / name).read_text(encoding="utf-8"))

def main():
    rule_schema = load_json("rule.schema.json")
    bench_schema = load_json("benchmark.schema.json")
    Draft202012Validator.check_schema(rule_schema)
    Draft202012Validator.check_schema(bench_schema)

    rules = yaml.safe_load((ATT / "rule_templates.yaml").read_text(encoding="utf-8"))
    rule_validator = Draft202012Validator(rule_schema)
    failed = False
    for rule in rules:
        errors = list(rule_validator.iter_errors(rule))
        print(f"RULE {rule.get('rule_id')}: {'PASS' if not errors else 'FAIL'}")
        for error in errors:
            print(f"  {error.json_path}: {error.message}")
        failed |= bool(errors)

    sample = json.loads((ATT / "examples" / "benchmark_sample.example.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(bench_schema).iter_errors(sample))
    # Cross-field rules not expressible in JSON Schema are enforced here.
    annotator_ids = [item.get("annotator_id") for item in sample.get("annotations", [])]
    if len(annotator_ids) != 2 or len(set(annotator_ids)) != 2 or set(annotator_ids) != set(sample.get("reviewer", [])):
        errors.append(type("ValidationIssue", (), {"json_path": "$.annotations", "message": "reviewer IDs must exactly match two unique annotations"})())
    if sample.get("label_status") == "resolved" and not sample.get("adjudication"):
        errors.append(type("ValidationIssue", (), {"json_path": "$.adjudication", "message": "resolved labels require adjudication"})())
    print(f"BENCHMARK SAMPLE: {'PASS' if not errors else 'FAIL'}")
    for error in errors:
        print(f"  {error.json_path}: {error.message}")
    failed |= bool(errors)

    injections = load_json("prompt_injection_dataset.json")
    count = len(injections.get("items", []))
    print(f"PROMPT INJECTION ITEMS: {count} (target >= 20)")
    failed |= count < 20

    # published 门禁复核（复审 r4 残留 P1-1）：status=published 的规则须 tests>=3 且 kind 覆盖三类
    rules = yaml.safe_load((ATT / "rule_templates.yaml").read_text(encoding="utf-8"))
    kinds = {"normal", "boundary", "invalid"}
    for r in rules:
        if r.get("status") != "published":
            continue
        tests = r.get("tests") or []
        if len(tests) < 3:
            print(f"PUBLISHED GATE FAIL: {r['rule_id']} tests<3")
            failed = True
        got_kinds = {t.get("kind") for t in tests}
        if not kinds.issubset(got_kinds):
            print(f"PUBLISHED GATE FAIL: {r['rule_id']} 缺 kind: {kinds - got_kinds}")
            failed = True

    units = yaml.safe_load((ATT / "unit_dictionary.yaml").read_text(encoding="utf-8"))
    seen = {}
    collisions = []
    known_ambiguous = {"K", "h", "小时", "℃", "°C", "degC"}  # 温度双轨/寿命双维的固有歧义：解析须显式维度（unit_dictionary normalization_rules）
    for dimension, spec in units.get("dimensions", {}).items():
        for unit, meta in spec.get("units", {}).items():
            for alias in [unit, *meta.get("aliases", [])]:
                if alias in seen and seen[alias] != (dimension, unit):
                    if alias in known_ambiguous:
                        print(f"  WARN ambiguous alias (需显式维度): {alias} -> {seen[alias]} vs {(dimension, unit)}")
                    else:
                        collisions.append((alias, seen[alias], (dimension, unit)))
                seen[alias] = (dimension, unit)
    print(f"UNIT EXACT-ALIAS COLLISIONS: {len(collisions)}")
    for item in collisions:
        print(" ", item)
    failed |= bool(collisions)

    print("RESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
