"""Unit Engine：加载 unit_dictionary.yaml，执行别名识别/维度检查/quantity_kind 双轨归一。

规则（02 §2.1、01 §3.1）：
- SI 符号区分大小写（mW/MW 不折叠）；自然语言别名不敏感但歧义须显式维度。
- 温度双轨：absolute 归一到 K（degC 带 +273.15 偏移），delta 归一到 K 差值（无偏移）。
- 错误码：UNKNOWN_UNIT / DIMENSION_MISMATCH / TEMPERATURE_SCALE_AMBIGUOUS。
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

import yaml

DIMENSION_MISMATCH = "DIMENSION_MISMATCH"
UNKNOWN_UNIT = "UNKNOWN_UNIT"
TEMPERATURE_SCALE_AMBIGUOUS = "TEMPERATURE_SCALE_AMBIGUOUS"

# 温度类维度（quantity_kind 语义特殊）
TEMP_DIMS_ABS = {"temperature_abs"}
TEMP_DIMS_DELTA = {"temperature_delta"}


class UnitError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass
class Normalized:
    value: float
    unit: str          # canonical
    dimension: str
    quantity_kind: str  # absolute / delta


class UnitEngine:
    def __init__(self, dict_path: str | pathlib.Path | None = None):
        path = dict_path or pathlib.Path(__file__).resolve().parents[2] / "V1.1/attachments/unit_dictionary.yaml"
        self.spec = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))
        self.dimensions: dict[str, dict] = self.spec["dimensions"]
        # 别名索引：区分大小写（SI 符号）+ 不区分大小写（自然语言别名，标记 ambiguous 集合）
        self._exact: dict[str, tuple[str, str]] = {}
        self._ci: dict[str, set[tuple[str, str]]] = {}
        for dim, spec in self.dimensions.items():
            for unit, meta in spec["units"].items():
                self._exact.setdefault(unit, (dim, unit))
                for alias in meta.get("aliases", []):
                    self._exact.setdefault(alias, (dim, unit))
                    self._ci.setdefault(alias.lower(), set()).add((dim, unit))

    def _lookup(self, unit: str, dimension: str | None) -> tuple[str, str, dict]:
        """返回 (dimension, unit, meta)。歧义且无显式维度 → TEMPERATURE/UNKNOWN 错误。"""
        exact = self._exact.get(unit)
        if exact:
            dim, u = exact
            if dimension and dim != dimension:
                raise UnitError(DIMENSION_MISMATCH, f"{unit} 属于 {dim}，与显式维度 {dimension} 冲突")
            return dim, u, self.dimensions[dim]["units"][u]
        ci = self._ci.get(unit.lower())
        if ci:
            if len(ci) == 1:
                dim, u = next(iter(ci))
                return dim, u, self.dimensions[dim]["units"][u]
            if dimension:
                hit = [(d, u) for d, u in ci if d == dimension]
                if hit:
                    dim, u = hit[0]
                    return dim, u, self.dimensions[dim]["units"][u]
            raise UnitError(
                TEMPERATURE_SCALE_AMBIGUOUS if any(d.startswith("temperature") for d, _ in ci)
                else UNKNOWN_UNIT,
                f"别名 {unit} 跨维度歧义 {sorted(ci)}——须显式指定 dimension")
        raise UnitError(UNKNOWN_UNIT, f"未知单位: {unit}")

    def normalize(self, value: float, unit: str, quantity_kind: str | None = None,
                  dimension: str | None = None) -> Normalized:
        """归一到 canonical。温度类按 quantity_kind 选 temperature_abs/temperature_delta。"""
        dim, u, meta = self._lookup(unit, dimension)
        if dim.startswith("temperature"):
            kind = quantity_kind or meta.get("quantity_kind")
            if not kind:
                raise UnitError(TEMPERATURE_SCALE_AMBIGUOUS,
                                f"{unit} 需要显式 quantity_kind (absolute/delta)")
            if kind == "absolute" and dim == "temperature_delta":
                dim = "temperature_abs"; u = u.replace("_delta", "")
                meta = self.dimensions[dim]["units"].get(u, meta)
            if kind == "delta" and dim == "temperature_abs":
                dim = "temperature_delta"; u = u + "_delta" if u in ("K", "degC") else "degC_delta"
                meta = self.dimensions[dim]["units"].get(u, meta)
            to_si = meta["to_si"]
            if u == "degC" and dim == "temperature_abs":
                return Normalized(float(value) + 273.15, "K", dim, "absolute")
            if u == "degF" and dim == "temperature_abs":
                c = (float(value) - 32) / 1.8
                return Normalized(c + 273.15, "K", dim, "absolute")
            if u == "degF" and dim == "temperature_delta":
                return Normalized(float(value) / 1.8, "K", dim, "delta")
            return Normalized(float(value) * float(to_si), "K", dim, kind)  # delta 归一 norm_unit 一律 K（复审 P2）
        to_si = meta["to_si"]
        return Normalized(float(value) * float(to_si), u, dim, meta.get("quantity_kind", "absolute"))

    def to_canonical_in_dim(self, value: float, unit: str, dimension: str | None = None,
                            quantity_kind: str | None = None) -> Normalized:
        """归一到该维度 canonical 单位（如 temperature_abs→K、voltage→V）。"""
        n = self.normalize(value, unit, quantity_kind, dimension)
        return n
