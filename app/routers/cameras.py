from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas, deps
from app.workers.manager import WorkerManager

router = APIRouter(prefix="/cameras", tags=["Câmeras"])
manager = WorkerManager()

@router.get("/", response_model=List[schemas.CameraOut])
def list_cameras(db: Session = Depends(deps.get_db), _: models.User = Depends(deps.get_current_user)):
    return db.query(models.Camera).all()

@router.post("/", response_model=schemas.CameraOut, status_code=status.HTTP_201_CREATED)
def create_camera(camera_in: schemas.CameraCreate, db: Session = Depends(deps.get_db), _: models.User = Depends(deps.get_admin_user)):
    camera = models.Camera(**camera_in.dict())
    db.add(camera)
    db.commit()
    db.refresh(camera)
    if camera.enabled:
        manager._start_worker(camera)
    return camera

@router.put("/{camera_id}", response_model=schemas.CameraOut)
def update_camera(camera_id: int, camera_in: schemas.CameraUpdate, db: Session = Depends(deps.get_db), _: models.User = Depends(deps.get_admin_user)):
    camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    for field, value in camera_in.dict(exclude_unset=True).items():
        setattr(camera, field, value)
    db.commit()
    db.refresh(camera)
    if camera.enabled:
        manager.restart_worker(camera_id)
    else:
        manager.stop_worker(camera_id)
    return camera

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: int, db: Session = Depends(deps.get_db), _: models.User = Depends(deps.get_admin_user)):
    camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    db.delete(camera)
    db.commit()
    manager.stop_worker(camera_id)
    return None

@router.post("/reload", status_code=status.HTTP_200_OK)
def reload_cameras(_: models.User = Depends(deps.get_admin_user)):
    manager.reload_config()
    return {"message": "Configuração de câmeras recarregada com sucesso."}
