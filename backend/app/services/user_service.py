from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional

from ..models.user import User
from ..utils.security import hash_password, verify_password, create_access_token, create_refresh_token
from ..utils.id_gen import generate_id
from ..schemas.user import RegisterRequest, LoginRequest, TokenResponse
from ..exceptions import AuthException, ValidationException
from ..redis_client import redis_client
from ..config import settings


class UserService:
    @staticmethod
    async def register(db: AsyncSession, data: RegisterRequest) -> User:
        existing = await db.execute(select(User).where(User.username == data.username))
        if existing.scalar_one_or_none():
            raise ValidationException("用户名已存在")
        user = User(
            id=generate_id(),
            username=data.username,
            password_hash=hash_password(data.password),
        )
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, username: str, password: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            raise AuthException("账号已被禁用")
        return user

    @staticmethod
    async def login(db: AsyncSession, data: LoginRequest) -> TokenResponse:
        user = await UserService.authenticate(db, data.username, data.password)
        if not user:
            raise AuthException("用户名或密码错误")
        user.last_login_at = datetime.utcnow()
        access_token = create_access_token(user.id, extra={"is_admin": user.is_admin})
        refresh_token = create_refresh_token(user.id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    async def refresh_token(refresh_token: str) -> TokenResponse:
        from ..utils.security import decode_token
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise AuthException("无效的刷新Token")
        user_id = int(payload.get("sub"))
        jti = payload.get("jti")
        if jti:
            await redis_client.set(f"wx:jwt:blacklist:{jti}", "1", ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
        access_token = create_access_token(user_id)
        new_refresh = create_refresh_token(user_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    async def logout(access_token: str, refresh_token: Optional[str] = None):
        from ..utils.security import decode_token
        try:
            payload = decode_token(access_token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                ttl = exp - int(datetime.utcnow().timestamp())
                if ttl > 0:
                    await redis_client.set(f"wx:jwt:blacklist:{jti}", "1", ex=ttl)
        except Exception:
            pass
        if refresh_token:
            try:
                payload = decode_token(refresh_token)
                jti = payload.get("jti")
                exp = payload.get("exp")
                if jti and exp:
                    ttl = exp - int(datetime.utcnow().timestamp())
                    if ttl > 0:
                        await redis_client.set(f"wx:jwt:blacklist:{jti}", "1", ex=ttl)
            except Exception:
                pass

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


user_service = UserService()
