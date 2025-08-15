import enum
import os
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Enum, ForeignKey, Boolean, Text, Float
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import create_engine

DB_URL = os.getenv("DB_URL", "sqlite:///./data/app.db")

Base = declarative_base()
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Role(str, enum.Enum):
    admin = "admin"
    supervisor = "supervisor"
    operador = "operador"
    auditor = "auditor"


class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=datetime.utcnow)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(Role), default=Role.operador, nullable=False)
    is_active = Column(Boolean, default=True)


class Camera(Base, TimestampMixin):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    nvr_base_url = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    channel_no = Column(Integer, nullable=False)
    threshold = Column(Float, default=0.5)
    debounce_sec = Column(Integer, default=5)
    enabled = Column(Boolean, default=True)
    ai_model_path = Column(String, nullable=True)
    polling_interval = Column(Integer, default=2)
    detect_person = Column(Boolean, default=True)
    detect_helmet = Column(Boolean, default=True)
    detect_mask = Column(Boolean, default=True)


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    image_path = Column(String, nullable=False)
    thumb_path = Column(String, nullable=True)
    ppe_status = Column(String, nullable=True)
    summary = Column(Text, nullable=True)

    camera = relationship("Camera")


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    detail = Column(Text, nullable=True)

    user = relationship("User")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


def init_db():
    Base.metadata.create_all(bind=engine)
