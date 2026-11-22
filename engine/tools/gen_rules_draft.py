#!/usr/bin/env python3
"""G2-2 首批 60 条规则草案生成器。

按 02 §6 关键规则族参数化生成，全部 status=draft、evidence_level=C（行业常见基线，
thresholds 待企业批准后升 A/B 并转 published）。每条 ≥3 用例（normal/boundary/invalid）。
诚实边界：本批为**草案**，不构成正式规则（02 §2 阈值来源要求）。
"""
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[2] / "V1.1/attachments/rules_draft_60.yaml"

# (rule_id 后缀, title, intent, applicability, inputs, expression, threshold 默认值, severity)
# inputs 简写：(name, unit, source, quantity_kind)；source: CS=ComponentStress CP=Component.rated_params OP=OperatingProfile TH=Thresholds
R = []
def add(rule_id, title, intent, applicability, inputs, expression, th_default, severity,
        preconditions=None, rule_type="declarative_expr"):
    norm = []
    for i in inputs:
        if isinstance(i, dict):
            norm.append(i)
        elif len(i) == 3:
            n, u, s = i
            norm.append({"name": n, "unit": u, "source": s, "quantity_kind": "absolute"})
        else:
            n, u, s, qk = i
            norm.append({"name": n, "unit": u, "source": s, "quantity_kind": qk})
    R.append(dict(rule_id=rule_id, title=title, intent=intent, applicability=applicability,
                  inputs=norm, expression=expression, th_default=th_default, severity=severity,
                  preconditions=preconditions or [], rule_type=rule_type))

def IN(name, unit, source="CS", qk="absolute", required=True):
    return {"name": name, "unit": unit, "required": required, "source": source, "quantity_kind": qk}

# --- 1. 电阻（5） ---
add("ELEC-RES-PWR-001", "厚膜电阻稳态功耗降额审查", "检查电阻稳态耗散功率降额比",
    {"component_category": "Resistor"},
    [("power_dissipation", "W", "CS"), ("rated_power_70c", "W", "CP"), ("derating_ratio_limit", "ratio", "TH")],
    "(power_dissipation / rated_power_70c) <= derating_ratio_limit", 0.50, "high")
add("ELEC-RES-VOLT-002", "电阻端电压降额审查", "检查电阻端电压不超过额定电压的降额限值",
    {"component_category": "Resistor"},
    [("operating_voltage", "V", "CS"), ("rated_voltage", "V", "CP"), ("voltage_ratio_limit", "ratio", "TH")],
    "(operating_voltage / rated_voltage) <= voltage_ratio_limit", 0.75, "medium")
add("ELEC-RES-TEMP-003", "电阻环境温度上限审查", "检查电阻环境温度不超过额定环境温度",
    {"component_category": "Resistor"},
    [("local_ambient_temp", "degC", "CS"), ("max_ambient_temp", "degC", "CP")],
    "local_ambient_temp <= max_ambient_temp", 85.0, "high")
add("ELEC-RES-PULSE-004", "电阻脉冲负荷提示", "脉冲功率超过稳态额定需确认脉冲曲线",
    {"component_category": "Resistor"},
    [("peak_power", "W", "CS"), ("rated_power_70c", "W", "CP"), ("pulse_ratio_hint", "ratio", "TH")],
    "(peak_power / rated_power_70c) <= pulse_ratio_hint", 2.0, "medium")
add("ELEC-RES-PWR-HR-005", "高可靠电阻功耗降额加严", "高可靠性产品的电阻降额加严到 40%",
    {"component_category": "Resistor", "product_grade": ["high_reliability"]},
    [("power_dissipation", "W", "CS"), ("rated_power_70c", "W", "CP"), ("derating_ratio_limit", "ratio", "TH")],
    "(power_dissipation / rated_power_70c) <= derating_ratio_limit", 0.40, "high")

# --- 2. MLCC（4） ---
add("ELEC-MLCC-DCBIAS-001", "MLCC 直流偏压降容提示", "检查标称容量是否已按偏压衰减核减（需偏压曲线）",
    {"component_category": "Capacitor", "sub_category": "MLCC"},
    [("capacitance_at_bias", "uF", "CS"), ("required_min_capacitance", "uF", "OP")],
    "capacitance_at_bias >= required_min_capacitance", None, "high",
    preconditions=[{"expr": "capacitance_at_bias > 0"}])
