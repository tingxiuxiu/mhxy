from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from ..database import Base


class GameConfig(Base):
    __tablename__ = "game_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(64), unique=True, nullable=False, index=True)
    config_value = Column(JSON, nullable=False)
    description = Column(Text, default="")
    version = Column(Integer, default=1, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)
    updated_by = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
