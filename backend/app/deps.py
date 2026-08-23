from fastapi import Depends, HTTPException, status, Header, Query, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from typing import Optional
import time

from .config import settings
from .database import get_db
from .redis_client import redis_client
from .models.user import User
from .models.character import Character
from .utils.crypto import verify_request_signature
from .exceptions import AuthException, RateLimitException, BannedException
from sqlalchemy import select
from sqlalchemy.orm import selectinload


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise AuthException("未提供认证凭证")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = int(payload.get("sub"))
        exp = payload.get("exp")
        if exp is None or exp < time.time():
            raise AuthException("token已过期")
        jti = payload.get("jti")
        if jti and await redis_client.exists(f"wx:jwt:blacklist:{jti}"):
            raise AuthException("token已失效")
    except JWTError:
        raise AuthException("无效的token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthException("用户不存在或已禁用")
    ban = await redis_client.get(f"wx:ban:user:{user_id}")
    if ban:
        raise BannedException(f"账号被封禁：{ban.decode() if isinstance(ban, bytes) else ban}")
    return user


async def get_current_char(
    char_id: Optional[int] = Header(None, alias="X-Char-ID"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Character:
    if not char_id:
        raise AuthException("请选择角色（X-Char-ID）")
    result = await db.execute(
        select(Character)
        .options(selectinload(Character.stats))
        .where(Character.id == char_id, Character.user_id == user.id, Character.is_deleted == False)
    )
    char = result.scalar_one_or_none()
    if not char:
        raise AuthException("角色不存在")
    return char


async def verify_signature(
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    x_nonce: str = Header(..., alias="X-Nonce"),
    x_sign: str = Header(..., alias="X-Sign"),
):
    if abs(int(time.time()) - int(x_timestamp)) > 300:
        raise AuthException("请求时间戳过期")
    nonce_key = f"wx:nonce:{x_nonce}"
    if await redis_client.exists(nonce_key):
        raise AuthException("重复请求")
    await redis_client.set(nonce_key, "1", ex=600)
    return True


async def rate_limit(
    user: User = Depends(get_current_user),
    x_action: str = Header("default", alias="X-Action"),
):
    import json
    limit_key = f"wx:rate:{user.id}:{x_action}"
    window = 60
    max_req = 60
    if x_action in ["battle_action", "move", "chat"]:
        max_req = 30
    elif x_action in ["attack", "use_skill"]:
        max_req = 20
    count = await redis_client.incr(limit_key)
    if count == 1:
        await redis_client.expire(limit_key, window)
    if count > max_req:
        raise RateLimitException("请求过于频繁，请稍后再试")
    return True


async def get_current_char_ws(
    websocket: WebSocket,
    token: str = Query(...),
    char_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, Character]:
    try:
        if await redis_client.sismember(settings.JWT_BLACKLIST_KEY, token):
            await websocket.close(code=4001)
            return None, None
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception:
        await websocket.close(code=4001)
        return None, None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        await websocket.close(code=4001)
        return None, None
    char_result = await db.execute(
        select(Character).where(Character.id == char_id, Character.user_id == user.id, Character.is_deleted == False)
    )
    char = char_result.scalar_one_or_none()
    if not char:
        await websocket.close(code=4003)
        return None, None
    return user, char
