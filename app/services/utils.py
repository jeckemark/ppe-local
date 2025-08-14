import os
import io
import shutil
import datetime
from PIL import Image
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR.parent / "data"
IMAGES_DIR = DATA_DIR / "images"
THUMBS_DIR = DATA_DIR / "thumbs"

def ensure_dirs():
    """Garante que as pastas necessárias existam."""
    for folder in [DATA_DIR, IMAGES_DIR, THUMBS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)

def save_image(camera_id: str, image_bytes: bytes, timestamp: datetime.datetime) -> str:
    """Salva a imagem completa e retorna o caminho absoluto."""
    ensure_dirs()
    filename = f"{camera_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
    file_path = IMAGES_DIR / filename
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    return str(file_path)

def save_thumbnail(camera_id: str, image_bytes: bytes, timestamp: datetime.datetime, size=(320, 240)) -> str:
    """Gera e salva thumbnail da imagem."""
    ensure_dirs()
    filename = f"{camera_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}_thumb.jpg"
    file_path = THUMBS_DIR / filename
    image = Image.open(io.BytesIO(image_bytes))
    image.thumbnail(size)
    image.save(file_path, "JPEG", quality=85)
    return str(file_path)

def cleanup_old_files(retention_days: int):
    """Remove arquivos antigos conforme a política de retenção."""
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=retention_days)
    for folder in [IMAGES_DIR, THUMBS_DIR]:
        if not folder.exists():
            continue
        for file in folder.iterdir():
            if file.is_file() and datetime.datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
                try:
                    file.unlink()
                except Exception:
                    pass

def format_datetime(dt: datetime.datetime) -> str:
    """Formata data/hora para exibição."""
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def get_file_bytes(path: str) -> bytes:
    """Lê bytes de um arquivo."""
    with open(path, "rb") as f:
        return f.read()

def delete_image_and_thumb(base_filename: str):
    """Remove a imagem e thumbnail correspondentes."""
    for folder in [IMAGES_DIR, THUMBS_DIR]:
        for file in folder.glob(f"{base_filename}*"):
            try:
                file.unlink()
            except Exception:
                pass

def copy_file(src: str, dest: str):
    """Copia arquivo de src para dest."""
    shutil.copy2(src, dest)
