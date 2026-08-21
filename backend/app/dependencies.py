from typing import Optional, AsyncGenerator
from fastapi import Depends, WebSocket, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .database import get_db
from .redis_client import redis_client
from .utils.security import decode_token
from .exceptions import AuthException, BannedException
from .models.user import User, AdminUser
from .models.character import Character

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise AuthException("未登录")
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthException("Token类型错误")
    jti = payload.get("jti")
    if jti and await redis_client.exists(f"wx:jwt:blacklist:{jti}"):
        raise AuthException("Token已失效")
    user_id = int(payload.get("sub"))
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthException("用户不存在或已被禁用")
    ban_key = f"wx:ban:user:{user_id}"
    if await redis_client.exists(ban_key):
        ban_info = await redis_client.hgetall(ban_key)
        raise BannedException(f"账号已被封禁: {ban_info.get('reason', '违规')}")
    return user


async def get_current_admin(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    if not token:
        raise AuthException("未登录")
    payload = decode_token(token)
    admin_id = int(payload.get("sub"))
    is_admin = payload.get("is_admin", False)
    if not is_admin:
        raise AuthException("需要管理员权限")
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin or not admin.is_active:
        raise AuthException("管理员账号不存在或已禁用")
    return admin


async def get_current_character(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Character:
    result = await db.execute(
        select(Character).where(
            Character.user_id == user.id,
            Character.is_online == True
        ).order_by(Character.updated_at.desc())
    )
    char = result.scalar_one_or_none()
    if not char:
        raise AuthException("请先选择角色进入游戏")
    ban_key = f"wx:ban:char:{char.id}"
    if await redis_client.exists(ban_key):
        ban_info = await redis_client.hgetall(ban_key)
        raise BannedException(f"角色已被封禁: {ban_info.get('reason', '违规')}")
    return char


async def get_ws_current_user(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001, reason="Token类型错误")
            return None
        user_id = int(payload.get("sub"))
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            await websocket.close(code=4001, reason="用户不存在")
            return None
        return user
    except Exception:
        await websocket.close(code=4001, reason="认证失败")
        return None
