from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

ALGO = "HS256"
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_token(subject: str, secret: str, expires_minutes: int = 60) -> str:
    now = datetime.utcnow()
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, secret, algorithm=ALGO)
