from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas, deps

router = APIRouter(prefix="/logs", tags=["Logs"])

@router.get("/", response_model=List[schemas.AuditLogOut])
def list_logs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(deps.get_db),
    _: models.User = Depends(deps.get_admin_user)
):
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

@router.post("/", response_model=schemas.AuditLogOut)
def create_log(
    log_in: schemas.AuditLogCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    log = models.AuditLog(
        user_id=current_user.id,
        action=log_in.action,
        details=log_in.details
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
