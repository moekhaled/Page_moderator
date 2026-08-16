from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import moderator, webhook
from app.routers.retention import router as retention_router

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(webhook.router)
app.include_router(moderator.router)
app.include_router(retention_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
