from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_current_char
from ..models.character import Character
from ..services.map_service import map_service

router = APIRouter(prefix="/api/map", tags=["地图"])


class MoveMapReq(BaseModel):
    target_map_id: int


class MoveCoordReq(BaseModel):
    direction: str


@router.get("/current")
async def current_map(db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    return await map_service.get_current_map_info(db, char)


@router.get("/list")
async def list_maps(db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    maps = await map_service.get_all_maps(db)
    return [{"id": m.id, "name": m.name, "type": m.type} for m in maps]


@router.post("/move/map")
async def move_map(req: MoveMapReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        target, x, y = await map_service.move_to_map(db, char, req.target_map_id)
        await map_service.teleport(char, target.id, x, y)
        await db.commit()
        return {"map_id": target.id, "name": target.name, "pos_x": x, "pos_y": y}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/move/coord")
async def move_coord(req: MoveCoordReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        map_cfg = await map_service.get_map(db, char.map_id)
        await map_service.move_coord(char, req.direction, map_cfg)
        encounter = await map_service.check_encounter(db, map_cfg)
        await db.commit()
        return {"pos_x": char.pos_x, "pos_y": char.pos_y, "encounter": encounter is not None}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
