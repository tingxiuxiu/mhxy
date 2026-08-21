from sqlalchemy import Column, Integer, String, Boolean, SmallInteger, JSON
from ..database import Base


class MonsterConfig(Base):
    __tablename__ = "monster_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False)
    level = Column(Integer, default=1, nullable=False)
    hp = Column(Integer, default=100, nullable=False)
    mp = Column(Integer, default=50, nullable=False)
    damage = Column(Integer, default=20, nullable=False)
    defense = Column(Integer, default=10, nullable=False)
    speed = Column(Integer, default=10, nullable=False)
    magic_damage = Column(Integer, default=10, nullable=False)
    magic_defense = Column(Integer, default=10, nullable=False)
    skills = Column(JSON, default=list, nullable=False)
    exp_reward = Column(Integer, default=50, nullable=False)
    cash_reward = Column(Integer, default=30, nullable=False)
    drop_items = Column(JSON, default=list, nullable=False)
    is_boss = Column(Boolean, default=False, nullable=False)
    resource_id = Column(String(64))
    is_active = Column(Boolean, default=True, nullable=False)
