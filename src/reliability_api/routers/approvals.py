from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..db import get_db
from ..dependencies import get_actor
from ..models import RuleVersion, CurveArtifact, Approval, AuditEvent
from ..schemas import ApprovalCreate

router=APIRouter(prefix="/v1/approvals",tags=["approvals"])

@router.post("",status_code=201)
def decide(payload: ApprovalCreate,db: Session=Depends(get_db),actor: str=Depends(get_actor)):
    rv=None; curve=None
    if payload.target_type=="rule_version":
        rv=db.query(RuleVersion).filter_by(id=payload.target_id).first()
        if not rv: raise HTTPException(404,detail={"error_code":"APPROVAL_TARGET_NOT_FOUND","message":"Rule version not found"})
        if payload.action=="publish" and rv.status!="tested":
            raise HTTPException(409,detail={"error_code":"RULE_TEST_GATE_REQUIRED","message":"Rule must pass its embedded test suite before publication"})
        if rv.status not in ("draft","in_review","tested","shadow"):
            raise HTTPException(409,detail={"error_code":"RULE_STATUS_TRANSITION_INVALID","message":f"Cannot approve a rule in status {rv.status}"})
        owner=rv.created_by
    else:
        curve=db.query(CurveArtifact).filter_by(id=payload.target_id).first()
        if not curve: raise HTTPException(404,detail={"error_code":"APPROVAL_TARGET_NOT_FOUND","message":"Curve artifact not found"})
        if curve.approved: raise HTTPException(409,detail={"error_code":"CURVE_ALREADY_APPROVED","message":"Curve artifact is already approved"})
        owner=curve.created_by
    if actor==owner: raise HTTPException(403,detail={"error_code":"SELF_APPROVAL_FORBIDDEN","message":"Creator cannot approve their own artifact"})
    if payload.action=="publish" and payload.decision!="approved":
        raise HTTPException(422,detail={"error_code":"APPROVAL_DECISION_MISMATCH","message":"publish action requires approved decision"})
    if payload.action=="reject" and payload.decision!="rejected":
        raise HTTPException(422,detail={"error_code":"APPROVAL_DECISION_MISMATCH","message":"reject action requires rejected decision"})
    approval=Approval(target_type=payload.target_type,target_id=payload.target_id,action=payload.action,decision=payload.decision,approver=actor,comment=payload.comment)
    if rv:
        if payload.action=="publish":
            rv.status="published"; rv.published_at=datetime.now(timezone.utc)
        else: rv.status="draft"
    else:
        curve.approved=(payload.action=="publish")
    target_id=rv.id if rv else curve.id; db.add(approval); db.add(AuditEvent(actor=actor,action="artifact.approval",resource_type=payload.target_type,resource_id=target_id,details={"decision":payload.decision,"action":payload.action}))
    db.commit(); db.refresh(approval)
    return {"approval_id":approval.id,"target_id":target_id,"decision":approval.decision,"rule_status":rv.status if rv else None,"curve_approved":curve.approved if curve else None,"approver":actor}
