from sqlalchemy import Column, BigInteger, Boolean, DateTime, Integer, SmallInteger, ForeignKey, JSON, String
from sqlalchemy.sql import func
from ..database import Base


class Battle(Base):
    __tablename__ = "battles"

    id = Column(BigInteger, primary_key=True, index=True)
    battle_type = Column(SmallInteger, default=1, nullable=False)
    map_id = Column(Integer, nullable=False)
    status = Column(SmallInteger, default=1, nullable=False, index=True)
    turn = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    extra_data = Column(JSON, default=dict, nullable=False)


class BattleParticipant(Base):
    __tablename__ = "battle_participants"

    id = Column(BigInteger, primary_key=True, index=True)
    battle_id = Column(BigInteger, ForeignKey("battles.id"), nullable=False, index=True)
    side = Column(SmallInteger, nullable=False)
    char_type = Column(SmallInteger, nullable=False)
    char_id = Column(BigInteger, nullable=False)
    char_name = Column(String(32), nullable=False)
    hp = Column(Integer, nullable=False)
    mp = Column(Integer, nullable=False)
    hp_max = Column(Integer, nullable=False)
    mp_max = Column(Integer, nullable=False)
    damage = Column(Integer, nullable=False)
    defense = Column(Integer, nullable=False)
    speed = Column(Integer, nullable=False)
    position = Column(Integer, nullable=False)
    is_dead = Column(Boolean, default=False, nullable=False)
    buffs = Column(JSON, default=list, nullable=False)


class BattleLog(Base):
    __tablename__ = "battle_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    battle_id = Column(BigInteger, ForeignKey("battles.id"), nullable=False, index=True)
    turn = Column(Integer, nullable=False)
    actor_id = Column(BigInteger, nullable=False)
    action_type = Column(SmallInteger, nullable=False)
    action_targets = Column(JSON, default=list, nullable=False)
    action_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
