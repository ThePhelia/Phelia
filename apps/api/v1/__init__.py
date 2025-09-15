from fastapi import APIRouter
from .routes import indexers as indexers_routes

api_router = APIRouter()
api_router.include_router(indexers_routes.router)

