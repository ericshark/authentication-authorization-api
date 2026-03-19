from fastapi import FastAPI, Depends
from routes import user_routes
from database import SessionLocal
from sqlalchemy import select, insert
from sqlalchemy.orm import Session
from models import User, Base
from typing import Annotated
from database import engine, get_db



app = FastAPI()

app.include_router(user_routes.router)

Base.metadata.create_all(engine)

db_dep = Annotated[Session, Depends(get_db)]
 

@app.get('/')
def root(db: db_dep):
    return {"message": "working good"}
    


@app.get('/add')
def addUser(db: db_dep):
    new_user = User(name="test 2", fullname="eric")
    db.add(new_user)
    db.commit()
    return {"message": "New user", "User_id": new_user.id}





