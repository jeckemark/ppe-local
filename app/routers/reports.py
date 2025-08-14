from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from fastapi.responses import StreamingResponse
import csv
import io
import os

from app import models, schemas, deps

router = APIRouter(prefix="/reports", tags=["Relatórios"])

@router.post("/search", response_model=List[schemas.EventOut])
def search_reports(
    filters: schemas.ReportFilter,
    db: Session = Depends(deps.get_db),
    _: models.User = Depends(deps.get_current_user)
):
    query = db.query(models.Event)
    if filters.camera_id:
        query = query.filter(models.Event.camera_id == filters.camera_id)
    if filters.start_date:
        query = query.filter(models.Event.timestamp >= filters.start_date)
    if filters.end_date:
        query = query.filter(models.Event.timestamp <= filters.end_date)
    return query.order_by(models.Event.timestamp.desc()).all()

@router.post("/export")
def export_reports_csv(
    filters: schemas.ReportFilter,
    db: Session = Depends(deps.get_db),
    _: models.User = Depends(deps.get_current_user)
):
    query = db.query(models.Event)
    if filters.camera_id:
        query = query.filter(models.Event.camera_id == filters.camera_id)
    if filters.start_date:
        query = query.filter(models.Event.timestamp >= filters.start_date)
    if filters.end_date:
        query = query.filter(models.Event.timestamp <= filters.end_date)
    events = query.order_by(models.Event.timestamp.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Câmera", "Timestamp", "Status EPI", "Caminho Imagem"])
    for e in events:
        writer.writerow([
            e.id,
            e.camera.name if e.camera else "",
            e.timestamp.isoformat(),
            e.ppe_status,
            e.image_path
        ])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=relatorio.csv"
    })

@router.get("/thumbnails/{event_id}")
def get_event_thumbnail(event_id: int, db: Session = Depends(deps.get_db), _: models.User = Depends(deps.get_current_user)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event or not event.thumb_path or not os.path.exists(event.thumb_path):
        raise HTTPException(status_code=404, detail="Miniatura não encontrada")
    return StreamingResponse(open(event.thumb_path, "rb"), media_type="image/jpeg")
