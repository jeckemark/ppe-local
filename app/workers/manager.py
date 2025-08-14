import threading
from typing import Dict
from sqlalchemy.orm import Session

from app.models import SessionLocal, Camera
from app.workers.picture_worker import PictureWorker

class WorkerManager:
    def __init__(self):
        self.workers: Dict[int, PictureWorker] = {}
        self.stop_events: Dict[int, threading.Event] = {}
        self.lock = threading.Lock()

    def start_all(self):
        """Inicia workers para todas as câmeras ativas."""
        with self.lock:
            db: Session = SessionLocal()
            try:
                cameras = db.query(Camera).filter(Camera.enabled == True).all()
                for cam in cameras:
                    self._start_worker(cam)
            finally:
                db.close()

    def _start_worker(self, camera: Camera):
        if camera.id in self.workers:
            return
        stop_event = threading.Event()
        worker = PictureWorker(camera, stop_event, debounce_seconds=camera.debounce or 10)
        worker.start()
        self.workers[camera.id] = worker
        self.stop_events[camera.id] = stop_event

    def stop_worker(self, camera_id: int):
        """Interrompe um worker específico."""
        with self.lock:
            if camera_id in self.stop_events:
                self.stop_events[camera_id].set()
                self.workers[camera_id].join(timeout=5)
                del self.workers[camera_id]
                del self.stop_events[camera_id]

    def restart_worker(self, camera_id: int):
        """Reinicia um worker específico."""
        self.stop_worker(camera_id)
        db: Session = SessionLocal()
        try:
            cam = db.query(Camera).filter(Camera.id == camera_id, Camera.enabled == True).first()
            if cam:
                self._start_worker(cam)
        finally:
            db.close()

    def stop_all(self):
        """Para todos os workers."""
        with self.lock:
            for cam_id, event in list(self.stop_events.items()):
                event.set()
            for cam_id, worker in list(self.workers.items()):
                worker.join(timeout=5)
            self.workers.clear()
            self.stop_events.clear()

    def reload_config(self):
        """Recarrega configuração de câmeras e reinicia workers conforme necessário."""
        with self.lock:
            db: Session = SessionLocal()
            try:
                active_cameras = {cam.id: cam for cam in db.query(Camera).filter(Camera.enabled == True).all()}

                # Parar workers de câmeras removidas ou desativadas
                for cam_id in list(self.workers.keys()):
                    if cam_id not in active_cameras:
                        self.stop_worker(cam_id)

                # Iniciar workers para novas câmeras
                for cam_id, cam in active_cameras.items():
                    if cam_id not in self.workers:
                        self._start_worker(cam)
            finally:
                db.close()
