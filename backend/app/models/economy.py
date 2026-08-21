from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer, SmallInteger, ForeignKey, JSON
from sqlalchemy.sql import func
from ..database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(BigInteger, primary_key=True, index=True)
    initiator_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False)
    target_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False)
    status = Column(SmallInteger, default=1, nullable=False)
    initiator_cash = Column(BigInteger, default=0, nullable=False)
    target_cash = Column(BigInteger, default=0, nullable=False)
    initiator_items = Column(JSON, default=list, nullable=False)
    target_items = Column(JSON, default=list, nullable=False)
    initiator_confirmed = Column(Boolean, default=False, nullable=False)
    target_confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))


class Stall(Base):
    __tablename__ = "stalls"

    id = Column(BigInteger, primary_key=True, index=True)
    owner_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False, unique=True)
    title = Column(String(32), default="杂货摊")
    map_id = Column(Integer, nullable=False)
    pos_x = Column(Integer, nullable=False)
    pos_y = Column(Integer, nullable=False)
    is_open = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StallItem(Base):
    __tablename__ = "stall_items"

    id = Column(BigInteger, primary_key=True, index=True)
    stall_id = Column(BigInteger, ForeignKey("stalls.id"), nullable=False, index=True)
    char_item_id = Column(BigInteger, ForeignKey("character_items.id"), nullable=False, unique=True)
    price = Column(BigInteger, nullable=False)
    sold = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sold_at = Column(DateTime(timezone=True))


class MarketListing(Base):
    __tablename__ = "market_listings"

    id = Column(BigInteger, primary_key=True, index=True)
    seller_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False, index=True)
    seller_name = Column(String(32), nullable=False)
    item_config_id = Column(BigInteger, nullable=False)
    item_name = Column(String(64), nullable=False)
    item_extra = Column(JSON, default=dict, nullable=False)
    price_per_unit = Column(BigInteger, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    status = Column(SmallInteger, default=1, nullable=False, index=True)
    listed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sold_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(BigInteger, primary_key=True, index=True)
    listing_id = Column(BigInteger, ForeignKey("market_listings.id"), nullable=False, index=True)
    buyer_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False)
    seller_id = Column(BigInteger, ForeignKey("characters.id"), nullable=False)
    item_config_id = Column(BigInteger, nullable=False)
    quantity = Column(Integer, nullable=False)
    price_per_unit = Column(BigInteger, nullable=False)
    total_price = Column(BigInteger, nullable=False)
    fee = Column(BigInteger, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RechargeOrder(Base):
    __tablename__ = "recharge_orders"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    order_no = Column(String(64), unique=True, nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    jade_amount = Column(Integer, nullable=False)
    pay_channel = Column(String(32))
    status = Column(SmallInteger, default=1, nullable=False)
    paid_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
