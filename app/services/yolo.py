import os
import cv2
import torch
from pathlib import Path
from typing import List, Dict, Any

class YoloDetector:
    def __init__(self, model_path: str, device: str = None, conf_threshold: float = 0.4):
        self.model_path = Path(model_path)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.conf_threshold = conf_threshold
        if not self.model_path.exists():
            raise FileNotFoundError(f"Modelo YOLO não encontrado: {self.model_path}")
        self.model = torch.hub.load(
            "ultralytics/yolov5",
            "custom",
            path=str(self.model_path),
            force_reload=False
        ).to(self.device)
        self.model.conf = self.conf_threshold

    def detect(self, bgr_image) -> List[Dict[str, Any]]:
        """Recebe imagem BGR (OpenCV) e retorna lista de detecções."""
        if bgr_image is None or bgr_image.size == 0:
            return []

        # Converte para RGB
        rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)

        # Inference
        results = self.model(rgb_image, size=640)
        detections = results.pandas().xyxy[0].to_dict(orient="records")

        output = []
        for det in detections:
            if det["confidence"] < self.conf_threshold:
                continue
            output.append({
                "class": det["name"],
                "confidence": float(det["confidence"]),
                "bbox": [float(det["xmin"]), float(det["ymin"]), float(det["xmax"]), float(det["ymax"])]
            })
        return output

    def detect_from_path(self, image_path: str) -> List[Dict[str, Any]]:
        """Recebe caminho de imagem e retorna detecções."""
        if not os.path.exists(image_path):
            return []
        bgr_image = cv2.imread(image_path)
        return self.detect(bgr_image)

# Exemplo de uso direto (debug)
if __name__ == "__main__":
    yolo = YoloDetector(model_path="model/ppe.pt", conf_threshold=0.4)
    img = cv2.imread("data/images/test.jpg")
    detections = yolo.detect(img)
    print(detections)
