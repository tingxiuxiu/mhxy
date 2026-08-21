from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer, SmallInteger, ForeignKey, Text
from sqlalchemy.sql import func
from ..database import Base


class Guild(Base):
    __tablename__ = "guilds"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(16), unique=True, nullable=False, index=True)
    leader_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False)
    level = Column(Integer, default=1, nullable=False)
    funds = Column(BigInteger, default=0, nullable=False)
    prosperity = Column(Integer, default=0, nullable=False)
    members_count = Column(Integer, default=1, nullable=False)
    current_notice = Column(String(256), default="欢迎加入！")
    description = Column(String(256), default="")
    announcement = Column(Text, default="")
    max_members = Column(Integer, default=50, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GuildMember(Base):
    __tablename__ = "guild_members"

    id = Column(BigInteger, primary_key=True, index=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False, index=True)
    character_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False, unique=True, index=True)
    position = Column(SmallInteger, default=6, nullable=False)
    contribution = Column(Integer, default=0, nullable=False)
    current_contrib = Column(Integer, default=0, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GuildSkill(Base):
    __tablename__ = "guild_skills"

    id = Column(BigInteger, primary_key=True, index=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False, index=True)
    skill_id = Column(Integer, nullable=False)
    level = Column(Integer, default=0, nullable=False)


class GuildLog(Base):
    __tablename__ = "guild_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False, index=True)
    char_id = Column(BigInteger, nullable=False)
    action_type = Column(String(32), nullable=False)
    content = Column(String(256), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
