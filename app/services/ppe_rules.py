from typing import List, Dict, Any

# Classes previstas no modelo YOLO
# Ajuste conforme as labels usadas no seu treinamento
PPE_CLASSES = {
    "person": "Pessoa",
    "helmet": "Capacete",
    "mask": "Máscara"
}

class PPEAnalyzer:
    def __init__(self, iou_threshold: float = 0.3):
        self.iou_threshold = iou_threshold

    def _iou(self, boxA, boxB) -> float:
        """Calcula Intersection over Union (IoU) entre dois bounding boxes."""
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interW = max(0, xB - xA)
        interH = max(0, yB - yA)
        interArea = interW * interH
        if interArea == 0:
            return 0.0
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        iou = interArea / float(boxAArea + boxBArea - interArea)
        return iou

    def analyze(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analisa detecções e retorna regras de uso de EPI violadas."""
        persons = [d for d in detections if d["class"] == "person"]
        helmets = [d for d in detections if d["class"] == "helmet"]
        masks = [d for d in detections if d["class"] == "mask"]

        results = []
        count_ok = 0
        count_violation = 0

        for person in persons:
            has_helmet = any(self._iou(person["bbox"], helmet["bbox"]) > self.iou_threshold for helmet in helmets)
            has_mask = any(self._iou(person["bbox"], mask["bbox"]) > self.iou_threshold for mask in masks)

            if has_helmet and has_mask:
                status = "OK"
                count_ok += 1
            elif not has_helmet and not has_mask:
                status = "Sem capacete e máscara"
                count_violation += 1
            elif not has_helmet:
                status = "Sem capacete"
                count_violation += 1
            elif not has_mask:
                status = "Sem máscara"
                count_violation += 1
            else:
                status = "Desconhecido"
                count_violation += 1

            results.append({
                "person_bbox": person["bbox"],
                "helmet": has_helmet,
                "mask": has_mask,
                "status": status
            })

        return {
            "total_persons": len(persons),
            "total_ok": count_ok,
            "total_violations": count_violation,
            "details": results
        }

# Exemplo de teste manual
if __name__ == "__main__":
    detections = [
        {"class": "person", "bbox": [0, 0, 100, 200], "confidence": 0.9},
        {"class": "helmet", "bbox": [10, 10, 90, 60], "confidence": 0.8},
        {"class": "mask", "bbox": [20, 60, 80, 120], "confidence": 0.85},
    ]
    analyzer = PPEAnalyzer()
    print(analyzer.analyze(detections))
