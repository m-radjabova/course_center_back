from fastapi import Depends, HTTPException, status
from app.dependencies.auth import get_current_user

def require_roles(*allowed_roles: str):
    def checker(user=Depends(get_current_user)):
        user_roles = set(user.roles or [])
        if not user_roles.intersection(set(allowed_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        return user
    return checker

require_admin = require_roles("admin")
