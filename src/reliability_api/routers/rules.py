from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..dependencies import get_actor
from ..models import Rule, RuleVersion, CurveArtifact
from reliability_engine.curves import CurveRepository
from reliability_engine.executor import RuleExecutor
from ..schemas import RuleCreate, RuleTestRequest
from ..services import create_rule, ContractError, execute_rule, audit

router=APIRouter(prefix="/v1/rules",tags=["rules"])

def pack(rule, rv):
    return {"rule_id":rule.rule_id,"domain":rule.domain,"title":rule.title,"version":rv.version,"status":rv.status,"version_id":rv.id,"content_hash":rv.content_hash,"definition":rv.definition,"created_at":rv.created_at}

@router.post("",status_code=201)
def create(payload: RuleCreate, db: Session=Depends(get_db), actor: str=Depends(get_actor)):
    try: rule,rv=create_rule(db,payload.definition,actor)
    except ContractError as e: raise HTTPException(409 if e.code=="RULE_ALREADY_EXISTS" else 422,detail={"error_code":e.code,"message":e.message})
    return pack(rule,rv)

@router.get("")
def list_rules(domain: str|None=None, status: str|None=None, limit: int=100, offset: int=0, db: Session=Depends(get_db)):
    limit=max(1,min(limit,200)); q=db.query(Rule,RuleVersion).join(RuleVersion,Rule.id==RuleVersion.rule_pk)
    if domain: q=q.filter(Rule.domain==domain)
    if status: q=q.filter(RuleVersion.status==status)
    total=q.count(); rows=q.order_by(Rule.rule_id,RuleVersion.created_at.desc()).offset(offset).limit(limit).all()
    return {"items":[pack(r,v) for r,v in rows],"total":total,"limit":limit,"offset":offset}


@router.post("/{rule_id}:validate")
def validate_rule_tests(rule_id: str,version: str|None=None,db: Session=Depends(get_db),actor: str=Depends(get_actor)):
    rule=db.query(Rule).filter_by(rule_id=rule_id).first()
    if not rule: raise HTTPException(404,detail={"error_code":"RULE_NOT_FOUND","message":"Rule not found"})
    q=db.query(RuleVersion).filter_by(rule_pk=rule.id)
    rv=q.filter_by(version=version).first() if version else q.order_by(RuleVersion.created_at.desc()).first()
    if not rv: raise HTTPException(404,detail={"error_code":"RULE_VERSION_NOT_FOUND","message":"Rule version not found"})
    if rv.status not in ("draft","tested"):
        raise HTTPException(409,detail={"error_code":"RULE_STATUS_TRANSITION_INVALID","message":f"Cannot validate a rule in status {rv.status}"})
    curves=CurveRepository()
    for c in db.query(CurveArtifact).filter_by(approved=True).all():
        curves.register(c.id,x_unit=c.x_unit,y_unit=c.y_unit,z_unit=c.z_unit,x_values=c.x_values,y_values=c.y_values,z_values=c.z_values,interpolation=c.interpolation)
    executor=RuleExecutor(curves=curves); outcomes=[]
    for case in rv.definition.get("tests",[]):
        result=executor.execute(rv.definition,case.get("inputs",{})); status=result.get("status","error")
        mapped={"pass":"PASS","fail":"FAIL","skipped":"SKIPPED_PRECONDITION","error":"ERROR"}.get(status,"ERROR")
        if status=="error" and result.get("error_code")=="INPUT_MISSING": mapped="DATA_GAP"
        expected=case.get("expected_status")
        outcomes.append({"name":case.get("name"),"expected_status":expected,"actual_status":mapped,"passed":expected==mapped,"error_code":result.get("error_code")})
    all_passed=bool(outcomes) and all(x["passed"] for x in outcomes)
    rv.status="tested" if all_passed else "draft"
    audit(db,actor,"rule.validate","rule_version",rv.id,{"all_passed":all_passed,"case_count":len(outcomes)})
    db.commit()
    return {"rule_id":rule_id,"version":rv.version,"status":rv.status,"all_passed":all_passed,"case_count":len(outcomes),"cases":outcomes}


