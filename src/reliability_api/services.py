import hashlib, json
from datetime import datetime, timezone
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy.orm import Session
from .models import Rule, RuleVersion, AuditEvent
from reliability_engine.executor import RuleExecutor

class ContractError(ValueError):
    def __init__(self, code, message): self.code, self.message = code, message; super().__init__(message)

def validate_rule(definition: dict):
    from pathlib import Path
    schema_path = Path(__file__).resolve().parent / "schema" / "rule.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(definition), key=lambda e: list(e.path))
    if errors:
        e=errors[0]; loc=".".join(map(str,e.path)) or "$"
        raise ContractError("RULE_SCHEMA_INVALID", f"{loc}: {e.message}")

def digest(definition):
    raw=json.dumps(definition,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()

def create_rule(db: Session, definition: dict, actor: str):
    validate_rule(definition)
    rid=definition["rule_id"]
    if db.query(Rule).filter_by(rule_id=rid).first(): raise ContractError("RULE_ALREADY_EXISTS", f"Rule {rid} already exists; create a new version instead")
    ver=str(definition.get("version","1.0.0")); status=definition.get("status","draft")
    if status!="draft": raise ContractError("INITIAL_STATUS_MUST_BE_DRAFT", "New rules must enter as draft")
    rule=Rule(rule_id=rid,domain=definition["domain"],title=definition["title"],latest_version=ver)
    rv=RuleVersion(version=ver,status="draft",definition=definition,content_hash=digest(definition),created_by=actor)
    rule.versions.append(rv); db.add(rule)
    db.flush()
    audit(db,actor,"rule.create","rule_version",rv.id,{"rule_id":rid,"version":ver})
    db.commit(); db.refresh(rv)
    return rule,rv

def audit(db, actor, action, resource_type, resource_id, details=None):
    db.add(AuditEvent(actor=actor,action=action,resource_type=resource_type,resource_id=resource_id,details=details or {}))

def execute_rule(definition, inputs):
    return RuleExecutor().execute(definition, inputs)
