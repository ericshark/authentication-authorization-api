import logging

from fastapi import FastAPI

from app.routes import auth_routes, user_routes

logging.basicConfig(
    level=logging.WARNING,
    format="%(name)s: %(message)s",
    datefmt="%H:%M:%S",
    #    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("app").setLevel(logging.DEBUG)

app = FastAPI()

app.include_router(auth_routes.router)
app.include_router(user_routes.router)


@app.get("/")
def root():
    return {"status": "ok"}
