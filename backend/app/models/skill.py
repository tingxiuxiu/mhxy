from sqlalchemy import Column, Integer, String, Boolean, SmallInteger, Text, JSON
from ..database import Base


class SkillConfig(Base):
    __tablename__ = "skill_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False)
    type = Column(SmallInteger, nullable=False)
    faction = Column(SmallInteger, default=0, nullable=False, index=True)
    mp_cost = Column(Integer, default=0, nullable=False)
    anger_cost = Column(Integer, default=0, nullable=False)
    target_type = Column(SmallInteger, default=1, nullable=False)
    target_count = Column(Integer, default=1, nullable=False)
    effect_type = Column(SmallInteger, default=1, nullable=False)
    effect_value = Column(JSON, default=dict, nullable=False)
    cooldown = Column(Integer, default=0, nullable=False)
    level_req = Column(Integer, default=1, nullable=False)
    description = Column(Text, default="")
    resource_id = Column(String(64))
    is_active = Column(Boolean, default=True, nullable=False)