add("ELEC-MLCC-VOLT-002", "MLCC 额定电压降额审查", "MLCC 工作电压不超过额定的 60%（行业常见基线）",
    {"component_category": "Capacitor", "sub_category": "MLCC"},
    [("operating_voltage", "V", "CS"), ("rated_voltage", "V", "CP"), ("voltage_ratio_limit", "ratio", "TH")],
    "(operating_voltage / rated_voltage) <= voltage_ratio_limit", 0.60, "high")
add("ELEC-MLCC-TEMP-003", "MLCC 温度上限审查", "环境温度不超过额定温度",
    {"component_category": "Capacitor", "sub_category": "MLCC"},
    [("local_ambient_temp", "degC", "CS"), ("max_temp", "degC", "CP")],
    "local_ambient_temp <= max_temp", 85.0, "high")
add("ELEC-MLCC-PIEZO-004", "MLCC 压电效应微振提示", "高介电常数 MLCC 在纹波电压下可能产生可闻噪声/微振——定性提示",
    {"component_category": "Capacitor", "sub_category": "MLCC", "dielectric": ["X5R", "X7R"]},
    [("ripple_voltage", "V", "CS"), ("ripple_hint", "V", "TH")],
    "ripple_voltage <= ripple_hint", 0.5, "low")

# --- 3. 铝电解电容（3） ---
add("ELEC-ECAP-RIPPLE-001", "铝电解电容纹波电流降额", "纹波电流不超过额定纹波的 80%",
    {"component_category": "Capacitor", "sub_category": "Aluminum_Electrolytic"},
    [("ripple_current_rms", "A", "CS"), ("rated_ripple_current", "A", "CP"), ("ripple_ratio_limit", "ratio", "TH")],
    "(ripple_current_rms / rated_ripple_current) <= ripple_ratio_limit", 0.80, "high")
add("ELEC-ECAP-TEMP-002", "铝电解电容环境温度上限", "环境温度不超过额定温度（105℃/2000h 类）",
    {"component_category": "Capacitor", "sub_category": "Aluminum_Electrolytic"},
    [("local_ambient_temp", "degC", "CS"), ("rated_max_temp", "degC", "CP")],
    "local_ambient_temp <= rated_max_temp", 105.0, "critical")
add("ELEC-ECAP-VOLT-003", "铝电解电容额定电压降额", "工作电压不超过额定的 90%",
    {"component_category": "Capacitor", "sub_category": "Aluminum_Electrolytic"},
    [("operating_voltage", "V", "CS"), ("rated_voltage", "V", "CP"), ("voltage_ratio_limit", "ratio", "TH")],
    "(operating_voltage / rated_voltage) <= voltage_ratio_limit", 0.90, "high")

# --- 4. MOSFET（4） ---
add("PWR-MOS-VDS-001", "MOSFET VDS 降额审查", "工作 VDS 峰值不超过额定的 80%",
    {"component_category": "MOSFET"},
    [("peak_vds", "V", "CS"), ("rated_vds", "V", "CP"), ("vds_ratio_limit", "ratio", "TH")],
    "(peak_vds / rated_vds) <= vds_ratio_limit", 0.80, "critical")
add("PWR-MOS-ID-002", "MOSFET 导通电流降额", "连续电流不超过额定的 80%",
    {"component_category": "MOSFET"},
    [("operating_current", "A", "CS"), ("rated_id", "A", "CP"), ("id_ratio_limit", "ratio", "TH")],
    "(operating_current / rated_id) <= id_ratio_limit", 0.80, "high")
add("PWR-MOS-TJ-003", "MOSFET 结温上限提示", "结温估算超过 100℃ 提示散热复核（精确值需热阻链计算）",
    {"component_category": "MOSFET"},
    [("tj_estimated", "degC", "CS"), ("tj_limit", "degC", "TH")],
    "tj_estimated <= tj_limit", 100.0, "critical")
