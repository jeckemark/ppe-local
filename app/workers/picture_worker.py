import time
import datetime
import requests
from threading import Thread, Event

from app.services.yolo import YoloDetector
from app.services.ppe_rules import PPEAnalyzer
from app.services import utils, metrics
from app.models import SessionLocal, Event as EventModel, Camera
from sqlalchemy.orm import Session

class PictureWorker(Thread):
    def __init__(self, camera: Camera, stop_event: Event, debounce_seconds: int = 10):
        super().__init__(daemon=True)
        self.camera = camera
        self.stop_event = stop_event
        self.debounce_seconds = debounce_seconds
        self.last_event_time = None
        self.detector = YoloDetector(self.camera.ai_model_path or None)
        self.analyzer = PPEAnalyzer()
        self.session_factory = SessionLocal

    def run(self):
        while not self.stop_event.is_set():
            start_time = time.time()
            try:
                image_bytes = self.fetch_picture()
                if not image_bytes:
                    metrics.record_rtsp_error(str(self.camera.id))
                    time.sleep(1)
                    continue

                results = self.detector.detect(image_bytes)
                summary = self.analyzer.analyze(results)

                if summary.get("total_violations"):
                    now = datetime.datetime.now()
                    if self.should_trigger_event(now):
                        self.save_event(image_bytes, summary, now)
                        self.last_event_time = now

                elapsed = time.time() - start_time
                metrics.record_latency(str(self.camera.id), elapsed)

            except Exception as e:
                metrics.record_rtsp_error(str(self.camera.id))
                time.sleep(1)
                continue

            time.sleep(self.camera.polling_interval or 2)

    def fetch_picture(self) -> bytes:
        """Obtém imagem estática via ISAPI."""
        try:
            url = f"{self.camera.nvr_base_url}/ISAPI/Streaming/channels/{self.camera.channel_no}/picture"
            auth = (self.camera.username, self.camera.password)
            resp = requests.get(url, auth=auth, timeout=10, verify=False)
            if resp.status_code == 200:
                return resp.content
            return None
        except Exception:
            return None

    def should_trigger_event(self, now: datetime.datetime) -> bool:
        """Controle de debounce."""
        if not self.last_event_time:
            return True
        return (now - self.last_event_time).total_seconds() >= self.debounce_seconds

    def save_event(self, image_bytes: bytes, summary: dict, timestamp: datetime.datetime):
        """Salva evento no banco e gera thumbnail."""
        db: Session = self.session_factory()
        try:
            image_path = utils.save_image(str(self.camera.id), image_bytes, timestamp)
            thumb_path = utils.save_thumbnail(str(self.camera.id), image_bytes, timestamp)
            event_type = "OK"
            if summary.get("details"):
                event_type = summary["details"][0].get("status", "OK")
            event = EventModel(
                camera_id=self.camera.id,
                event_type=event_type,
                image_path=image_path,
                thumb_path=thumb_path,
                score=summary.get("total_violations", 0),
                created_at=timestamp,
            )
            db.add(event)
            db.commit()
            db.refresh(event)
        finally:
            db.close()
