from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_current_user, rate_limit
from ..services.user_service import user_service
from ..models.user import User

router = APIRouter(prefix="/api/auth", tags=["认证"])


class RegisterReq(BaseModel):
    username: str
    password: str
    email: str = ""


class LoginReq(BaseModel):
    username: str
    password: str


class RefreshReq(BaseModel):
    refresh_token: str


@router.post("/register")
async def register(req: RegisterReq, db: AsyncSession = Depends(get_db)):
    try:
        user = await user_service.register(db, req.username, req.password, req.email)
        return {"success": True, "user_id": user.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(req: LoginReq, db: AsyncSession = Depends(get_db)):
    try:
        token_data = await user_service.login(db, req.username, req.password)
        return token_data
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh")
async def refresh(req: RefreshReq, db: AsyncSession = Depends(get_db)):
    try:
        return await user_service.refresh_token(db, req.refresh_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(user: User = Depends(get_current_user), _=Depends(rate_limit)):
    await user_service.logout(user.id)
    return {"success": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email, "is_admin": user.is_admin}