@router.post("/{rule_id}/versions",status_code=201)
def create_version(rule_id: str,payload: RuleCreate,db: Session=Depends(get_db),actor: str=Depends(get_actor)):
    try:
        definition=payload.definition
        from ..services import validate_rule, digest
        validate_rule(definition)
        if definition.get("rule_id")!=rule_id: raise ContractError("RULE_ID_MISMATCH","definition.rule_id must match URL rule_id")
        if definition.get("status")!="draft": raise ContractError("INITIAL_STATUS_MUST_BE_DRAFT","New versions must enter as draft")
        rule=db.query(Rule).filter_by(rule_id=rule_id).first()
        if not rule: raise HTTPException(404,detail={"error_code":"RULE_NOT_FOUND","message":"Rule not found"})
        ver=str(definition.get("version",""))
        if not ver: raise ContractError("RULE_VERSION_REQUIRED","version is required")
        if db.query(RuleVersion).filter_by(rule_pk=rule.id,version=ver).first(): raise ContractError("RULE_VERSION_ALREADY_EXISTS",f"Version {ver} already exists")
        rv=RuleVersion(version=ver,status="draft",definition=definition,content_hash=digest(definition),created_by=actor)
        rule.versions.append(rv); rule.latest_version=ver
        db.add(rv); db.flush(); audit(db,actor,"rule.version.create","rule_version",rv.id,{"rule_id":rule_id,"version":ver}); db.commit(); db.refresh(rv)
        return pack(rule,rv)
    except ContractError as e:
        raise HTTPException(409 if e.code.endswith("EXISTS") else 422,detail={"error_code":e.code,"message":e.message})

@router.get("/{rule_id}")
def get_rule(rule_id: str, version: str|None=None, db: Session=Depends(get_db)):
    rule=db.query(Rule).filter_by(rule_id=rule_id).first()
    if not rule: raise HTTPException(404,detail={"error_code":"RULE_NOT_FOUND","message":"Rule not found"})
    q=db.query(RuleVersion).filter_by(rule_pk=rule.id)
    rv=q.filter_by(version=version).first() if version else q.order_by(RuleVersion.created_at.desc()).first()
    if not rv: raise HTTPException(404,detail={"error_code":"RULE_VERSION_NOT_FOUND","message":"Rule version not found"})
    return pack(rule,rv)

@router.post("/{rule_id}:test")
def test_rule(rule_id: str,payload: RuleTestRequest,version: str|None=None,db: Session=Depends(get_db),actor: str=Depends(get_actor)):
    rule=db.query(Rule).filter_by(rule_id=rule_id).first()
    if not rule: raise HTTPException(404,detail={"error_code":"RULE_NOT_FOUND","message":"Rule not found"})
    q=db.query(RuleVersion).filter_by(rule_pk=rule.id)
    rv=q.filter_by(version=version).first() if version else q.order_by(RuleVersion.created_at.desc()).first()
    if not rv: raise HTTPException(404,detail={"error_code":"RULE_VERSION_NOT_FOUND","message":"Rule version not found"})
    curves=CurveRepository()
    for c in db.query(CurveArtifact).filter_by(approved=True).all():
        curves.register(c.id,x_unit=c.x_unit,y_unit=c.y_unit,z_unit=c.z_unit,x_values=c.x_values,y_values=c.y_values,z_values=c.z_values,interpolation=c.interpolation)
    result=RuleExecutor(curves=curves).execute(rv.definition,payload.inputs)
    audit(db,actor,"rule.test","rule_version",rv.id,{"status":result.get("status"),"error_code":result.get("error_code")}); db.commit()
    return {"rule_id":rule_id,"version":rv.version,"execution":result}
