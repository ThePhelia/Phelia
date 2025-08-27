from fastapi import APIRouter

router = APIRouter()

@router.post("/auth/login")
async def login(payload: dict):
    # MVP stub — возвращаем фиктивный токен
    return {"accessToken": "dev-token", "tokenType": "Bearer"}

@router.get("/me")
async def me():
    return {"id": "dev", "email": "dev@example", "role": "admin"}
