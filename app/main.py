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
            admin = User(email="admin@example.com",
                         password_hash=get_password_hash("admin123"),
                         role=Role.admin)
            db.add(admin)
        if not db.query(Setting).first():
            s = Setting(retention_days=int(os.getenv("RETENTION_DAYS", "15")))
            db.add(s)
        db.commit()
    finally:
        db.close()


ensure_bootstrap()

metrics = Metrics()
manager = WorkerManager(metrics=metrics)


class EventHub:
    def __init__(self):
        self._clients: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)

    async def disconnect(self, ws: WebSocket):
        if ws in self._clients:
            self._clients.remove(ws)

    async def broadcast(self, payload: Dict[str, Any]):
        dead = []
        for ws in list(self._clients):
            try:
                await ws.send_text(json.dumps(payload, ensure_ascii=False))
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


event_hub = EventHub()


async def on_event(ev: Dict[str, Any]):
    db = SessionLocal()
    try:
        e = Event(
            ts=dt.datetime.utcnow(),
            camera_id=ev["camera_id"],
            ev_type=ev["type"],
            score=ev.get("score", 0.0),
            image_path=ev.get("image_path"),
            meta=json.dumps(ev.get("meta", {}), ensure_ascii=False),
        )
        db.add(e)
        db.commit()
        db.refresh(e)
        payload = {
            "id": e.id,
            "ts": e.ts.isoformat() + "Z",
            "camera_id": e.camera_id,
            "type": e.ev_type,
            "score": e.score,
            "image_path": e.image_path,
            "meta": json.loads(e.meta or "{}")
        }
        await event_hub.broadcast({"kind": "event", "data": payload})
    finally:
        db.close()


manager.set_event_callback(on_event)


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
        if not u or not verify_password(password, u.password_hash):
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
    await event_hub.connect(ws)
    try:
        await ws.send_text(json.dumps({"kind": "hello"}, ensure_ascii=False))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await event_hub.disconnect(ws)
    except Exception:
        await event_hub.disconnect(ws)


async def retention_loop():
    while True:
        days = 15
        db = SessionLocal()
        try:
            s = db.query(Setting).first()
            if s:
                days = int(s.retention_days or 15)
            cutoff = dt.datetime.utcnow() - dt.timedelta(days=days)
            old = db.query(Event).filter(Event.ts < cutoff).all()
            for e in old:
                if e.image_path and os.path.exists(e.image_path):
                    try:
                        os.remove(e.image_path)
                    except:
                        pass
                db.delete(e)
            db.commit()
        finally:
            db.close()
        await asyncio.sleep(3600)


async def startup():
    await manager.start()
    asyncio.create_task(retention_loop())


@app.on_event("startup")
async def on_startup():
    await startup()


@app.on_event("shutdown")
async def on_shutdown():
    await manager.stop()