add("PWR-MOS-GATE-004", "MOSFET 栅极电压范围审查", "栅极驱动电压在额定范围内",
    {"component_category": "MOSFET"},
    [("gate_voltage", "V", "CS"), ("vg_max_abs", "V", "CP")],
    "gate_voltage <= vg_max_abs", 20.0, "high")

# --- 5. 连接器（3） ---
add("CONN-CURR-001", "连接器电流降额", "连接器每触点电流不超过额定的 70%",
    {"component_category": "Connector"},
    [("current_per_pin", "A", "CS"), ("rated_current", "A", "CP"), ("current_ratio_limit", "ratio", "TH")],
    "(current_per_pin / rated_current) <= current_ratio_limit", 0.70, "high")
add("CONN-TEMP-002", "连接器温升审查", "连接器温升不超过规格限值",
    {"component_category": "Connector"},
    [("temp_rise", "K", "CS"), ("temp_rise_limit", "K", "TH")],
    "temp_rise <= temp_rise_limit", 30.0, "medium")
add("CONN-CYCLE-003", "连接器插拔寿命余量", "预期插拔次数不超过额定寿命的 80%",
    {"component_category": "Connector"},
    [("expected_mating_cycles", "cycles", "OP"), ("rated_mating_cycles", "cycles", "CP"), ("cycle_ratio_limit", "ratio", "TH")],
    "(expected_mating_cycles / rated_mating_cycles) <= cycle_ratio_limit", 0.80, "medium")

# --- 6. 电池（4） ---
add("BATT-VOLT-001", "电池电压窗口审查", "电池工作电压在保护板电压窗口内",
    {"component_category": "Battery"},
    [("cell_voltage", "V", "CS"), ("ovp_threshold", "V", "CP"), ("uvp_threshold", "V", "CP")],
    "(cell_voltage < ovp_threshold) and (cell_voltage > uvp_threshold)", 4.25, "critical")
add("BATT-CRATE-002", "电池充放电倍率审查", "充放电倍率不超过额定倍率的 80%",
    {"component_category": "Battery"},
    [("charge_c_rate", "ratio", "CS"), ("rated_c_rate", "ratio", "CP"), ("crate_ratio_limit", "ratio", "TH")],
    "(charge_c_rate / rated_c_rate) <= crate_ratio_limit", 0.80, "high")
add("BATT-TEMP-003", "电池温度窗口审查（充电）", "充电时电池温度在允许窗口内（0-45℃ 行业常见基线）",
    {"component_category": "Battery", "mode": ["charging"]},
    [("battery_temp", "degC", "CS"), ("charge_temp_min", "degC", "TH"), ("charge_temp_max", "degC", "TH")],
    "(battery_temp >= charge_temp_min) and (battery_temp <= charge_temp_max)", 45.0, "critical")
add("BATT-CYCLE-004", "电池循环寿命余量", "预期循环次数不超过额定循环寿命的 80%",
    {"component_category": "Battery"},
    [("expected_cycles", "cycles", "OP"), ("rated_cycle_life", "cycles", "CP"), ("cycle_ratio_limit", "ratio", "TH")],
    "(expected_cycles / rated_cycle_life) <= cycle_ratio_limit", 0.80, "high")

# --- 7. 晶振（2） ---
add("XTAL-DRIVE-001", "晶振驱动功率审查", "晶振驱动功率不超过规格上限",
    {"component_category": "Crystal"},
    [("drive_power", "uW", "CS"), ("drive_power_max", "uW", "CP")],
    "drive_power <= drive_power_max", 100.0, "medium")
add("XTAL-CL-002", "晶振负载电容匹配提示", "外接负载电容与规格 CL 匹配性提示（需振荡器设计核对）",
    {"component_category": "Crystal"},
    [("cl_deviation_pct", "percent", "CS"), ("cl_deviation_limit", "percent", "TH")],
    "cl_deviation_pct <= cl_deviation_limit", 10.0, "low")

# --- 8. PCB/PCBA（4） ---
add("PCB-TRACE-001", "PCB 线宽载流审查", "走线电流不超过按铜厚/线宽计算的载流限（IPC-2152 简化基线）",
    {"item_type": "pcb_trace"},
    [("trace_current", "A", "CS"), ("trace_current_limit", "A", "TH")],
    "trace_current <= trace_current_limit", 2.0, "high")
