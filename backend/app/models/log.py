from sqlalchemy import Column, BigInteger, String, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    char_id = Column(BigInteger, default=0, nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    detail = Column(JSON, default=dict, nullable=False)
    ip = Column(String(45), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
