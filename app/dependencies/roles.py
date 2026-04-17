from fastapi import Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.models.enums import UserRole


def require_roles(*allowed_roles: UserRole):
    def checker(user=Depends(get_current_user)):
        if not user.has_any_role(*allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return user

    return checker


require_admin = require_roles(UserRole.ADMIN)
require_teacher_or_admin = require_roles(UserRole.TEACHER, UserRole.ADMIN)
