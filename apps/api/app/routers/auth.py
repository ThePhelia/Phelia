from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.core.security import (
    create_token,
    verify_password,
    get_current_user,
    hash_password,
)
from app.db.session import session_scope
from app.db.models import User

router = APIRouter()


class Credentials(BaseModel):
    email: EmailStr
    password: str


@router.post("/auth/login")
def login(payload: Credentials):
    with session_scope() as db:
        user = db.query(User).filter_by(email=payload.email).first()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_token(str(user.id), settings.APP_SECRET)
        return {"accessToken": token, "tokenType": "Bearer"}


@router.post("/auth/register", status_code=201)
def register(payload: Credentials):
    with session_scope() as db:
        existing = db.query(User).filter_by(email=payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        user = User(
            email=payload.email, hashed_password=hash_password(payload.password)
        )
        db.add(user)
        db.flush()
        token = create_token(str(user.id), settings.APP_SECRET)
        return {"accessToken": token, "tokenType": "Bearer"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }
