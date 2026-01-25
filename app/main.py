from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import configure_logging
from app.api.orchestrate import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield

app = FastAPI(
    title=settings.service_name,
    lifespan=lifespan
)

app.include_router(api_router, prefix="/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
