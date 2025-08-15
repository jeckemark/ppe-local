import asyncio
import time
import hashlib
import datetime as dt
import os

import httpx
import cv2
import numpy as np

from app.models import Camera
from app.services.yolo import YoloDetector
from app.services.ppe_rules import PPEAnalyzer
from app.services.metrics import Metrics


class PictureWorker:
    """
    Worker assíncrono que captura snapshots via ISAPI (/picture),
    roda YOLO, aplica regras de EPI e dispara callback de evento.
    """

    def __init__(
        self,
        camera: Camera,
        metrics: Metrics,
        on_event,
        interval_sec: int = 2,
        timeout: float = 5.0,
    ):
        self.camera = camera
        self.metrics = metrics
        self.on_event = on_event
        self.interval_sec = interval_sec
        self.timeout = timeout
        self._stop = False

        self._detector = YoloDetector(
            model_path=os.getenv("MODEL_PATH", "./model/ppe.pt"),
            conf_threshold=camera.threshold or 0.4,
        )
        self._ppe = PPEAnalyzer(iou_threshold=0.15)

        self._last_event_ts = 0.0
        self._last_sig = None

    def update_config(self, camera: Camera):
        self.camera = camera

    def stop(self):
        self._stop = True

    async def run(self):
        backoff = 1.0
        while not self._stop and self.camera.active:
            t0 = time.time()
            try:
                jpg = await self._fetch_picture()
                if not jpg:
                    self.metrics.rtsp_errors.labels(str(self.camera.id)).inc()
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 15)
                    continue
                backoff = 1.0

                arr = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if arr is None:
                    await asyncio.sleep(self.interval_sec)
                    continue

                # YOLO
                t1 = time.time()
                dets = self._detector.detect(arr)  # [{'class','confidence','bbox':[x1,y1,x2,y2]}]
                t2 = time.time()

                # Regras PPE
                summary = self._ppe.analyze(dets)
                ev_type = None
                if summary.get("total_violations", 0) > 0:
                    if any(d["status"] == "Sem capacete e máscara" for d in summary["details"]):
                        ev_type = "no_helmet_no_mask"
                    elif any(d["status"] == "Sem capacete" for d in summary["details"]):
                        ev_type = "no_helmet"
                    elif any(d["status"] == "Sem máscara" for d in summary["details"]):
                        ev_type = "no_mask"

                now = time.time()
                if ev_type:
                    sig = hashlib.sha1(f"{ev_type}:{summary}".encode()).hexdigest()
                    if now - self._last_event_ts < (self.camera.debounce_sec or 5):
                        self.metrics.debounce.labels(str(self.camera.id)).inc()
                    elif sig == self._last_sig:
                        self.metrics.dedupe.labels(str(self.camera.id)).inc()
                    else:
                        ts = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
                        img_path = f"./data/images/cam{self.camera.id}_{ts}.jpg"
                        with open(img_path, "wb") as f:
                            f.write(jpg)
                        self._last_event_ts = now
                        self._last_sig = sig
                        # Delega persistência/broadcast ao callback do manager/main.py
                        await self.on_event(
                            {
                                "camera_id": self.camera.id,
                                "type": ev_type,
                                "score": 1.0,
                                "image_path": img_path,
                                "meta": summary,
                            }
                        )

                # métricas
                self.metrics.fps.labels(str(self.camera.id)).set(
                    1.0 / max(1e-3, time.time() - t0)
                )
                self.metrics.latency.labels("detect").observe((t2 - t1) * 1000.0)

                await asyncio.sleep(max(0.0, self.interval_sec - (time.time() - t0)))
            except Exception:
                self.metrics.rtsp_errors.labels(str(self.camera.id)).inc()
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 15)

    async def _fetch_picture(self) -> bytes | None:
        """Obtém imagem estática via ISAPI."""
        try:
            base = self.camera.nvr_base_url.rstrip("/")
            url = f"{base}/ISAPI/Streaming/channels/{self.camera.channel_no}/picture"
            auth = (self.camera.nvr_username, self.camera.nvr_password)
            async with httpx.AsyncClient(verify=False, timeout=self.timeout) as cli:
                r = await cli.get(url, auth=auth)
            if r.status_code == 200 and r.content:
                return r.content
            return None
        except Exception:
            return None
