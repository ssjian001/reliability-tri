from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import AuditEvent

router=APIRouter(prefix="/v1/audit-events",tags=["audit"])
@router.get("")
def list_audit(resource_type: str|None=None,resource_id: str|None=None,limit: int=100,offset: int=0,db: Session=Depends(get_db)):
    q=db.query(AuditEvent)
    if resource_type: q=q.filter_by(resource_type=resource_type)
    if resource_id: q=q.filter_by(resource_id=resource_id)
    total=q.count(); rows=q.order_by(AuditEvent.created_at.desc()).offset(offset).limit(max(1,min(limit,200))).all()
    return {"items":[{"event_id":x.id,"actor":x.actor,"action":x.action,"resource_type":x.resource_type,"resource_id":x.resource_id,"details":x.details,"created_at":x.created_at} for x in rows],"total":total,"limit":limit,"offset":offset}
