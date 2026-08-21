import redis.asyncio as redis
from typing import Optional, Any
import json

from .config import settings


class RedisClient:
    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    async def connect(self):
        if self._redis is None:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()

    async def disconnect(self):
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    @property
    def client(self) -> redis.Redis:
        if self._redis is None:
            raise RuntimeError("Redis not connected")
        return self._redis

    async def get(self, key: str) -> Optional[str]:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None, nx: bool = False):
        await self._redis.set(key, value, ex=ex, nx=nx)

    async def ttl(self, key: str) -> int:
        return await self._redis.ttl(key)

    async def delete(self, *keys: str):
        if keys:
            await self._redis.delete(*keys)

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.exists(key))

    async def expire(self, key: str, seconds: int):
        await self._redis.expire(key, seconds)

    async def hget(self, key: str, field: str) -> Optional[str]:
        return await self._redis.hget(key, field)

    async def hset(self, key: str, mapping: dict, ex: Optional[int] = None):
        await self._redis.hset(key, mapping=mapping)
        if ex:
            await self._redis.expire(key, ex)

    async def hgetall(self, key: str) -> dict:
        return await self._redis.hgetall(key)

    async def hdel(self, key: str, *fields: str):
        await self._redis.hdel(key, *fields)

    async def incr(self, key: str) -> int:
        return await self._redis.incr(key)

    async def incrby(self, key: str, amount: int) -> int:
        return await self._redis.incrby(key, amount)

    async def lpush(self, key: str, *values: str):
        await self._redis.lpush(key, *values)

    async def rpush(self, key: str, *values: str):
        await self._redis.rpush(key, *values)

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> list:
        return await self._redis.lrange(key, start, end)

    async def ltrim(self, key: str, start: int, end: int):
        await self._redis.ltrim(key, start, end)

    async def sadd(self, key: str, *members: str):
        await self._redis.sadd(key, *members)

    async def srem(self, key: str, *members: str):
        await self._redis.srem(key, *members)

    async def smembers(self, key: str) -> set:
        return await self._redis.smembers(key)

    async def sismember(self, key: str, member: str) -> bool:
        return bool(await self._redis.sismember(key, member))

    async def scard(self, key: str) -> int:
        return await self._redis.scard(key)

    async def get_json(self, key: str) -> Optional[Any]:
        data = await self.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None

    async def set_json(self, key: str, value: Any, ex: Optional[int] = None):
        await self.set(key, json.dumps(value, ensure_ascii=False), ex=ex)

    async def set_lock(self, key: str, value: str = "1", ex: int = 10) -> bool:
        return bool(await self._redis.set(key, value, nx=True, ex=ex))

    async def release_lock(self, key: str):
        await self.delete(key)


redis_client = RedisClient()


async def get_redis() -> RedisClient:
    return redis_client


async def init_redis():
    await redis_client.connect()


async def close_redis():
    await redis_client.disconnect()
