from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from fastapi.responses import FileResponse

from app import models, schemas, deps
import os

router = APIRouter(prefix="/events", tags=["Eventos"])

@router.get("/", response_model=List[schemas.EventOut])
def list_events(limit: int = 50, db: Session = Depends(deps.get_db), _: models.User = Depends(deps.get_current_user)):
    return db.query(models.Event).order_by(models.Event.created_at.desc()).limit(limit).all()

@router.get("/search", response_model=List[schemas.EventOut])
def search_events(
    camera_id: int = None,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(deps.get_db),
    _: models.User = Depends(deps.get_current_user)
):
    query = db.query(models.Event)
    if camera_id:
        query = query.filter(models.Event.camera_id == camera_id)
    if start_date:
        query = query.filter(models.Event.created_at >= start_date)
    if end_date:
        query = query.filter(models.Event.created_at <= end_date)
    return query.order_by(models.Event.created_at.desc()).all()

@router.get("/{event_id}", response_model=schemas.EventOut)
def get_event(event_id: int, db: Session = Depends(deps.get_db), _: models.User = Depends(deps.get_current_user)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    return event

@router.get("/{event_id}/image")
def get_event_image(event_id: int, db: Session = Depends(deps.get_db), _: models.User = Depends(deps.get_current_user)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event or not event.image_path or not os.path.exists(event.image_path):
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return FileResponse(event.image_path)

@router.delete("/{event_id}")
def delete_event(event_id: int, db: Session = Depends(deps.get_db), _: models.User = Depends(deps.get_admin_user)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    if event.image_path and os.path.exists(event.image_path):
        os.remove(event.image_path)
    db.delete(event)
    db.commit()
    return {"message": "Evento excluído com sucesso"}
