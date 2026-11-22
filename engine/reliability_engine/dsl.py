"""受限 DSL：Python 语法子集白名单 + 确定性求值（01 §3.1；simpleeval 沙箱）。

白名单（02 §2.1，r3-delta 定案为 Python 语法）：比较 > >= < <= == !=、逻辑 and or not、
算术 + - * /、三元条件 (a if cond else b)。禁止函数调用、属性访问、下标、lambda、import。
字面量口径：变量按 inputs 声明单位传入（MeasuredParam.decl），字面量与变量同口径可比。
"""
from __future__ import annotations

import ast

import simpleeval

ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Compare,
    ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE,
    ast.IfExp, ast.Name, ast.Load, ast.Constant,
)


def validate(expr: str, variables: list[str]) -> None:
    """静态校验：白名单节点 + 变量名 + 禁函数调用。违规抛 ValueError（→ ERROR Finding，不裸抛）。"""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"DSL 语法错误: {e.msg}") from None
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"DSL 违规节点: {type(node).__name__}")
        if isinstance(node, ast.Call):
            raise ValueError("禁止函数调用")
        if isinstance(node, ast.Name) and node.id not in variables and node.id != "null":
            raise ValueError(f"未知变量: {node.id}")


class DSLEvaluator:
    """确定性求值器。变量缺值由调用方以状态机判定（DATA_GAP），本类只求值。"""

    def __init__(self, variable_values: dict, extra_funcs: dict | None = None):
        self.values = dict(variable_values)
        names = dict(self.values)
        names["null"] = None
        self.eval_ = simpleeval.SimpleEval(names=names, functions=dict(extra_funcs or {}))
        self._extra_funcs = dict(extra_funcs or {})

    def evaluate(self, expr: str, variables: list[str]) -> float | bool:
        validate(expr, list(set(variables) | set(self.values) | {"null"}))
        self.eval_.names = dict(self.values)
        self.eval_.names["null"] = None
        return self.eval_.eval(expr)

    def with_values(self, values: dict) -> "DSLEvaluator":
        self.values = dict(values)
        return self
