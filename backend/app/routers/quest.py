from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_current_char
from ..models.character import Character
from ..services.quest_service import quest_service

router = APIRouter(prefix="/api/quest", tags=["任务"])


class AcceptReq(BaseModel):
    quest_id: int


class SubmitReq(BaseModel):
    quest_id: int


@router.get("/available")
async def available(db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    return await quest_service.get_available_quests(db, char)


@router.get("/current")
async def current(db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    return await quest_service.get_current_quests(db, char)


@router.post("/accept")
async def accept(req: AcceptReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        cq = await quest_service.accept_quest(db, char, req.quest_id)
        await db.commit()
        return {"success": True, "char_quest_id": cq.id}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submit")
async def submit(req: SubmitReq, db: AsyncSession = Depends(get_db), char: Character = Depends(get_current_char)):
    try:
        result = await quest_service.submit_quest(db, char, req.quest_id)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
