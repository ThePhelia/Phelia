from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.db.session import session_scope
from app.db.models import User

ALGO = "HS256"
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

auth_scheme = HTTPBearer()


def create_token(subject: str, secret: str, expires_minutes: int = 60) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, secret, algorithm=ALGO)


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.APP_SECRET, algorithms=[ALGO])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    with session_scope() as db:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
