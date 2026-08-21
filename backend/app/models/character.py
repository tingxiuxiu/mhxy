from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer, SmallInteger, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Character(Base):
    __tablename__ = "characters"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(16), unique=True, nullable=False, index=True)
    gender = Column(SmallInteger, default=1, nullable=False)
    race = Column(SmallInteger, default=1, nullable=False)
    faction = Column(SmallInteger, default=1, nullable=False, index=True)
    job = Column(SmallInteger, default=1, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    exp = Column(BigInteger, default=0, nullable=False)
    map_id = Column(Integer, ForeignKey("map_configs.id"), default=1, nullable=False)
    pos_x = Column(Integer, default=10, nullable=False)
    pos_y = Column(Integer, default=10, nullable=False)
    team_id = Column(BigInteger, ForeignKey("teams.id"), index=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), index=True)
    cash = Column(BigInteger, default=0, nullable=False)
    reserve_cash = Column(BigInteger, default=0, nullable=False)
    jade = Column(BigInteger, default=0, nullable=False)
    hp = Column(Integer, default=100, nullable=False)
    mp = Column(Integer, default=50, nullable=False)
    anger = Column(Integer, default=0, nullable=False)
    strength = Column(Integer, default=5, nullable=False)
    magic = Column(Integer, default=5, nullable=False)
    vitality = Column(Integer, default=5, nullable=False)
    endurance = Column(Integer, default=5, nullable=False)
    agility = Column(Integer, default=5, nullable=False)
    attr_points = Column(Integer, default=0, nullable=False)
    practice_phys = Column(Integer, default=0, nullable=False)
    is_online = Column(Boolean, default=False, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    in_battle_id = Column(BigInteger, index=True)
    last_logout_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    stats = relationship("CharacterStats", back_populates="character", uselist=False, cascade="all, delete-orphan")


class CharacterStats(Base):
    __tablename__ = "character_stats"

    character_id = Column(BigInteger, ForeignKey("characters.id"), primary_key=True)
    base_hp = Column(Integer, default=100, nullable=False)
    base_mp = Column(Integer, default=50, nullable=False)
    base_hit = Column(Integer, default=20, nullable=False)
    base_damage = Column(Integer, default=30, nullable=False)
    base_defense = Column(Integer, default=20, nullable=False)
    base_speed = Column(Integer, default=10, nullable=False)
    base_magic_damage = Column(Integer, default=15, nullable=False)
    base_magic_defense = Column(Integer, default=15, nullable=False)
    pot_points = Column(Integer, default=5, nullable=False)
    pot_tizhi = Column(Integer, default=5, nullable=False)
    pot_moli = Column(Integer, default=5, nullable=False)
    pot_liliang = Column(Integer, default=5, nullable=False)
    pot_naili = Column(Integer, default=5, nullable=False)
    pot_minjie = Column(Integer, default=5, nullable=False)
    practice_phys = Column(Integer, default=0, nullable=False)
    practice_def = Column(Integer, default=0, nullable=False)
    practice_mdef = Column(Integer, default=0, nullable=False)
    practice_capture = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    character = relationship("Character", back_populates="stats")
