from sqlalchemy import Column, Integer, String, Boolean, DateTime, SmallInteger, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from ..database import Base


class MapConfig(Base):
    __tablename__ = "map_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False, unique=True)
    type = Column(SmallInteger, default=1, nullable=False)
    width = Column(Integer, default=50, nullable=False)
    height = Column(Integer, default=50, nullable=False)
    adjacent_maps = Column(JSON, default=list, nullable=False)
    is_dark = Column(Boolean, default=False, nullable=False)
    encounter_rate = Column(Integer, default=0, nullable=False)
    encounters = Column(JSON, default=list, nullable=False)
    resource_id = Column(String(64))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NpcConfig(Base):
    __tablename__ = "npc_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False)
    title = Column(String(32))
    map_id = Column(Integer, ForeignKey("map_configs.id"), nullable=False, index=True)
    pos_x = Column(Integer, default=0, nullable=False)
    pos_y = Column(Integer, default=0, nullable=False)
    npc_type = Column(SmallInteger, default=1, nullable=False)
    dialog = Column(Text, default="")
    shop_items = Column(JSON, default=list, nullable=False)
    quest_ids = Column(JSON, default=list, nullable=False)
    teleport_to = Column(JSON)
    functions = Column(JSON, default=list, nullable=False)
    resource_id = Column(String(64))
    is_active = Column(Boolean, default=True, nullable=False)
