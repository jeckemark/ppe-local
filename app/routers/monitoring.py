from typing import List

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models, deps

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

LAYOUT_OPTIONS = [1, 4, 8, 16, 32]
COLS_MAP = {1: 1, 4: 2, 8: 4, 16: 4, 32: 8}


@router.get("/monitoramento", response_class=HTMLResponse)
async def monitoring_page(
    request: Request,
    layout: int = 4,
    db: Session = Depends(deps.get_db),
    user: models.User = Depends(deps.get_current_user),
):
    """Página principal de monitoramento com grade de câmeras e eventos recentes."""
    layout = layout if layout in LAYOUT_OPTIONS else 4
    cols = COLS_MAP.get(layout, 4)

    cameras: List[models.Camera] = (
        db.query(models.Camera).filter(models.Camera.enabled == True).all()
    )
    events: List[models.Event] = (
        db.query(models.Event)
        .order_by(models.Event.timestamp.desc())
        .limit(50)
        .all()
    )

    return templates.TemplateResponse(
        "monitoring.html",
        {
            "request": request,
            "user": user,
            "cameras": cameras,
            "events": events,
            "layout": layout,
            "cols": cols,
        },
    )


@router.get("/monitoramento/event/{event_id}", response_class=HTMLResponse)
async def monitoring_event_detail(
    request: Request,
    event_id: int,
    db: Session = Depends(deps.get_db),
    user: models.User = Depends(deps.get_current_user),
):
    """Retorna o HTML parcial com a imagem do evento selecionado."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    return templates.TemplateResponse(
        "event_detail.html", {"request": request, "event": event}
    )
