from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from app.auth.lockout import reset_failed_attempts
from app.core.dependencies import RoleChecker, db_dep, redis_dep
from app.models import RoleEnum, User
from app.schemas import RoleUpdate, UserOut

router = APIRouter()

require_admin = RoleChecker([RoleEnum.ADMIN])
require_staff = RoleChecker([RoleEnum.ADMIN, RoleEnum.MODERATOR])


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


@router.post("/admin/unlock/{username}")
def unlock(
    username: str,
    admin: Annotated[User, Depends(require_admin)],
    redis: redis_dep,
):
    reset_failed_attempts(username, redis)
    return {"message": f"succesful reset for: {username}"}
