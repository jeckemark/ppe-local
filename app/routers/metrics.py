from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.orm import Session

from app import deps, models
from app.services import metrics

router = APIRouter(prefix="/metrics", tags=["Métricas"])

@router.get("/", response_class=PlainTextResponse)
def get_metrics(
    _: models.User = Depends(deps.get_current_user)
):
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/stats")
def get_stats(
    db: Session = Depends(deps.get_db),
    _: models.User = Depends(deps.get_current_user)
):
    total_cameras = db.query(models.Camera).count()
    total_events = db.query(models.Event).count()
    return {
        "total_cameras": total_cameras,
        "total_events": total_events,
        "fps": metrics.fps_gauge.collect()[0].samples[0].value if metrics.fps_gauge.collect() else 0,
        "cpu_usage": metrics.cpu_usage_gauge.collect()[0].samples[0].value if metrics.cpu_usage_gauge.collect() else 0,
        "ram_usage": metrics.ram_usage_gauge.collect()[0].samples[0].value if metrics.ram_usage_gauge.collect() else 0
    }
