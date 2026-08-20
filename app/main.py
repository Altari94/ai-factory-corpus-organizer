from fastapi import FastAPI

from app.api.catalogue import router as catalogue_router
from app.api.health import router as health_router
from app.api.semantic_snapshot import router as semantic_snapshot_router
from app.api.corpus import router as corpus_router
from app.config.settings import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(health_router)
app.include_router(catalogue_router)
app.include_router(semantic_snapshot_router)
app.include_router(corpus_router)