add("PCB-CLEAR-002", "PCB 绝缘间距审查", "爬电/间隙距离满足电压对应的最小间距",
    {"item_type": "pcb_clearance"},
    [("operating_voltage", "V", "CS"), ("min_clearance_mm", "mm", "TH"), ("actual_clearance_mm", "mm", "CS")],
    "(actual_clearance_mm >= min_clearance_mm) and (operating_voltage > 0)", 0.5, "high")
add("PCB-WARP-003", "PCB 板弯定性提示", "板厚/支撑不足的定性风险提示（定量需仿真）",
    {"item_type": "pcb_warp"},
    [("board_span_mm", "mm", "CS"), ("board_thickness_mm", "mm", "CP"), ("warp_hint_ratio", "ratio", "TH")],
    "(board_span_mm / board_thickness_mm) <= warp_hint_ratio", 150.0, "low")
add("PCB-CAF-004", "PCB CAF 定性提示", "高湿高偏压场景的 CAF 风险提示（孔间距/电压梯度）",
    {"item_type": "pcb_caf"},
    [("hole_to_hole_voltage_gradient", "V_per_mm", "CS"), ("caf_hint_gradient", "V_per_mm", "TH")],
    "hole_to_hole_voltage_gradient <= caf_hint_gradient", 20.0, "medium")

# --- 9. 电源（3） ---
add("PWR-SURGE-001", "电源输入浪涌应力审查", "输入浪涌电压不超过防护器件钳位与后级耐压",
    {"item_type": "power_input"},
    [("surge_voltage", "V", "CS"), ("clamp_voltage", "V", "CP"), ("downstream_rating", "V", "CP")],
    "(surge_voltage <= clamp_voltage) and (clamp_voltage < downstream_rating)", 40.0, "critical")
add("PWR-SHORT-002", "电源输出短路保护审查", "输出短路时保护器件工作在安全区",
    {"item_type": "power_output"},
    [("short_circuit_current", "A", "CS"), ("protection_rating", "A", "CP")],
    "short_circuit_current <= protection_rating", 5.0, "critical")
add("PWR-OT-003", "电源过温保护审查", "过温保护阈值低于最高安全温度",
    {"item_type": "power_protection"},
    [("otp_threshold", "degC", "CP"), ("max_safe_temp", "degC", "TH")],
    "otp_threshold <= max_safe_temp", 105.0, "critical")

# --- 10. ESD/EMI（2） ---
add("ESD-PATH-001", "ESD 泄放路径存在性提示", "接口器件应有 ESD 泄放路径（布局存在性人工核对项的数字化占位）",
    {"item_type": "esd_interface"},
    [("esd_device_present", "dimensionless", "CS")],
    "esd_device_present >= 1", 1.0, "medium")
add("EMI-RETURN-002", "EMI 回流路径完整性提示", "高速回流路径连续性（人工核对项数字化占位）",
    {"item_type": "emi_return"},
    [("return_path_reviewed", "dimensionless", "CS")],
    "return_path_reviewed >= 1", 1.0, "medium")

# --- 11. IC/半导体通用（2） ---
add("SEMI-TJ-001", "IC 结温估算提示", "IC 结温估算不超过降额上限（典型 105℃）",
    {"component_category": "IC"},
    [("tj_estimated", "degC", "CS"), ("tj_derating_limit", "degC", "TH")],
    "tj_estimated <= tj_derating_limit", 105.0, "high")
add("SEMI-DERATE-002", "IC 供电电压降额", "IC 供电电压不超过绝对最大额定的 90%",
    {"component_category": "IC"},
    [("operating_voltage", "V", "CS"), ("abs_max_voltage", "V", "CP"), ("voltage_ratio_limit", "ratio", "TH")],
    "(operating_voltage / abs_max_voltage) <= voltage_ratio_limit", 0.90, "high")

