import hashlib, json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..dependencies import get_actor
from ..models import CurveArtifact, AuditEvent
from ..schemas import CurveCreate
from reliability_engine.curves import CurveRepository

router=APIRouter(prefix="/v1/curves",tags=["curves"])

@router.post("",status_code=201)
def create_curve(payload: CurveCreate,db: Session=Depends(get_db),actor: str=Depends(get_actor)):
    if db.query(CurveArtifact).filter_by(id=payload.id).first(): raise HTTPException(409,detail={"error_code":"CURVE_ALREADY_EXISTS","message":"Curve ID already exists"})
    data=payload.model_dump(); supplied=data.pop("checksum")
    canonical=json.dumps({k:v for k,v in data.items() if k!="source_ref"},sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    actual=hashlib.sha256(canonical).hexdigest()
    if supplied!=actual: raise HTTPException(422,detail={"error_code":"CURVE_CHECKSUM_MISMATCH","message":"Checksum does not match canonical curve payload"})
    try:
        CurveRepository().register(payload.id,x_unit=payload.x_unit,y_unit=payload.y_unit,z_unit=payload.z_unit,x_values=payload.x_values,y_values=payload.y_values,z_values=payload.z_values,interpolation=payload.interpolation)
    except Exception as e: raise HTTPException(422,detail={"error_code":"CURVE_INVALID","message":str(e)})
    curve=CurveArtifact(**data,checksum=actual,approved=False,created_by=actor); db.add(curve); db.add(AuditEvent(actor=actor,action="curve.create",resource_type="curve",resource_id=curve.id,details={"approved":False,"source_ref":curve.source_ref})); db.commit()
    return {"curve_id":curve.id,"checksum":curve.checksum,"approved":curve.approved,"status":"pending_review"}


@router.get("/{curve_id}")
def get_curve(curve_id: str,db: Session=Depends(get_db)):
    curve=db.query(CurveArtifact).filter_by(id=curve_id).first()
    if not curve: raise HTTPException(404,detail={"error_code":"CURVE_NOT_FOUND","message":"Curve not found"})
    return {"curve_id":curve.id,"x_unit":curve.x_unit,"y_unit":curve.y_unit,"z_unit":curve.z_unit,"x_values":curve.x_values,"y_values":curve.y_values,"z_values":curve.z_values,"interpolation":curve.interpolation,"source_ref":curve.source_ref,"checksum":curve.checksum,"approved":curve.approved,"created_by":curve.created_by}
