from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer, SmallInteger, ForeignKey
from sqlalchemy.sql import func
from ..database import Base


class Friend(Base):
    __tablename__ = "friends"

    id = Column(BigInteger, primary_key=True, index=True)
    char_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False, index=True)
    friend_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False, index=True)
    intimacy = Column(Integer, default=0, nullable=False)
    group_name = Column(String(32), default="好友")
    is_blacklist = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FriendRequest(Base):
    __tablename__ = "friend_requests"

    id = Column(BigInteger, primary_key=True, index=True)
    from_char_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False)
    to_char_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False)
    status = Column(SmallInteger, default=0, nullable=False)
    message = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TeamInvite(Base):
    __tablename__ = "team_invites"

    id = Column(BigInteger, primary_key=True, index=True)
    from_char_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False)
    to_char_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False)
    target_type = Column(String(16), default="team", nullable=False)
    target_id = Column(BigInteger, nullable=False)
    status = Column(SmallInteger, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expired_at = Column(DateTime(timezone=True))


class Team(Base):
    __tablename__ = "teams"

    id = Column(BigInteger, primary_key=True, index=True)
    leader_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False)
    target = Column(String(64), default="")
    is_locked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    channel = Column(SmallInteger, nullable=False, index=True)
    speaker_id = Column(BigInteger, nullable=False)
    speaker_name = Column(String(32), nullable=False)
    content = Column(String(512), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
