"""受限 DSL：白名单 Parser/AST + 确定性求值（01 §3.1；simpleeval 沙箱）。

白名单：比较 > >= < <= == !=、逻辑 AND OR NOT、算术 + - * /、受限 IF(cond, a, b)。
禁止函数调用（除 IF）、属性访问、下标、推导式、lambda、import。
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
IF = "IF"


def validate(expr: str, variables: list[str]) -> None:
    """静态校验：白名单节点 + 变量名 + 禁函数调用。违规抛 ValueError。"""
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"DSL 违规节点: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in variables and node.id != "null":
            raise ValueError(f"未知变量: {node.id}")
        if isinstance(node, ast.Call) and not (
            isinstance(node.func, ast.Name) and node.func.id == IF
        ):
            raise ValueError("禁止函数调用（仅允许 IF）")


class DSLEvaluator:
    """确定性求值器。缺失变量求值时抛 MISSING_INPUT。"""

    def __init__(self, variable_values: dict[str, float], extra_funcs: dict | None = None):
        self.values = dict(variable_values)
        names = dict(self.values)
        names[IF] = lambda c, a, b: a if c else b
        names["null"] = None
        self.eval_ = simpleeval.SimpleEval(names=names, functions=dict(extra_funcs or {}))
        self._extra_funcs = dict(extra_funcs or {})

    def evaluate(self, expr: str, variables: list[str]) -> float | bool:
        validate(expr, list(set(variables) | set(self.values) | {IF}))
        self.eval_.names = dict(self.values)
        self.eval_.names[IF] = lambda c, a, b: (a if c else b)
        self.eval_.names["null"] = None
        return self.eval_.eval(expr)

    def with_values(self, values: dict[str, float]) -> "DSLEvaluator":
        self.values = dict(values)
        return self
