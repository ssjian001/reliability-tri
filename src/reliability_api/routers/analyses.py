from datetime import datetime, timezone
import hashlib, json, re
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from ..db import get_db
from ..dependencies import get_actor
from ..config import settings
from ..models import Rule, RuleVersion, AnalysisRun, Finding, CurveArtifact, AuditEvent, IdempotencyRecord
from ..schemas import AnalysisRequest
from ..services import execute_rule
from reliability_engine.curves import CurveRepository
from reliability_engine.executor import RuleExecutor

router=APIRouter(prefix="/v1/analyses",tags=["analyses"])

def _executor(db):
    curves=CurveRepository()
    for c in db.query(CurveArtifact).filter_by(approved=True).all():
        curves.register(c.id,x_unit=c.x_unit,y_unit=c.y_unit,z_unit=c.z_unit,x_values=c.x_values,y_values=c.y_values,z_values=c.z_values,interpolation=c.interpolation)
    return RuleExecutor(curves=curves)

@router.post("/derating",status_code=200)
def start_derating(payload: AnalysisRequest,db: Session=Depends(get_db),actor: str=Depends(get_actor),idempotency_key: str|None=Header(default=None,alias="Idempotency-Key")):
    request_doc={"inputs":payload.inputs,"rule_ids":payload.rule_ids}
    request_hash=hashlib.sha256(json.dumps(request_doc,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    if idempotency_key:
        if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}",idempotency_key):
            raise HTTPException(400,detail={"error_code":"IDEMPOTENCY_KEY_INVALID","message":"Idempotency-Key must be 8-128 safe ASCII characters"})
        prior=db.query(IdempotencyRecord).filter_by(key=idempotency_key).first()
        if prior:
            if prior.request_hash!=request_hash:
                raise HTTPException(409,detail={"error_code":"IDEMPOTENCY_CONFLICT","message":"Idempotency-Key was already used with a different request"})
            return prior.response_payload
    q=db.query(Rule,RuleVersion).join(RuleVersion,Rule.id==RuleVersion.rule_pk).filter(RuleVersion.status=="published")
    if payload.rule_ids: q=q.filter(Rule.rule_id.in_(payload.rule_ids))
    else: q=q.filter(Rule.domain.in_(["derating","power","thermal"]))
    rows=q.order_by(Rule.rule_id).limit(settings.max_sync_rules+1).all()
    if payload.rule_ids and len(rows)!=len(set(payload.rule_ids)):
        raise HTTPException(422,detail={"error_code":"RULE_NOT_PUBLISHED_OR_NOT_FOUND","message":"One or more requested rules are missing or not published"})
    if not rows:
        raise HTTPException(422,detail={"error_code":"NO_PUBLISHED_RULES","message":"No published rules matched this analysis request"})
    if len(rows)>settings.max_sync_rules: raise HTTPException(413,detail={"error_code":"ANALYSIS_RULE_LIMIT","message":"Too many rules for synchronous execution"})
    run=AnalysisRun(analysis_type="derating",status="running",input_payload=payload.inputs,requested_by=actor)
    db.add(run); db.flush(); executor=_executor(db); counts={"pass":0,"fail":0,"error":0,"skipped":0}
    for rule,rv in rows:
        result=executor.execute(rv.definition,payload.inputs)
        st=result.get("status","error"); counts[st]=counts.get(st,0)+1
        db.add(Finding(run_id=run.id,rule_id=rule.rule_id,rule_version=rv.version,severity=rv.definition.get("severity","info"),status=st,result_payload=result.get("result"),error_code=result.get("error_code")))
    run.status="completed"; run.result_summary={"rules_evaluated":len(rows),"counts":counts}; run.completed_at=datetime.now(timezone.utc)
    db.add(AuditEvent(actor=actor,action="analysis.derating",resource_type="analysis_run",resource_id=run.id,details=run.result_summary))
    response={"run_id":run.id,"analysis_type":run.analysis_type,"status":run.status,"summary":run.result_summary,"created_at":run.created_at.isoformat()}
    if idempotency_key: db.add(IdempotencyRecord(key=idempotency_key,request_hash=request_hash,response_payload=response,status_code=200))
    db.commit(); db.refresh(run)
    return response

@router.get("/{run_id}")
def get_analysis(run_id: str,db: Session=Depends(get_db)):
    run=db.query(AnalysisRun).filter_by(id=run_id).first()
    if not run: raise HTTPException(404,detail={"error_code":"ANALYSIS_NOT_FOUND","message":"Analysis run not found"})
    return {"run_id":run.id,"analysis_type":run.analysis_type,"status":run.status,"summary":run.result_summary,"created_at":run.created_at,"completed_at":run.completed_at}

@router.get("/{run_id}/findings")
def get_findings(run_id: str,limit: int=100,offset: int=0,db: Session=Depends(get_db)):
    if not db.query(AnalysisRun).filter_by(id=run_id).first(): raise HTTPException(404,detail={"error_code":"ANALYSIS_NOT_FOUND","message":"Analysis run not found"})
    q=db.query(Finding).filter_by(run_id=run_id); total=q.count(); rows=q.order_by(Finding.rule_id).offset(offset).limit(max(1,min(limit,200))).all()
    return {"items":[{"finding_id":f.id,"rule_id":f.rule_id,"rule_version":f.rule_version,"severity":f.severity,"status":f.status,"result":f.result_payload,"error_code":f.error_code} for f in rows],"total":total,"limit":limit,"offset":offset}
