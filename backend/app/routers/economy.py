from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_current_char
from ..models.character import Character
from ..services.economy_service import shop_service, market_service

router = APIRouter(prefix="/api/economy", tags=["经济"])


class BuyShopReq(BaseModel):
    item_config_id: int
    count: int = 1


class SellReq(BaseModel):
    char_item_id: int
    count: int = 1


class ListReq(BaseModel):
    char_item_id: int
    price_per_unit: int
    count: int = 1


class BuyMarketReq(BaseModel):
    listing_id: int
    count: int = 1


class CancelReq(BaseModel):
    listing_id: int


@router.get("/shop/{shop_id}")
async def shop_items(shop_id: int, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    return await shop_service.get_shop_items(db, shop_id)


@router.post("/shop/buy")
async def buy_shop(req: BuyShopReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        result = await shop_service.buy_item(db, char, req.item_config_id, req.count)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/shop/sell")
async def sell(req: SellReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        result = await shop_service.sell_item(db, char, req.char_item_id, req.count)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/market/search")
async def search_market(item_name: str = "", page: int = 1, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    listings = await market_service.search_listings(db, item_name, page)
    return [{"id": l.id, "item_name": l.item_name, "price": l.price_per_unit, "quantity": l.quantity,
             "seller": l.seller_name} for l in listings]


@router.post("/market/list")
async def list_item(req: ListReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        l = await market_service.list_item(db, char, req.char_item_id, req.price_per_unit, req.count)
        await db.commit()
        return {"listing_id": l.id}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/market/buy")
async def buy_market(req: BuyMarketReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        result = await market_service.buy_listing(db, char, req.listing_id, req.count)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/market/cancel")
async def cancel_market(req: CancelReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        await market_service.cancel_listing(db, char, req.listing_id)
        await db.commit()
        return {"success": True}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
