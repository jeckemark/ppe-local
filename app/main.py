import os
import asyncio
import json
import pathlib
import datetime as dt
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from fastapi import FastAPI, Depends, Request, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import create_access_token, verify_password, get_password_hash
from app.deps import get_db, get_current_user, require_roles
from app.models import Base, engine, SessionLocal, User, Camera, Event, AuditLog, Setting, Role
from app.routers import cameras as cameras_router
from app.routers import events as events_router
from app.routers import reports as reports_router
from app.routers import users as users_router
from app.routers import logs as logs_router
from app.routers import metrics as metrics_router
from app.routers import monitoring as monitoring_router
from app.services.metrics import Metrics
from app.workers.manager import WorkerManager

DATA_DIR = pathlib.Path("./data")
IMAGES_DIR = DATA_DIR / "images"
THUMBS_DIR = DATA_DIR / "thumbs"
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(THUMBS_DIR, exist_ok=True)
os.makedirs("model", exist_ok=True)

app = FastAPI(title="PPE Local", version="1.0.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

Base.metadata.create_all(bind=engine)


def ensure_bootstrap():
    db = SessionLocal()
    try:
        if not db.query(User).first():
            admin = User(
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                role=Role.admin,
            )
            db.add(admin)
        if not db.query(Setting).filter(Setting.key == "retention_days").first():
            s = Setting(key="retention_days", value=os.getenv("RETENTION_DAYS", "15"))
            db.add(s)
        db.commit()
    finally:
        db.close()


ensure_bootstrap()

metrics = Metrics()
manager = WorkerManager()


@app.get("/")
async def root(user=Depends(get_current_user)):
    """Redireciona a rota raiz para a página de monitoramento."""
    return RedirectResponse(url="/monitoramento")


@app.get("/cameras", response_class=HTMLResponse)
async def cameras_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles(Role.admin, Role.supervisor)),
):
    cams = db.query(Camera).all()
    return templates.TemplateResponse(
        "cameras.html",
        {"request": request, "user": user, "cameras": cams, "active_tab": "cameras"},
    )


@app.post("/cameras", response_class=HTMLResponse)
async def create_camera_page(
    request: Request,
    name: str = Form(...),
    nvr_base_url: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    channel_no: int = Form(...),
    threshold: float = Form(0.5),
    debounce_sec: int = Form(5),
    detect_person: bool = Form(False),
    detect_helmet: bool = Form(False),
    detect_mask: bool = Form(False),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(Role.admin, Role.supervisor)),
):
    cam = Camera(
        name=name,
        nvr_base_url=nvr_base_url,
        username=username,
        password=password,
        channel_no=channel_no,
        threshold=threshold,
        debounce_sec=debounce_sec,
        detect_person=detect_person,
        detect_helmet=detect_helmet,
        detect_mask=detect_mask,
    )
    db.add(cam)
    db.commit()
    db.refresh(cam)
    manager._start_worker(cam)
    return RedirectResponse(url="/cameras", status_code=303)


@app.get("/relatorios", response_class=HTMLResponse)
async def reports_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("base.html", {
        "request": request,
        "user": user,
        "active_tab": "relatorios"
    })


@app.get("/banco", response_class=HTMLResponse)
async def db_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("base.html", {
        "request": request,
        "user": user,
        "active_tab": "banco"
    })


@app.get("/usuarios", response_class=HTMLResponse)
async def users_page(request: Request, user=Depends(require_roles(Role.admin, Role.supervisor))):
    return templates.TemplateResponse("base.html", {
        "request": request,
        "user": user,
        "active_tab": "usuarios"
    })


@app.get("/metricas", response_class=HTMLResponse)
async def metrics_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("base.html", {
        "request": request,
        "user": user,
        "active_tab": "metricas"
    })


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, user=Depends(require_roles(Role.admin, Role.auditor))):
    return templates.TemplateResponse("base.html", {
        "request": request,
        "user": user,
        "active_tab": "logs"
    })


@app.post("/api/login")
def login(email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if not u or not verify_password(password, u.hashed_password):
            return JSONResponse({"detail": "Credenciais inválidas"}, status_code=401)
        token = create_access_token({"sub": u.email, "role": u.role.value})
        return {"access_token": token, "token_type": "bearer"}
    finally:
        db.close()


app.include_router(cameras_router.router, prefix="/api/cameras", tags=["cameras"])
app.include_router(events_router.router, prefix="/api/events", tags=["events"])
app.include_router(reports_router.router, prefix="/api/reports", tags=["reports"])
app.include_router(users_router.router, prefix="/api/users", tags=["users"])
app.include_router(logs_router.router, prefix="/api/logs", tags=["logs"])
app.include_router(metrics_router.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(monitoring_router.router)


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


async def retention_loop():
    while True:
        days = 15
        db = SessionLocal()
        try:
            s = db.query(Setting).filter(Setting.key == "retention_days").first()
            if s:
                days = int(s.value)
            cutoff = dt.datetime.utcnow() - dt.timedelta(days=days)
            old = db.query(Event).filter(Event.timestamp < cutoff).all()
            for e in old:
                if e.image_path and os.path.exists(e.image_path):
                    try:
                        os.remove(e.image_path)
                    except Exception:
                        pass
                db.delete(e)
            db.commit()
        finally:
            db.close()
        await asyncio.sleep(3600)


async def startup():
    manager.start_all()
    asyncio.create_task(retention_loop())


@app.on_event("startup")
async def on_startup():
    await startup()


@app.on_event("shutdown")
async def on_shutdown():
    manager.stop_all()
