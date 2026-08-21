from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..deps import get_db, get_current_user, get_current_char
from ..models.user import User
from ..models.character import Character
from ..services.character_service import character_service
from ..exceptions import GameException

router = APIRouter(prefix="/api/character", tags=["角色"])


class CreateCharReq(BaseModel):
    name: str
    job: int


class AllocatePointReq(BaseModel):
    strength: int = 0
    magic: int = 0
    vitality: int = 0
    endurance: int = 0
    agility: int = 0


@router.post("/create")
async def create_char(req: CreateCharReq, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        char = await character_service.create_character(db, user.id, req.name, req.job)
        await db.commit()
        return {"char_id": char.id, "name": char.name}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
async def list_chars(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    chars = await character_service.get_user_characters(db, user.id)
    return [{"id": c.id, "name": c.name, "level": c.level, "job": c.job, "map_id": c.map_id} for c in chars]


@router.get("/info")
async def get_info(db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    stats = character_service.get_combat_stats(char)
    from ..services.item_service import item_service
    equipped = await item_service.get_equipped_items(db, char)
    bonus = await item_service.get_item_bonus(db, char)
    return {
        "id": char.id, "name": char.name, "level": char.level, "job": char.job,
        "exp": char.exp, "next_exp": character_service.calc_next_exp(char.level),
        "hp": char.hp, "mp": char.mp, "cash": char.cash, "reserve_cash": char.reserve_cash,
        "hp_max": stats["hp_max"] + bonus.get("hp", 0),
        "mp_max": stats["mp_max"] + bonus.get("mp", 0),
        "damage": stats["damage"] + bonus.get("damage", 0),
        "defense": stats["defense"] + bonus.get("defense", 0),
        "speed": stats["speed"] + bonus.get("speed", 0),
        "magic_damage": stats["magic_damage"] + bonus.get("magic_damage", 0),
        "magic_defense": stats["magic_defense"] + bonus.get("magic_defense", 0),
        "attr_points": char.attr_points,
        "strength": char.strength, "magic": char.magic, "vitality": char.vitality,
        "endurance": char.endurance, "agility": char.agility,
        "equipped": equipped,
        "map_id": char.map_id, "pos_x": char.pos_x, "pos_y": char.pos_y,
    }


@router.post("/allocate")
async def allocate(req: AllocatePointReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        await character_service.allocate_point(db, char, req.strength, req.magic, req.vitality, req.endurance, req.agility)
        await db.commit()
        return {"success": True}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/heal")
async def heal(db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    if char.cash < 100:
        raise HTTPException(status_code=400, detail="治疗需要100金币")
    char.cash -= 100
    stats = character_service.get_combat_stats(char)
    char.hp = stats["hp_max"]
    char.mp = stats["mp_max"]
    await db.commit()
    return {"hp": char.hp, "mp": char.mp, "cash": char.cash}
