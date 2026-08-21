import asyncio
import os
import sys
import pytest
import pytest_asyncio
from typing import Generator

# 必须在导入 app 之前设置环境变量，否则 pydantic-settings 的 lru_cache 会缓存配置
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["DEBUG"] = "false"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeRedis:
    def __init__(self):
        self._data = {}
        self._expiry = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self._data:
            return False
        self._data[key] = str(value)
        if ex:
            import time
            self._expiry[key] = time.time() + ex
        return True

    async def get(self, key):
        import time
        if key in self._expiry and self._expiry[key] < time.time():
            del self._data[key]
            del self._expiry[key]
            return None
        return self._data.get(key)

    async def delete(self, *keys):
        for k in keys:
            self._data.pop(k, None)
            self._expiry.pop(k, None)
        return len(keys)

    async def exists(self, *keys):
        import time
        cnt = 0
        for k in keys:
            if k in self._data:
                if k in self._expiry and self._expiry[k] < time.time():
                    del self._data[k]
                    del self._expiry[k]
                else:
                    cnt += 1
        return cnt

    async def incr(self, key, amount=1):
        v = self._data.get(key, "0")
        try:
            n = int(v) + amount
        except Exception:
            n = amount
        self._data[key] = str(n)
        return n

    async def incrby(self, key, amount=1):
        return await self.incr(key, amount)

    async def expire(self, key, seconds):
        import time
        self._expiry[key] = time.time() + seconds
        return True

    async def ttl(self, key):
        import time
        if key not in self._expiry:
            return -1
        t = self._expiry[key] - time.time()
        return max(0, int(t))

    async def lpush(self, key, *values):
        if key not in self._data or not isinstance(self._data[key], list):
            self._data[key] = []
        for v in values:
            self._data[key].insert(0, v if isinstance(v, str) else str(v))
        return len(self._data[key])

    async def rpush(self, key, *values):
        if key not in self._data or not isinstance(self._data[key], list):
            self._data[key] = []
        for v in values:
            self._data[key].append(v if isinstance(v, str) else str(v))
        return len(self._data[key])

    async def ltrim(self, key, start, end):
        if key in self._data and isinstance(self._data[key], list):
            stop = end + 1 if end >= 0 else None
            self._data[key] = self._data[key][start:stop]

    async def lrange(self, key, start, end):
        d = self._data.get(key, [])
        if not isinstance(d, list):
            return []
        stop = end + 1 if end >= 0 else None
        return d[start:stop]

    async def sismember(self, key, value):
        v = self._data.get(key)
        if isinstance(v, set):
            return str(value) in v or value in v
        return False

    async def sadd(self, key, *values):
        if key not in self._data or not isinstance(self._data[key], set):
            self._data[key] = set()
        for v in values:
            self._data[key].add(str(v))

    async def srem(self, key, *values):
        if key in self._data and isinstance(self._data[key], set):
            for v in values:
                self._data[key].discard(str(v))

    async def smembers(self, key):
        v = self._data.get(key)
        return v if isinstance(v, set) else set()

    async def scard(self, key):
        v = self._data.get(key)
        return len(v) if isinstance(v, set) else 0

    async def hset(self, key, mapping=None, ex=None, **kwargs):
        if mapping is None:
            mapping = kwargs
        if key not in self._data or not isinstance(self._data[key], dict):
            self._data[key] = {}
        for field, value in mapping.items():
            self._data[key][field] = str(value)
        if ex:
            import time
            self._expiry[key] = time.time() + ex

    async def hget(self, key, field):
        d = self._data.get(key)
        if isinstance(d, dict):
            return d.get(field)
        return None

    async def hgetall(self, key):
        d = self._data.get(key)
        return d if isinstance(d, dict) else {}

    async def hdel(self, key, *fields):
        d = self._data.get(key)
        if isinstance(d, dict):
            for f in fields:
                d.pop(f, None)

    async def set_json(self, key, value, ex=None):
        import json
        await self.set(key, json.dumps(value, ensure_ascii=False), ex=ex)

    async def get_json(self, key):
        import json
        data = await self.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except Exception:
            return None

    async def set_lock(self, key, value="1", ex=10):
        return await self.set(key, value, ex=ex, nx=True)

    async def release_lock(self, key):
        await self.delete(key)

    async def ping(self):
        return True

    async def close(self):
        pass


@pytest_asyncio.fixture
async def fake_redis():
    r = FakeRedis()
    from app import redis_client as rc_mod
    # 清除 settings 缓存，确保测试环境变量生效
    from app.config import get_settings
    get_settings.cache_clear()

    old_redis = rc_mod.redis_client._redis
    rc_mod.redis_client._redis = r
    try:
        yield r
    finally:
        rc_mod.redis_client._redis = old_redis


@pytest_asyncio.fixture
async def db_session():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.database import Base

    # 确保所有模型都被导入
    import app.models  # noqa: F401

    # 清除 settings 缓存以使用测试 DATABASE_URL
    from app.config import get_settings
    get_settings.cache_clear()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session

    await engine.dispose()
