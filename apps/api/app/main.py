from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import health, auth, downloads, search
from app.db.init_db import init_db

app = FastAPI(title="Music AutoDL API", version="0.1.0")

origins = [o.strip() for o in settings.CORS_ORIGINS.split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(downloads.router, prefix="/api/v1", tags=["downloads"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])


@app.on_event("startup")
def startup_event() -> None:
    init_db()

@app.get("/")
def root():
    return {"name": "music-autodl", "env": settings.APP_ENV}
