from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer, SmallInteger, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from ..database import Base


class ItemConfig(Base):
    __tablename__ = "item_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False)
    type = Column(SmallInteger, nullable=False, index=True)
    subtype = Column(SmallInteger, default=0, nullable=False)
    level_req = Column(Integer, default=0, nullable=False)
    race_req = Column(SmallInteger, default=0, nullable=False)
    faction_req = Column(SmallInteger, default=0, nullable=False)
    stackable = Column(Boolean, default=True, nullable=False)
    max_stack = Column(Integer, default=99, nullable=False)
    sell_price = Column(Integer, default=0, nullable=False)
    buy_price = Column(Integer, default=0, nullable=False)
    effect = Column(JSON, default=dict, nullable=False)
    resource_id = Column(String(64))
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CharacterItem(Base):
    __tablename__ = "character_items"

    id = Column(BigInteger, primary_key=True, index=True)
    character_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False, index=True)
    item_config_id = Column(Integer, ForeignKey("item_configs.id"), nullable=False)
    slot_type = Column(SmallInteger, default=1, nullable=False, index=True)
    slot_index = Column(Integer, default=0, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    bind_type = Column(SmallInteger, default=0, nullable=False)
    extra_attr = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ShopConfig(Base):
    __tablename__ = "shop_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False)
    npc_id = Column(Integer, default=0, nullable=False)
    type = Column(SmallInteger, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class ShopItem(Base):
    __tablename__ = "shop_items"

    id = Column(BigInteger, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shop_configs.id"), nullable=False, index=True)
    item_config_id = Column(Integer, ForeignKey("item_configs.id"), nullable=False)
    price = Column(Integer, default=0, nullable=False)
    price_modifier = Column(Integer, default=100, nullable=False)
    stock = Column(Integer, default=-1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