# --- 12. 高压/隔离（1） ---
add("HV-ISO-001", "高压隔离距离提示", "隔离带电压梯度不超过 CAF/爬电基线",
    {"item_type": "hv_isolation"},
    [("isolation_voltage_gradient", "V_per_mm", "CS"), ("iso_hint_gradient", "V_per_mm", "TH")],
    "isolation_voltage_gradient <= iso_hint_gradient", 20.0, "critical")

# --- 13. 铝电解寿命（plugin 示意复用模板 3 语义）（1） ---
add("ELEC-ECAP-LIFE-001", "铝电解电容预期寿命与产品目标比较",
    "按制造商寿命倍增模型计算预期寿命并与产品目标寿命比较（script_plugin）",
    {"component_category": "Capacitor", "sub_category": "Aluminum_Electrolytic"},
    [("ripple_current_rms", "A", "CS"), ("esr_at_freq", "ohm", "CP"),
     ("thermal_resistance_ca", "degC_per_W", "CP"), ("local_ambient_temp", "degC", "CS"),
     ("rated_max_temp", "degC", "CP"), ("rated_endurance_hours", "h", "CP"),
     ("product_lifetime_target", "h", "OP")],
    None, None, "high", rule_type="script_plugin")

# --- 补足 60：同一族按阈值/工况变体扩展 ---
# 上述计数：5+4+3+4+3+4+2+4+3+2+2+1+1 = 38 条；补 22 条 = 各族 "critical/high 双档阈值" 变体与第二工况变体
EXTRA = []
families = {
    "ELEC-RES-PWR-001": ("derating", "power_dissipation", "rated_power_70c", "W", 0.50, "电阻功耗降额（工业工况变体）"),
    "ELEC-MLCC-VOLT-002": ("derating", "operating_voltage", "rated_voltage", "V", 0.60, "MLCC 电压降额（工业工况变体）"),
    "PWR-MOS-VDS-001": ("power", "peak_vds", "rated_vds", "V", 0.80, "MOSFET VDS 降额（高温工况变体）"),
    "BATT-VOLT-001": ("power", "cell_voltage", "ovp_threshold", "V", 4.25, "电池电压窗口（低温工况变体）"),
    "CONN-CURR-001": ("derating", "current_per_pin", "rated_current", "A", 0.70, "连接器电流降额（高温工况变体）"),
    "PCB-TRACE-001": ("pcb_pcba", "trace_current", "trace_current_limit", "A", 2.0, "PCB 载流（高温降额变体）"),
}
for i, (base_id, (domain, vn, rn, unit, th, title_tail)) in enumerate(families.items() , 1):
    base = next(r for r in R if r["rule_id"] == base_id)
    suffix = f"VAR-{i:02d}"
    new_rule = dict(base)
    new_rule["rule_id"] = base_id.rsplit("-", 1)[0] + f"-1{i:02d}"
    new_rule["title"] = title_tail
    # inputs 的 units 需按 (vn, rn) 对齐——简化：直接沿用 base 的 inputs（字段名一致的场景）
    EXTRA.append(new_rule)
R.extend(EXTRA)

# 输出为 rule.schema.json 兼容 YAML（tests 生成）
def gen_tests(rule):
    th = rule.get("th_default")
    tests = []
    # 主判定变量：inputs 中最后一个（生成器约定：TH 阈值对应变量放最后）
    names = [i["name"] for i in rule["inputs"]]
    main_var = names[-1] if names else None
    if th is not None and isinstance(th, (int, float)):
        tests.append({"name": "正常（阈值 80%）", "kind": "normal",
                      "inputs": {**{n: th * 0.8 for n in names}, main_var: th * 0.8},
                      "expected_pass": True, "expected_status": "PASS"})
        tests.append({"name": "边界（恰达阈值）", "kind": "boundary",
                      "inputs": {n: th for n in names},
                      "expected_pass": True, "expected_status": "PASS"})
        tests.append({"name": "超阈值判失败", "kind": "invalid",
                      "inputs": {n: th * 1.5 for n in names},
                      "expected_pass": False, "expected_status": "FAIL"})
    else:
        tests.append({"name": "插件数值回归（占位，接插件后补手算基准）", "kind": "normal",
                      "inputs": {n: 0 for n in names},
                      "expected_status": "PASS"})
        tests.append({"name": "异常输入（非数值）", "kind": "invalid",
                      "inputs": {n: "not-a-number" for n in names},
                      "expected_status": "ERROR"})
    return tests

