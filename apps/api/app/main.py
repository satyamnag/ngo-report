"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import assets, auth, backgrounds, projects, templates
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(templates.router)
app.include_router(projects.router)
app.include_router(assets.router)
app.include_router(backgrounds.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}