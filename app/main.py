import pretty_errors
from fastapi import FastAPI

from app.routes import auth_routes, user_routes

pretty_errors.configure(separator_character="*", line_color=pretty_errors.BRIGHT_RED)

app = FastAPI()

app.include_router(auth_routes.router)
app.include_router(user_routes.router)


@app.get("/")
def root():
    return {"status": "ok"}
