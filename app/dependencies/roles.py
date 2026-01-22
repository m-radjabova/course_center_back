from fastapi import Depends, HTTPException
from app.dependencies.auth import get_current_user
from app.models.user import User

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user
