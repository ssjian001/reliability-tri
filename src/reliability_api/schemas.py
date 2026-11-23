from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class RuleCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    definition: dict[str, Any]

class RuleTestRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)

class AnalysisRequest(BaseModel):
    inputs: dict[str, Any]
    rule_ids: list[str] | None = None

class ApprovalCreate(BaseModel):
    target_type: Literal["rule_version", "curve"]
    target_id: str
    action: Literal["publish", "reject"]
    decision: Literal["approved", "rejected"]
    comment: str | None = None

class RuleVersionOut(BaseModel):
    id: str
    rule_id: str
    version: str
    status: str
    content_hash: str
    definition: dict[str, Any]
    model_config = ConfigDict(from_attributes=True)

class ErrorOut(BaseModel):
    error_code: str
    message: str
    request_id: str | None = None

class CurveCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    x_unit: str
    y_unit: str
    z_unit: str
    x_values: list[float]
    y_values: list[float]
    z_values: list[list[float]]
    interpolation: Literal["linear", "log_log_linear"] = "log_log_linear"
    source_ref: str = Field(min_length=1, max_length=500)
    checksum: str = Field(min_length=64, max_length=64)
