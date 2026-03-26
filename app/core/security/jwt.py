from datetime import datetime, timedelta, timezone
from typing import cast
from jose import jwt
from jose.exceptions import JWTError
from dotenv import load_dotenv
import os

load_dotenv()

JWT_SECRET_RAW = os.getenv("JWT_SECRET")
if not JWT_SECRET_RAW:
    raise ValueError("JWT_SECRET is not set in environment variables.")
JWT_SECRET = cast(str, JWT_SECRET_RAW)

JWT_ALG = os.getenv("JWT_ALG", "HS256")     
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", 60))

def create_access_token(payload: dict) -> str:
    data = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES_MIN)
    data["exp"] = expire
    token = jwt.encode(data, JWT_SECRET, algorithm=JWT_ALG)
    return token


def decode_access_token(token: str) -> dict | None:
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return decoded
    except JWTError:
        return None 