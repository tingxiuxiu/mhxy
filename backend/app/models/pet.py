from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer, SmallInteger, ForeignKey, Numeric, JSON
from sqlalchemy.sql import func
from ..database import Base


class PetConfig(Base):
    __tablename__ = "pet_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False)
    level_req = Column(Integer, default=0, nullable=False)
    base_hp = Column(Integer, default=100, nullable=False)
    base_mp = Column(Integer, default=50, nullable=False)
    base_attack = Column(Integer, default=50, nullable=False)
    base_defense = Column(Integer, default=40, nullable=False)
    base_speed = Column(Integer, default=30, nullable=False)
    base_magic = Column(Integer, default=40, nullable=False)
    growth_rate = Column(Numeric(4, 3), default=1.0, nullable=False)
    possible_skills = Column(JSON, default=list, nullable=False)
    capture_rate = Column(Integer, default=20, nullable=False)
    resource_id = Column(String(64))
    is_active = Column(Boolean, default=True, nullable=False)


class CharacterPet(Base):
    __tablename__ = "character_pets"

    id = Column(BigInteger, primary_key=True, index=True)
    character_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False, index=True)
    pet_config_id = Column(Integer, ForeignKey("pet_configs.id"), nullable=False)
    nickname = Column(String(32))
    level = Column(Integer, default=0, nullable=False)
    exp = Column(BigInteger, default=0, nullable=False)
    hp = Column(Integer, default=100, nullable=False)
    mp = Column(Integer, default=50, nullable=False)
    loyalty = Column(Integer, default=100, nullable=False)
    life = Column(Integer, default=10000, nullable=False)
    is_battle = Column(Boolean, default=False, nullable=False)
    slot_index = Column(Integer, default=0, nullable=False)
    skills = Column(JSON, default=list, nullable=False)
    attr_gz = Column(Integer, nullable=False)
    attr_fy = Column(Integer, nullable=False)
    attr_tz = Column(Integer, nullable=False)
    attr_fz = Column(Integer, nullable=False)
    attr_sd = Column(Integer, nullable=False)
    growth = Column(Numeric(4, 3), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
