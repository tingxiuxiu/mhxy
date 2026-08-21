from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer, SmallInteger, ForeignKey, Text, JSON, Date
from sqlalchemy.sql import func
from ..database import Base


class QuestConfig(Base):
    __tablename__ = "quest_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    type = Column(SmallInteger, nullable=False, index=True)
    level_min = Column(Integer, default=1, nullable=False)
    level_max = Column(Integer, default=0, nullable=False)
    repeatable = Column(Boolean, default=False, nullable=False)
    daily_limit = Column(Integer, default=0, nullable=False)
    giver_npc_id = Column(Integer, nullable=False)
    steps = Column(JSON, default=list, nullable=False)
    rewards = Column(JSON, default=dict, nullable=False)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True, nullable=False)


class CharacterQuest(Base):
    __tablename__ = "character_quests"

    id = Column(BigInteger, primary_key=True, index=True)
    character_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False, index=True)
    quest_id = Column(Integer, ForeignKey("quest_configs.id"), nullable=False, index=True)
    status = Column(SmallInteger, default=1, nullable=False)
    current_step = Column(Integer, default=0, nullable=False)
    step_data = Column(JSON, default=dict, nullable=False)
    accepted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    times_completed = Column(Integer, default=0, nullable=False)
    today_date = Column(Date)
