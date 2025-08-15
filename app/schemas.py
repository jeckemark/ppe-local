from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.models import Role


# ------------------------
# Usuários
# ------------------------
class UserBase(BaseModel):
    email: EmailStr
    role: Role = Role.operador
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)


class UserOut(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ------------------------
# Autenticação
# ------------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: Optional[str] = None


# ------------------------
# Câmeras
# ------------------------
class CameraBase(BaseModel):
    name: str
    nvr_base_url: str
    username: str
    password: str
    channel_no: int
    threshold: float = 0.5
    debounce_sec: int = 5
    enabled: bool = True
    ai_model_path: Optional[str] = None
    polling_interval: int = 2
    detect_person: bool = True
    detect_helmet: bool = True
    detect_mask: bool = True


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    nvr_base_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    channel_no: Optional[int] = None
    threshold: Optional[float] = None
    debounce_sec: Optional[int] = None
    enabled: Optional[bool] = None
    ai_model_path: Optional[str] = None
    polling_interval: Optional[int] = None
    detect_person: Optional[bool] = None
    detect_helmet: Optional[bool] = None
    detect_mask: Optional[bool] = None


class CameraOut(CameraBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ------------------------
# Eventos
# ------------------------
class EventBase(BaseModel):
    camera_id: int
    timestamp: datetime
    image_path: str
    thumb_path: Optional[str] = None
    ppe_status: Optional[str] = None
    summary: Optional[str] = None


class EventCreate(EventBase):
    pass


class EventOut(EventBase):
    id: int
    created_at: datetime
    camera: CameraOut

    class Config:
        from_attributes = True


# ------------------------
# Relatórios
# ------------------------
class ReportFilter(BaseModel):
    camera_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ------------------------
# Auditoria
# ------------------------
class AuditLogBase(BaseModel):
    user_id: int
    action: str
    detail: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogOut(AuditLogBase):
    id: int
    created_at: datetime
    user: UserOut

    class Config:
        from_attributes = True


# ------------------------
# Configurações
# ------------------------
class SettingBase(BaseModel):
    key: str
    value: str


class SettingOut(SettingBase):
    pass


class ReportFilter(BaseModel):
    camera_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
