from prometheus_client import Counter, Gauge, Histogram

# Métricas principais
fps_gauge = Gauge("camera_fps", "Frames por segundo por câmera", ["camera_id"])
latency_hist = Histogram(
    "pipeline_latency_seconds",
    "Latência total (captura -> detecção -> persistência) em segundos",
    ["camera_id"]
)
queue_gauge = Gauge("event_queue_size", "Tamanho da fila de eventos", ["camera_id"])
rtsp_error_counter = Counter("rtsp_errors_total", "Total de erros RTSP por câmera", ["camera_id"])
reconnect_success_counter = Counter("camera_reconnect_success_total", "Reconexões bem-sucedidas", ["camera_id"])
reconnect_fail_counter = Counter("camera_reconnect_fail_total", "Reconexões mal-sucedidas", ["camera_id"])
cpu_usage_gauge = Gauge("system_cpu_usage_percent", "Uso de CPU em %")
ram_usage_gauge = Gauge("system_ram_usage_percent", "Uso de RAM em %")
events_per_min_gauge = Gauge("events_per_minute", "Eventos por minuto", ["camera_id"])
dedupe_hits_counter = Counter("event_dedupe_hits_total", "Eventos descartados por deduplicação", ["camera_id"])
debounce_hits_counter = Counter("event_debounce_hits_total", "Eventos descartados por debounce", ["camera_id"])


def record_fps(camera_id: str, fps: float):
    fps_gauge.labels(camera_id=camera_id).set(fps)


def record_latency(camera_id: str, seconds: float):
    latency_hist.labels(camera_id=camera_id).observe(seconds)


def record_queue_size(camera_id: str, size: int):
    queue_gauge.labels(camera_id=camera_id).set(size)


def record_rtsp_error(camera_id: str):
    rtsp_error_counter.labels(camera_id=camera_id).inc()


def record_reconnect_success(camera_id: str):
    reconnect_success_counter.labels(camera_id=camera_id).inc()


def record_reconnect_fail(camera_id: str):
    reconnect_fail_counter.labels(camera_id=camera_id).inc()


def record_cpu_usage(percent: float):
    cpu_usage_gauge.set(percent)


def record_ram_usage(percent: float):
    ram_usage_gauge.set(percent)


def record_events_per_min(camera_id: str, count: int):
    events_per_min_gauge.labels(camera_id=camera_id).set(count)


def record_dedupe_hit(camera_id: str):
    dedupe_hits_counter.labels(camera_id=camera_id).inc()


def record_debounce_hit(camera_id: str):
    debounce_hits_counter.labels(camera_id=camera_id).inc()