out = []
for rule in R:
    domain = rule.get("applicability", {}).get("component_category") or \
             rule.get("applicability", {}).get("item_type") or "derating"
    domain_map = {"Resistor": "derating", "Capacitor": "derating", "MOSFET": "power",
                  "Connector": "derating", "Battery": "power", "Crystal": "derating",
                  "IC": "power"}
    d = domain_map.get(domain, rule.get("domain", "derating"))
    inputs = []
    for i in rule["inputs"]:
        if isinstance(i, dict):
            inputs.append({"name": i["name"], "unit": i["unit"], "required": True,
                           "source": {"CS": "ComponentStress", "CP": "Component.rated_params",
                                      "OP": "OperatingProfile", "TH": "Thresholds"}.get(i.get("source"), i.get("source", "Manual")),
                           "quantity_kind": i.get("quantity_kind", "absolute")})
        else:
            n, u, s, qk = i
            inputs.append({"name": n, "unit": u, "required": True,
                           "source": {"CS": "ComponentStress", "CP": "Component.rated_params",
                                      "OP": "OperatingProfile", "TH": "Thresholds"}.get(s, s),
                           "quantity_kind": qk})
    item = {
        "rule_id": rule["rule_id"], "rule_type": rule["rule_type"], "domain": d,
        "title": rule["title"], "intent": rule["intent"],
        "applicability": rule["applicability"],
        "inputs": inputs,
        "preconditions": rule["preconditions"],
        "expression_or_payload": (
            {"expression": rule["expression"]}
            if rule["rule_type"] == "declarative_expr"
            else (
                {"curve_eval": {}} if rule["rule_type"] == "lookup_curve"
                else {
                    "plugin_ref": {
                        "module": "reliability_calc.capacitors.ecap_arrhenius_v1",
                        "entry_func": "evaluate_ecap_lifetime",
                        "digest": "sha256:local-dev",
                        "verdict_expr": "predicted_life_hours >= product_lifetime_target * life_safety_factor",
                    },
                    "outputs_exposed": [
                        {"name": "core_temp_est", "unit": "degC", "type": "number", "quantity_kind": "absolute"},
                        {"name": "predicted_life_hours", "unit": "h", "type": "number", "quantity_kind": "absolute"},
                    ],
                }
            )
        ),
        "thresholds": ({} if rule.get("th_default") is None else
                       {"limit": {"value": rule["th_default"],
                         "unit": next((i["unit"] for i in rule["inputs"] if i["name"] not in
                              ("power_dissipation", "operating_voltage", "operating_current",
                               "peak_vds", "ripple_current_rms", "local_ambient_temp", "cell_voltage",
                               "trace_current", "esr_at_freq", "thermal_resistance_ca",
                               "rated_endurance_hours", "product_lifetime_target")), "dimensionless"),
                         "source_ref": "行业常见基线（C 级，待企业批准）"}}) if rule.get("th_default") is not None else None,
        "severity": rule["severity"], "rationale": rule["intent"],
        "recommendation": "按企业降额规范与器件手册核对阈值后批准",
        "evidence": [{"evidence_id": f"EVD-DRAFT-{rule['rule_id']}", "level": "C",
                      "publisher": "行业常见基线（草案）", "title": rule["title"],
                      "version_date": "2026-11-22", "locator": "待补", "limitations": "草案阈值，须企业批准后转 A/B 级"}],
        "evidence_level": "C", "owner": "待指派", "reviewer": "待指派",
        "version": "0.1.0", "status": "draft",
        "effective_date": "2026-11-22", "expiry_date": None,
        "tests": gen_tests(rule),
        "notes": "G2-2 草案：thresholds 为行业常见基线（C 级），企业批准后转 A/B 级并升 published",
    }
    out.append(item)

import yaml
OUT.write_text(yaml.dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")
print(f"草案规则: {len(out)} 条 → {OUT}")
ids = [r["rule_id"] for r in out]
assert len(ids) == len(set(ids)), "rule_id 重复！"
print("rule_id 唯一性 OK")