from fastapi import FastAPI, Depends
from app.routes import user_routes, auth_routes
from sqlalchemy.orm import Session
from typing import Annotated
from app.database import get_db
import pretty_errors


pretty_errors.configure(separator_character="*", line_color=pretty_errors.BRIGHT_RED)

app = FastAPI()

app.include_router(user_routes.router)
app.include_router(auth_routes.router)


db_dep = Annotated[Session, Depends(get_db)]


@app.get("/")
def root():
    return {"test": "working good"}
