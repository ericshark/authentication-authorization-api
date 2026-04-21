from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from app.auth import RoleChecker, get_current_user
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import RoleUpdate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])

db_dep = Annotated[Session, Depends(get_db)]

require_admin = RoleChecker([RoleEnum.ADMIN])
require_staff = RoleChecker([RoleEnum.ADMIN, RoleEnum.MODERATOR])


@router.get("/me")
def get_me(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me")
def update_user(
    user_info: UserUpdate,
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
):
    try:
        user_data = user_info.model_dump(exclude_unset=True)
        stmt = update(User).where(User.id == user.id).values(user_data)
        db.execute(stmt)
        db.commit()
        return {"updated_id": user.id}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already taken")


@router.get("/admin/users")
def get_all_users(
    db: db_dep, admin: Annotated[User, Depends(require_admin)]
) -> list[UserOut]:
    users = db.execute(select(User)).scalars().all()
    return [UserOut.model_validate(u) for u in users]


@router.patch("/admin/{u_id}/role")
def change_role(
    u_id: int,
    role_update: RoleUpdate,
    db: db_dep,
    admin: Annotated[User, Depends(require_admin)],
):
    try:
        user = db.execute(select(User).where(User.id == u_id)).scalar_one()
        user.role = role_update.role
        db.commit()
        return {"updated_id": u_id, "new_role": role_update.role}
    except NoResultFound:
        raise HTTPException(status_code=404, detail="User not found")
