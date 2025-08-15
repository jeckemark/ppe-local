from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas, deps, auth

router = APIRouter(prefix="/users", tags=["Usuários"])

@router.get("/", response_model=List[schemas.UserOut])
def list_users(
    db: Session = Depends(deps.get_db),
    _: models.User = Depends(deps.get_admin_user)
):
    return db.query(models.User).all()

@router.post("/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(deps.get_db),
    _: models.User = Depends(deps.get_admin_user)
):
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Usuário já existe")
    hashed_pw = auth.get_password_hash(user_in.password)
    user = models.User(
        email=user_in.email,
        hashed_password=hashed_pw,
        role=user_in.role,
        is_active=user_in.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    user_in: schemas.UserUpdate,
    db: Session = Depends(deps.get_db),
    _: models.User = Depends(deps.get_admin_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user_in.email:
        user.email = user_in.email
    if user_in.password:
        user.hashed_password = auth.get_password_hash(user_in.password)
    if user_in.role:
        user.role = user_in.role
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    _: models.User = Depends(deps.get_admin_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    db.delete(user)
    db.commit()
    return None
