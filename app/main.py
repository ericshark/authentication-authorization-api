from fastapi import FastAPI, Depends
from app.routes import user_routes, auth_routes
from app.database import SessionLocal
from sqlalchemy import select, insert
from sqlalchemy.orm import Session
from app.models import User, Base
from typing import Annotated
from app.database import engine, get_db




app = FastAPI()

app.include_router(user_routes.router)
app.include_router(auth_routes.router)

Base.metadata.create_all(engine)



db_dep = Annotated[Session, Depends(get_db)]
 

@app.get('/')
def root():
    return {"test": "working good"}





