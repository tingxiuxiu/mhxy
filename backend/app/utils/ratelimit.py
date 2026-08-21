from typing import Optional
from fastapi import Request
from ..redis_client import redis_client
from ..config import settings
from ..exceptions import RateLimitException


async def check_rate_limit(key: str, limit: int, window_sec: int = 60) -> bool:
    redis = redis_client.client
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window_sec)
    if current > limit:
        ttl = await redis.ttl(key)
        raise RateLimitException(f"操作过于频繁，请{ttl}秒后再试")
    return True


async def global_rate_limit(ip: str):
    key = f"wx:ratelimit:ip:{ip}:{int(__import__('time').time() // 60)}"
    await check_rate_limit(key, settings.RATE_LIMIT_IP_PER_MINUTE, 60)


async def user_rate_limit(char_id: int):
    key = f"wx:ratelimit:user:{char_id}:{int(__import__('time').time() // 60)}"
    await check_rate_limit(key, settings.RATE_LIMIT_PER_MINUTE, 60)


async def action_cd(char_id: int, action: str, cooldown_sec: int):
    key = f"wx:cd:{char_id}:{action}"
    if await redis_client.exists(key):
        ttl = await redis_client.client.ttl(key)
        raise RateLimitException(f"操作冷却中，请{ttl}秒后再试")
    await redis_client.set(key, "1", ex=cooldown_sec)
