import os
import jwt
import datetime as dt
from typing import Optional
from passlib.context import CryptContext

JWT_SECRET = os.getenv("JWT_SECRET", "e2c1b9d7d67a4f3eaa6c2c17f0f5b9150c03b1d4eaa3b08c2c79d4d9f5c3e4a7")
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "480"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire = dt.datetime.utcnow() + dt.timedelta(minutes=expires_delta or JWT_EXPIRES_MIN)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> Optional[dict]:
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
