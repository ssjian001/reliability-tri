"""MeasuredParam：物理量值对象（01 §5.0）。保留原值 + 归一值 + 三轴可信度。"""
from __future__ import annotations

from dataclasses import dataclass, field

from .units import UnitEngine, UnitError

PASS_REQUIRED = {"source_level": ["A", "B"], "extraction_status": ["human_verified", "measured"],
                 "applicability_status": ["in_scope"]}


import pint

_ureg = pint.UnitRegistry()
# engine 别名 → Pint 符号（温度仿射由 Pint offset units 原生处理）
_PINT = {"V": "V", "mV": "mV", "uV": "uV", "kV": "kV",
         "A": "A", "mA": "mA", "uA": "uA", "kA": "kA",
         "W": "W", "mW": "mW", "kW": "kW", "uW": "uW",
         "F": "farad", "mF": "millifarad", "uF": "microfarad", "nF": "nanofarad", "pF": "picofarad",
         "ohm": "ohm", "mOhm": "milliohm", "kOhm": "kilohm", "MOhm": "megohm",
         "H": "henry", "mH": "millihenry", "uH": "microhenry",
         "degC": "degC", "K": "kelvin", "degF": "degF",
         "Hz": "Hz", "kHz": "kHz", "MHz": "MHz", "GHz": "GHz",
         "s": "s", "ms": "ms", "us": "us", "min": "min", "h": "h",
         "J": "J", "mJ": "mJ", "Wh": "Wh", "mWh": "mWh",
         "mAh": "mAh", "Ah": "Ah", "kg": "kg", "g": "g", "mg": "mg",
         "m": "m", "mm": "mm", "um": "um", "mil": "mil",
         "Pa": "Pa", "kPa": "kPa", "atm": "atm",
         "degC_per_W": "degC/W", "K_per_W": "kelvin/watt",
         "ratio": "dimensionless", "percent": "percent", "dimensionless": "dimensionless",
         "table": "dimensionless", "Bps": "B/s", "cycles": "dimensionless"}


@dataclass
class MeasuredParam:
    raw_value: str | float
    raw_unit: str
    norm_value: float
    norm_unit: str
    quantity_kind: str            # absolute / delta
    source_type: str              # datasheet | bom | simulation | manual | assumed
    evidence_id: str | None
    source_level: str             # A / B / C / D（来源权威性）
    extraction_status: str        # human_verified / ai_unverified / measured
    applicability_status: str     # in_scope / out_of_scope / unknown
    revision: str | None = None
    effective_date: str | None = None
    applicability_note: str | None = None
    decl_unit: str | None = None       # 规则声明的单位（表达式求值口径）
    decl_value: float | None = None    # 声明单位下的数值（DSL/插件消费口径）

    def decl(self, decl_unit: str) -> "MeasuredParam":
        """返回声明单位口径的副本（Pint 仿射换算）。换算失败必须抛错——
        不得把 SI 归一值冒充声明口径值（复审 C-2：违反 02「不自动猜测」）。"""
        import dataclasses
        raw = self.raw_value if isinstance(self.raw_value, (int, float)) else None
        if raw is None:
            raise UnitError("MISSING_INPUT", f"raw_value 非数值: {self.raw_value!r}")
        src_sym = _PINT.get(self.raw_unit)
        dst_sym = _PINT.get(decl_unit)
        if src_sym is None or dst_sym is None:
            raise UnitError("UNKNOWN_UNIT", f"单位不可解析: {self.raw_unit} → {decl_unit}")
        try:
            v = _ureg.Quantity(raw, src_sym).to(dst_sym).magnitude
        except Exception as e:
            raise UnitError("DIMENSION_MISMATCH", f"{self.raw_unit} → {decl_unit}: {e}")
        return dataclasses.replace(self, decl_unit=decl_unit, decl_value=v)

    def can_support_formal_pass(self) -> bool:
        """正式 PASS 三轴同时达标（复审 P1-1：C 级不得静默 PASS）。"""
        return (self.source_level in PASS_REQUIRED["source_level"]
                and self.extraction_status in PASS_REQUIRED["extraction_status"]
                and self.applicability_status in PASS_REQUIRED["applicability_status"])


def from_dict(d: dict, engine: UnitEngine, dimension: str | None = None) -> MeasuredParam:
    """从 {"value":..,"unit":..,...} 或简写 {"value":..,"unit":..} 构造并归一。

    支持字典键：value（必填）、unit（必填）、quantity_kind、source_type、evidence_id、
    source_level、extraction_status、applicability_status、revision、effective_date、
    applicability_note、dimension（显式维度消歧义）。
    """
    qk = d.get("quantity_kind")
    try:
        n = engine.normalize(d["value"], d["unit"], qk, d.get("dimension"))
    except UnitError as e:
        if e.code == "TEMPERATURE_SCALE_AMBIGUOUS" and dimension:
            n = engine.normalize(d["value"], d["unit"], qk or ("delta" if "delta" in dimension else "absolute"), dimension)
        else:
            raise
    defaults = {"source_type": "manual", "evidence_id": None, "source_level": "D",
                "extraction_status": "ai_unverified", "applicability_status": "unknown"}
    return MeasuredParam(
        raw_value=d["value"], raw_unit=d["unit"], norm_value=n.value, norm_unit=n.unit,
        quantity_kind=n.quantity_kind or "absolute",
        source_type=d.get("source_type", defaults["source_type"]),
        evidence_id=d.get("evidence_id", defaults["evidence_id"]),
        source_level=d.get("source_level", defaults["source_level"]),
        extraction_status=d.get("extraction_status", defaults["extraction_status"]),
        applicability_status=d.get("applicability_status", defaults["applicability_status"]),
        revision=d.get("revision"), effective_date=d.get("effective_date"),
        applicability_note=d.get("applicability_note"),
    )
