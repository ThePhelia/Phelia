from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import create_token, verify_password, get_current_user
from app.db.session import session_scope
from app.db.models import User

router = APIRouter()


class Credentials(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
def login(payload: Credentials):
    with session_scope() as db:
        user = db.query(User).filter_by(email=payload.email).first()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_token(str(user.id), settings.APP_SECRET)
        return {"accessToken": token, "tokenType": "Bearer"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}
