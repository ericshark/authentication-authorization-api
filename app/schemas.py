from ast import Del

from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime


class UserBase(BaseModel):
    username : str
    name : str
    email : EmailStr
    


class UserCreate(UserBase):
    password : str

class UserOut(UserBase):
    id : int
    date_created : datetime 
    is_active : bool
    model_config = ConfigDict(from_attributes=True)
    JWT: str

class UserUpdate(BaseModel):
    username : str | None = None
    name : str | None = None
    email : EmailStr | None = None

class UpdatePassword(BaseModel):
    username: str
    old_password: str
    new_password: str

class loginUser(BaseModel):
    username: str
    password: str

