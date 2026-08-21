from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..deps import get_db, get_current_char
from ..models.character import Character
from ..services.battle_service import battle_service
from ..services.map_service import map_service
from ..game.enums import ActionType

router = APIRouter(prefix="/api/battle", tags=["战斗"])


class BattleActionReq(BaseModel):
    action_type: str
    target_unit_id: str = None
    skill_id: int = None
    item_id: int = None


@router.post("/start/random")
async def start_random(db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        map_cfg = await map_service.get_map(db, char.map_id)
        if not map_cfg or not map_cfg.is_dark:
            raise HTTPException(status_code=400, detail="当前地图无法遇敌")
        monsters = await map_service.check_encounter(db, map_cfg)
        if not monsters:
            return {"encounter": False}
        result = await battle_service.start_battle(db, char, monsters, battle_type=1)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/command")
async def command(req: BattleActionReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        action_map = {
            "attack": ActionType.ATTACK, "skill": ActionType.SKILL, "defend": ActionType.DEFEND,
            "escape": ActionType.ESCAPE, "capture": ActionType.CAPTURE, "item": ActionType.ITEM,
        }
        act = action_map.get(req.action_type)
        if not act:
            raise HTTPException(status_code=400, detail="无效指令")
        result = await battle_service.submit_command(
            char.id, char.id, act, req.target_unit_id, req.skill_id, req.item_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/state")
async def state(char: Character = Depends(get_current_char)):
    s = await battle_service.get_battle(char.id)
    if not s:
        return {"in_battle": False}
    return {"in_battle": True, "battle_id": s.battle_id, "turn": s.turn, "state": s.state.value,
            "player_units": [{"unit_id": u.unit_id, "name": u.name, "hp": u.hp, "hp_max": u.hp_max,
                              "mp": u.mp, "mp_max": u.mp_max, "is_alive": u.is_alive} for u in s.player_units],
            "enemy_units": [{"unit_id": u.unit_id, "name": u.name, "hp": u.hp, "hp_max": u.hp_max,
                             "mp": u.mp, "mp_max": u.mp_max, "is_alive": u.is_alive} for u in s.enemy_units]}


@router.post("/resolve")
async def resolve(db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        result = await battle_service.resolve_turn(db, char.id)
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
