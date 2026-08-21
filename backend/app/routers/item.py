from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_current_char
from ..models.character import Character
from ..services.item_service import item_service
from ..game.enums import EquipSlot

router = APIRouter(prefix="/api/item", tags=["物品"])


class UseItemReq(BaseModel):
    char_item_id: int
    target_id: int = None


class EquipReq(BaseModel):
    slot: int


@router.get("/bag")
async def get_bag(db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    items = await item_service.get_bag_items(db, char)
    result = []
    for it in items:
        from ..models.item import ItemConfig
        from sqlalchemy import select
        cfg = await db.execute(select(ItemConfig).where(ItemConfig.id == it.item_config_id))
        c = cfg.scalar_one_or_none()
        result.append({
            "instance_id": it.id, "config_id": it.item_config_id, "name": c.name if c else "",
            "count": it.quantity, "type": c.type if c else "", "subtype": c.subtype if c else "",
            "bind_type": it.bind_type, "effect": c.effect if c else {},
        })
    return result


@router.post("/use")
async def use(req: UseItemReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        result = await item_service.use_item(db, char, req.char_item_id, req.target_id)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/equip/{slot}")
async def equip(slot: int, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        result = await item_service.unequip_item(db, char, slot)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
