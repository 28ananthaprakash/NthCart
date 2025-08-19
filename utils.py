import json
from pathlib import Path
from fastapi import HTTPException
from typing import Optional
import jwt
import datetime
import os

DATA_PATH = Path(__file__).parent / "data.json"
JWT_SECRET = os.environ.get("JWT_SECRET", "Ananthaprakash") # TO DO: use .env to set JWT_SECRET
JWT_ALGO = "HS256"
JWT_EXP_DELTA_SECONDS = 60 * 60 * 24 # 1 day


def load_data(): # Reason behind "on the fly" data loading is inspired from relational databases. Keep the connection only when necessary
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def authenticate(email: str, password: str) -> Optional[dict]:
    data = load_data()
    users = data.get("users", {})
    for u in users.values():
        if u.get("email") == email:
            if u.get("password") == password:
                return u
            return None
    return None


def create_token_for_user(user: dict) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": user.get("username"),
        "iat": now,
        "exp": now + datetime.timedelta(seconds=JWT_EXP_DELTA_SECONDS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token: Optional[str]) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="missing token")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid token")


# def _token_to_username(x_token: Optional[str]) -> Optional[str]:
#     # Deprecated when using JWTs
#     if not x_token:
#         return None
#     if not x_token.endswith("-token"):
#         return None
#     return x_token[:-6]


def require_user(x_token: Optional[str]) -> dict:
    payload = decode_token(x_token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid token payload")
    data = load_data()
    user = data.get("users", {}).get(username)
    if not user:
        raise HTTPException(status_code=401, detail="invalid token user")
    return user


def require_admin(x_token: Optional[str]) -> dict:
    user = require_user(x_token) # Admin must be a user
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="admin required")
    return user
