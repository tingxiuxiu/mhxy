from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """应用配置，所有字段从环境变量或 .env 文件读取"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---------- 应用基础配置 ----------
    APP_NAME: str = Field(default="文字西游", alias="PROJECT_NAME")
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    API_V1_PREFIX: str = Field(default="/api/v1")
    ADMIN_PREFIX: str = Field(default="/api/admin")

    # ---------- 安全配置 ----------
    SECRET_KEY: str = Field(default="wx-secret-key-change-in-production")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    JWT_BLACKLIST_KEY: str = Field(default="wx:jwt:blacklist")
    REQUEST_SIGN_SECRET: str = Field(default="wx-request-sign-secret-change-me")

    # ---------- 数据库配置 ----------
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://wenxi:wenxi123@localhost:5432/wenxi"
    )
    DATABASE_ECHO: bool = Field(default=False)

    # ---------- Redis配置 ----------
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = Field(default=50)

    # ---------- ID生成配置 ----------
    HASHIDS_SALT: str = Field(default="wx-hashids-salt")
    HASHIDS_MIN_LENGTH: int = Field(default=8)

    # ---------- 接口限流 ----------
    RATE_LIMIT_PER_MINUTE: int = Field(default=100)
    RATE_LIMIT_IP_PER_MINUTE: int = Field(default=200)

    # ---------- 游戏冷却（秒） ----------
    MOVE_COOLDOWN_SEC: int = Field(default=1)
    CHAT_WORLD_COOLDOWN_SEC: int = Field(default=30)
    BATTLE_CMD_COOLDOWN_SEC: int = Field(default=3)
    TRADE_COOLDOWN_SEC: int = Field(default=10)
    ENCOUNTER_COOLDOWN_SEC: int = Field(default=3)

    # ---------- 战斗配置 ----------
    BATTLE_TURN_TIMEOUT_SEC: int = Field(default=45)
    BATTLE_MAX_ROUNDS: int = Field(default=150)

    # ---------- WebSocket配置 ----------
    WS_HEARTBEAT_INTERVAL_SEC: int = Field(default=30)
    WS_HEARTBEAT_TIMEOUT_SEC: int = Field(default=90)
    WS_MAX_MESSAGE_SIZE_KB: int = Field(default=4)

    # ---------- 经济系统 ----------
    MONEY_CARRY_LIMIT_BASE: int = Field(default=100000)
    MONEY_CARRY_LIMIT_PER_LEVEL: int = Field(default=100000)
    TRADE_LEVEL_LIMIT: int = Field(default=30)

    # ---------- 敏感词 ----------
    SENSITIVE_WORDS: List[str] = Field(default_factory=lambda: ["赌博", "色情", "暴力"])


@lru_cache()
def get_settings() -> Settings:
    """获取单例配置（lru_cache缓存）"""
    return Settings()


settings = get_settings()
