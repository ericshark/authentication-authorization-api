import logging

from fastapi import FastAPI
from app.routes import (
    auth_routes,
    oauth_routes,
    password_routes,
    user_routes,
    admin_routes,
)
from app.core.config import settings
from starlette.middleware.sessions import SessionMiddleware

logging.basicConfig(
    level=logging.WARNING,
    format="%(name)s: %(message)s",
    datefmt="%H:%M:%S",
    #    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("app").setLevel(logging.DEBUG)

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(admin_routes.router, tags=["admin"])
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(user_routes.router, prefix="/users", tags=["users"])
app.include_router(oauth_routes.router, prefix="/auth", tags=["oauth"])
app.include_router(password_routes.router, prefix="/auth", tags=["password"])


@app.get("/")
def root():
    return {"status": "ok"}
