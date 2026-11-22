class RuleEngineError(Exception):
    """Base error carrying a stable machine-readable code."""
    code = "RULE_ENGINE_ERROR"

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        if code:
            self.code = code


class ParseError(RuleEngineError):
    code = "DSL_PARSE_ERROR"


class EvaluationError(RuleEngineError):
    code = "DSL_EVALUATION_ERROR"


class UnitError(RuleEngineError):
    code = "UNIT_ERROR"


class DimensionMismatch(UnitError):
    code = "DIMENSION_MISMATCH"


class MissingInput(EvaluationError):
    code = "INPUT_MISSING"


class PluginError(RuleEngineError):
    code = "PLUGIN_ERROR"
