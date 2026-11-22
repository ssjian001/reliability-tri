"""Small, explicit unit engine for reliability-rule evaluation.

SI symbols are case-sensitive. Absolute temperature is represented in K;
temperature differences use a distinct dimension and never accept degC/degF.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Mapping
from .errors import UnitError, DimensionMismatch

@dataclass(frozen=True)
class UnitDef:
    dimension: str
    scale: float = 1.0
    offset: float = 0.0  # canonical = value * scale + offset

UNITS: dict[str, UnitDef] = {
    "1": UnitDef("dimensionless"),
    "V": UnitDef("voltage"), "mV": UnitDef("voltage", 1e-3), "uV": UnitDef("voltage", 1e-6), "kV": UnitDef("voltage", 1e3),
    "A": UnitDef("current"), "mA": UnitDef("current", 1e-3), "uA": UnitDef("current", 1e-6), "kA": UnitDef("current", 1e3),
    "W": UnitDef("power"), "mW": UnitDef("power", 1e-3), "uW": UnitDef("power", 1e-6), "kW": UnitDef("power", 1e3),
    "Ohm": UnitDef("resistance"), "ohm": UnitDef("resistance"), "mOhm": UnitDef("resistance", 1e-3), "kOhm": UnitDef("resistance", 1e3), "MOhm": UnitDef("resistance", 1e6),
    "F": UnitDef("capacitance"), "mF": UnitDef("capacitance", 1e-3), "uF": UnitDef("capacitance", 1e-6), "nF": UnitDef("capacitance", 1e-9), "pF": UnitDef("capacitance", 1e-12),
    "H": UnitDef("inductance"), "mH": UnitDef("inductance", 1e-3), "uH": UnitDef("inductance", 1e-6),
    "Hz": UnitDef("frequency"), "kHz": UnitDef("frequency", 1e3), "MHz": UnitDef("frequency", 1e6), "GHz": UnitDef("frequency", 1e9),
    "s": UnitDef("time"), "ms": UnitDef("time", 1e-3), "us": UnitDef("time", 1e-6), "min": UnitDef("time", 60), "h": UnitDef("time", 3600), "day": UnitDef("time", 86400),
    "J": UnitDef("energy"), "mJ": UnitDef("energy", 1e-3), "Wh": UnitDef("energy", 3600), "mWh": UnitDef("energy", 3.6),
    "mAh": UnitDef("capacity_charge", 3.6), "Ah": UnitDef("capacity_charge", 3600), "C": UnitDef("capacity_charge"),
    "m": UnitDef("length"), "mm": UnitDef("length", 1e-3), "um": UnitDef("length", 1e-6), "mil": UnitDef("length", 2.54e-5),
    "Pa": UnitDef("pressure"), "kPa": UnitDef("pressure", 1e3), "atm": UnitDef("pressure", 101325),
    "Bps": UnitDef("flow_rate"), "kg": UnitDef("mass"), "g": UnitDef("mass", 1e-3), "mg": UnitDef("mass", 1e-6),
    "cycle": UnitDef("cycle_count"), "cycles": UnitDef("cycle_count"),
    "K": UnitDef("temperature"), "degC": UnitDef("temperature", 1, 273.15), "degF": UnitDef("temperature", 5/9, 255.3722222222222),
    "deltaK": UnitDef("temperature_difference"), "deltaC": UnitDef("temperature_difference"), "K_delta": UnitDef("temperature_difference"), "degC_delta": UnitDef("temperature_difference"), "degF_delta": UnitDef("temperature_difference", 5/9),
    "K/W": UnitDef("thermal_resistance"), "degC_per_W": UnitDef("thermal_resistance"),
    "%": UnitDef("dimensionless", 0.01), "ratio": UnitDef("dimensionless"), "ppm": UnitDef("dimensionless", 1e-6),
}

# Explicit aliases from the V1.1 unit dictionary. Symbol matching remains exact;
# only these natural-language aliases are case-insensitive.
EXACT_ALIASES = {
    "°C":"degC", "℃":"degC", "celsius":"degC", "摄氏度":"degC",
    "°F":"degF", "fahrenheit":"degF", "华氏度":"degF",
    "Ω":"Ohm", "欧姆":"Ohm", "欧":"Ohm", "µV":"uV", "microvolt":"uV",
    "µA":"uA", "microamp":"uA", "µW":"uW", "microwatt":"uW",
    "µF":"uF", "microfarad":"uF", "微法":"uF", "µH":"uH", "microhenry":"uH",
    "µs":"us", "microsecond":"us", "微秒":"us", "µm":"um", "micrometer":"um", "微米":"um",
    "millivolt":"mV", "毫伏":"mV", "ampere":"A", "amps":"A", "安培":"A",
    "milliamp":"mA", "毫安":"mA", "watt":"W", "瓦特":"W", "瓦":"W",
    "milliwatt":"mW", "毫瓦":"mW", "farad":"F", "法拉":"F", "millifarad":"mF",
    "nanofarad":"nF", "picofarad":"pF", "milliohm":"mOhm", "毫欧":"mOhm",
    "kiloohm":"kOhm", "kilohm":"kOhm", "千欧":"kOhm", "megaohm":"MOhm", "兆欧":"MOhm",
    "henry":"H", "亨利":"H", "millihenry":"mH", "hertz":"Hz", "赫兹":"Hz",
    "kilohertz":"kHz", "megahertz":"MHz", "gigahertz":"GHz", "second":"s", "sec":"s", "秒":"s",
    "millisecond":"ms", "毫秒":"ms", "hour":"h", "hr":"h", "小时":"h", "minute":"min", "分钟":"min",
    "joule":"J", "焦耳":"J", "millijoule":"mJ", "watthour":"Wh", "瓦时":"Wh",
    "milliwatthour":"mWh", "毫安时":"mAh", "安时":"Ah", "coulomb":"C", "库仑":"C",
    "kilogram":"kg", "千克":"kg", "gram":"g", "克":"g", "milligram":"mg", "毫克":"mg",
    "meter":"m", "米":"m", "millimeter":"mm", "毫米":"mm", "mil":"mil", "mils":"mil", "密耳":"mil",
    "pascal":"Pa", "帕斯卡":"Pa", "kilopascal":"kPa", "标准大气压":"atm",
    "cycles":"cycle", "次":"cycle", "循环":"cycle", "dimensionless":"1", "无量纲":"1",
    "比例":"ratio", "倍率":"ratio", "percent":"%", "百分比":"%", "ppm":"ppm",
    "kelvin":"K", "开尔文":"K", "delta_K":"K_delta", "ΔK":"K_delta",
    "delta_degC":"degC_delta", "Δ°C":"degC_delta", "delta_degF":"degF_delta", "Δ°F":"degF_delta",
    "kelvin_per_watt":"K/W", "K_per_W":"K/W", "°C/W":"degC_per_W", "℃/W":"degC_per_W",
    "bytes_per_second":"Bps"
}
TEXT_ALIASES = {k.lower():v for k,v in EXACT_ALIASES.items() if k.isascii() and k.isalpha()}

def resolve_unit(unit: str) -> str:
    if unit in UNITS: return unit
    if unit in EXACT_ALIASES: return EXACT_ALIASES[unit]
    # Case-insensitivity is limited to explicit word aliases, never SI symbols.
    if isinstance(unit,str) and unit.lower() in TEXT_ALIASES: return TEXT_ALIASES[unit.lower()]
    raise UnitError(f"Unknown or case-mismatched unit: {unit}", code="UNKNOWN_UNIT")

# SI base-dimension vectors enable physically meaningful compound arithmetic.
_DIM_VECTORS = {
    "dimensionless": {}, "ratio": {},
    "mass": {"M":1}, "length": {"L":1}, "time": {"T":1},
    "current": {"I":1}, "temperature_difference": {"Theta":1},
    "temperature": {"Theta_abs":1}, "cycle_count": {"Cycle":1},
    "flow_rate": {"Byte":1,"T":-1},
    "frequency": {"T":-1},
    "voltage": {"M":1,"L":2,"T":-3,"I":-1},
    "power": {"M":1,"L":2,"T":-3},
    "resistance": {"M":1,"L":2,"T":-3,"I":-2},
    "capacitance": {"M":-1,"L":-2,"T":4,"I":2},
    "inductance": {"M":1,"L":2,"T":-2,"I":-2},
    "energy": {"M":1,"L":2,"T":-2},
    "capacity_charge": {"I":1,"T":1},
    "pressure": {"M":1,"L":-1,"T":-2},
    "thermal_resistance": {"Theta":1,"M":-1,"L":-2,"T":3},
}
_VECTOR_NAMES = {tuple(sorted((k,v) for k,v in vec.items() if v)): name for name,vec in _DIM_VECTORS.items()}

def _dimension_vector(name):
    if name in _DIM_VECTORS: return dict(_DIM_VECTORS[name])
    if name.startswith("derived{") and name.endswith("}"):
        body=name[8:-1]; out={}
        for item in body.split(","):
            if item:
                key,val=item.split(":",1); out[key]=int(val)
        return out
    return {name:1}

def _combine_dimensions(a, b, sign):
    v=_dimension_vector(a)
    for key,power in _dimension_vector(b).items(): v[key]=v.get(key,0)+sign*power
    v={k:p for k,p in v.items() if p}
    key=tuple(sorted(v.items()))
    return _VECTOR_NAMES.get(key, "derived{" + ",".join(f"{k}:{v[k]}" for k in sorted(v)) + "}")

@dataclass(frozen=True)
class Quantity:
    value: float  # canonical SI value
    dimension: str
    display_unit: str = "1"

    @classmethod
    def of(cls, value: float, unit: str = "1") -> "Quantity":
        unit = resolve_unit(unit)
        if isinstance(value, bool): raise UnitError("Boolean is not a numeric quantity")
        if not math.isfinite(float(value)):
            raise UnitError("Quantity must be finite")
        u = UNITS[unit]
        canonical = float(value) * u.scale + u.offset
        if not math.isfinite(canonical): raise UnitError("Converted quantity must be finite")
        return cls(canonical, u.dimension, unit)

    def in_unit(self, unit: str) -> float:
        unit = resolve_unit(unit)
        u = UNITS[unit]
        if u.dimension != self.dimension:
            raise DimensionMismatch(f"Cannot convert {self.dimension} to {u.dimension}")
        return (self.value - u.offset) / u.scale

    def _same(self, other: "Quantity") -> None:
        if not isinstance(other, Quantity) or self.dimension != other.dimension:
            raise DimensionMismatch(f"Incompatible dimensions: {self.dimension} and {getattr(other, 'dimension', type(other).__name__)}")
        if self.dimension == "temperature":
            # Absolute temperatures may be compared/subtracted, but never added.
            return

    def add(self, other: "Quantity") -> "Quantity":
        self._same(other)
        if self.dimension == "temperature":
            raise UnitError("Adding two absolute temperatures is undefined; use temperature_difference")
        return Quantity(self.value + other.value, self.dimension, self.display_unit)

    def sub(self, other: "Quantity") -> "Quantity":
        self._same(other)
        dim = "temperature_difference" if self.dimension == "temperature" else self.dimension
        return Quantity(self.value - other.value, dim, "deltaK" if dim == "temperature_difference" else self.display_unit)

    def mul(self, other: "Quantity") -> "Quantity":
        if self.dimension == "temperature" or other.dimension == "temperature":
            raise UnitError("Multiplication of absolute temperature is not supported")
        if self.dimension == "dimensionless": return Quantity(self.value * other.value, other.dimension, other.display_unit)
        if other.dimension == "dimensionless": return Quantity(self.value * other.value, self.dimension, self.display_unit)
        return Quantity(self.value * other.value, _combine_dimensions(self.dimension,other.dimension,1), "1")

    def div(self, other: "Quantity") -> "Quantity":
        if other.value == 0: raise UnitError("Division by zero")
        if self.dimension == "temperature" or other.dimension == "temperature":
            raise UnitError("Division involving absolute temperature is not supported")
        if other.dimension == "dimensionless": return Quantity(self.value / other.value, self.dimension, self.display_unit)
        if self.dimension == other.dimension: return Quantity(self.value / other.value, "dimensionless", "1")
        return Quantity(self.value / other.value, _combine_dimensions(self.dimension,other.dimension,-1), "1")

    def compare(self, other: "Quantity", op: str) -> bool:
        self._same(other)
        return {"<": self.value < other.value, "<=": self.value <= other.value, ">": self.value > other.value, ">=": self.value >= other.value, "==": self.value == other.value, "!=": self.value != other.value}[op]

    def __bool__(self):
        raise UnitError("A quantity cannot be used as a boolean")

def validate_unit_aliases(alias_map: Mapping[str, str]) -> list[str]:
    """Validate exact aliases only; case folding is intentionally forbidden."""
    seen: dict[str, str] = {}
    collisions = []
    for unit, definition in UNITS.items():
        for alias in [unit, *alias_map.get(unit, [])]:
            if alias in seen and seen[alias] != unit:
                collisions.append(f"{alias}: {seen[alias]} vs {unit}")
            else: seen[alias] = unit
    return collisions
