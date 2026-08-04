import logging

from fastapi import FastAPI
from app.routes import (
    auth_routes,
    oauth_routes,
    password_routes,
    twofa_routes,
    user_routes,
    admin_routes,
    system_routes,
)
from app.core.config import settings
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logging.basicConfig(
    level=logging.DEBUG,
    format=" %(levelname)s: %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    #    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(admin_routes.router, tags=["admin"])
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(user_routes.router, prefix="/users", tags=["users"])
app.include_router(oauth_routes.router, prefix="/auth", tags=["oauth"])
app.include_router(password_routes.router, prefix="/auth", tags=["password"])
app.include_router(twofa_routes.router, prefix="/auth", tags=["two-fa"])
app.include_router(system_routes.router, tags=["system"])


@app.get("/")
def root():
    return {"status": "ok"}
