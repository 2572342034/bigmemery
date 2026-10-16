from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.knowledge import router as knowledge_router
from app.core.config import settings
from app.db.session import init_databases
from app.services.auth_service import auth_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_databases()
    auth_service.ensure_default_admin()
    yield


app = FastAPI(
    title="AI Chat SSE Demo",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
