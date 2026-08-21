from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional, Dict, Any
import random

from ..models.economy import ShopConfig, ShopItem, MarketListing, Transaction
from ..models.item import ItemConfig
from ..models.character import Character
from ..game.enums import MarketStatus
from ..utils.id_gen import generate_id
from ..exceptions import EconomyException, ItemException
from .item_service import item_service
from .character_service import character_service


class ShopService:
    @staticmethod
    async def get_shop_items(db: AsyncSession, shop_id: int) -> List[Dict[str, Any]]:
        result = await db.execute(
            select(ShopItem, ItemConfig)
            .join(ItemConfig, ShopItem.item_config_id == ItemConfig.id)
            .where(and_(ShopItem.shop_id == shop_id, ShopItem.is_active == True))
        )
        items = []
        for si, cfg in result.all():
            price = si.price if si.price > 0 else int(cfg.buy_price * si.price_modifier / 100)
            items.append({
                "item_id": cfg.id, "name": cfg.name, "price": price,
                "sell_price": int(cfg.sell_price),
                "stack": cfg.max_stack, "type": cfg.type,
                "stock": si.stock,
            })
        return items

    @staticmethod
    async def buy_item(db: AsyncSession, char: Character, item_config_id: int, count: int = 1,
                       price: int = 0) -> dict:
        cfg_result = await db.execute(select(ItemConfig).where(ItemConfig.id == item_config_id))
        cfg = cfg_result.scalar_one_or_none()
        if not cfg:
            raise ItemException("物品不存在")
        actual_price = price if price > 0 else cfg.buy_price
        total_cost = actual_price * count
        if char.cash < total_cost:
            raise EconomyException("金币不足")
        await item_service.add_item(db, char, item_config_id, count)
        await character_service.add_cash(char, -total_cost)
        return {"item": cfg.name, "count": count, "cost": total_cost}

    @staticmethod
    async def sell_item(db: AsyncSession, char: Character, char_item_id: int, count: int = 1) -> dict:
        result = await db.execute(
            select(CharacterItem, ItemConfig)
            .join(ItemConfig, CharacterItem.item_config_id == ItemConfig.id)
            .where(and_(CharacterItem.id == char_item_id, CharacterItem.character_id == char.id))
        )
        from ..models.item import CharacterItem
        row = result.first()
        if not row:
            raise ItemException("物品不存在")
        item, cfg = row
        if item.quantity < count:
            raise ItemException("数量不足")
        if item.bind_type == 1:
            raise EconomyException("绑定物品无法出售")
        sell_price = int(cfg.sell_price) * count
        await item_service.remove_item_by_instance(db, char, char_item_id, count)
        await character_service.add_cash(char, sell_price)
        return {"item": cfg.name, "count": count, "reward": sell_price}


class MarketService:
    FEE_RATE = 0.05
    MAX_LISTINGS_PER_CHAR = 10

    @staticmethod
    async def list_item(db: AsyncSession, char: Character, char_item_id: int,
                        price_per_unit: int, count: int = 1) -> MarketListing:
        if price_per_unit < 1:
            raise EconomyException("价格必须>=1")
        my_count = await db.execute(
            select(MarketListing).where(
                and_(MarketListing.seller_id == char.id, MarketListing.status == MarketStatus.LISTED)
            )
        )
        if len(my_count.scalars().all()) >= MarketService.MAX_LISTINGS_PER_CHAR:
            raise EconomyException("上架数量已满")
        result = await db.execute(
            select(CharacterItem, ItemConfig)
            .join(ItemConfig, CharacterItem.item_config_id == ItemConfig.id)
            .where(and_(CharacterItem.id == char_item_id, CharacterItem.character_id == char.id))
        )
        from ..models.item import CharacterItem
        row = result.first()
        if not row:
            raise ItemException("物品不存在")
        item, cfg = row
        if item.quantity < count:
            raise ItemException("数量不足")
        if item.bind_type == 1:
            raise EconomyException("绑定物品不能上架")
        fee = int(price_per_unit * count * MarketService.FEE_RATE)
        if char.cash < fee:
            raise EconomyException(f"手续费不足，需要{fee}金币")
        await character_service.add_cash(char, -fee)
        await item_service.remove_item_by_instance(db, char, char_item_id, count)
        listing = MarketListing(
            id=generate_id(), seller_id=char.id, seller_name=char.name,
            item_config_id=cfg.id, item_name=cfg.name, item_extra=item.extra_attr,
            price_per_unit=price_per_unit, quantity=count,
            status=MarketStatus.LISTED
        )
        db.add(listing)
        await db.flush()
        return listing

    @staticmethod
    async def search_listings(db: AsyncSession, item_name: str = "", page: int = 1, size: int = 20) -> List[MarketListing]:
        query = select(MarketListing).where(MarketListing.status == MarketStatus.LISTED)
        if item_name:
            query = query.where(MarketListing.item_name.contains(item_name))
        query = query.order_by(MarketListing.listed_at.desc()).offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def buy_listing(db: AsyncSession, char: Character, listing_id: int, count: int = 1) -> dict:
        result = await db.execute(select(MarketListing).where(MarketListing.id == listing_id))
        listing = result.scalar_one_or_none()
        if not listing or listing.status != MarketStatus.LISTED:
            raise EconomyException("商品不存在或已下架")
        if listing.seller_id == char.id:
            raise EconomyException("不能买自己的商品")
        if listing.quantity < count:
            raise EconomyException("库存不足")
        total = listing.price_per_unit * count
        if char.cash < total:
            raise EconomyException("金币不足")
        await character_service.add_cash(char, -total)
        await item_service.add_item(db, char, listing.item_config_id, count, extra_attr=listing.item_extra)
        listing.quantity -= count
        txn = Transaction(
            id=generate_id(), listing_id=listing_id, buyer_id=char.id, seller_id=listing.seller_id,
            item_config_id=listing.item_config_id, quantity=count, price_per_unit=listing.price_per_unit,
            total_price=total, fee=int(total * MarketService.FEE_RATE)
        )
        db.add(txn)
        if listing.quantity <= 0:
            listing.status = MarketStatus.SOLD
        seller_result = await db.execute(select(Character).where(Character.id == listing.seller_id))
        seller = seller_result.scalar_one_or_none()
        if seller:
            await character_service.add_cash(seller, total)
        return {"item": listing.item_name, "count": count, "cost": total}

    @staticmethod
    async def cancel_listing(db: AsyncSession, char: Character, listing_id: int):
        result = await db.execute(select(MarketListing).where(MarketListing.id == listing_id))
        listing = result.scalar_one_or_none()
        if not listing or listing.seller_id != char.id:
            raise EconomyException("商品不存在")
        if listing.status != MarketStatus.LISTED:
            raise EconomyException("商品已售出或已取消")
        await item_service.add_item(db, char, listing.item_config_id, listing.quantity, extra_attr=listing.item_extra)
        listing.status = MarketStatus.CANCELLED


shop_service = ShopService()
market_service = MarketService()
