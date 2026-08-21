from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_current_char
from ..models.character import Character
from ..services.guild_service import guild_service

router = APIRouter(prefix="/api/guild", tags=["帮派"])


class CreateGuildReq(BaseModel):
    name: str
    description: str = ""


class InviteReq(BaseModel):
    target_char_id: int


class JoinReq(BaseModel):
    guild_id: int


@router.post("/create")
async def create(req: CreateGuildReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        g = await guild_service.create_guild(db, char, req.name, req.description)
        await db.commit()
        return {"guild_id": g.id, "name": g.name}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my")
async def my_guild(db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    return await guild_service.get_char_guild(db, char)


@router.get("/{guild_id}")
async def guild_info(guild_id: int, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    info = await guild_service.get_guild_info(db, guild_id)
    if not info:
        raise HTTPException(status_code=404, detail="帮派不存在")
    return info


@router.post("/join")
async def join(req: JoinReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        await guild_service.join_guild(db, char, req.guild_id)
        await db.commit()
        return {"success": True}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/leave")
async def leave(db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        await guild_service.leave_guild(db, char)
        await db.commit()
        return {"success": True}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
