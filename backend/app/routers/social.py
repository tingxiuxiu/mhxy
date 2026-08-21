from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_current_char
from ..models.character import Character
from ..services.social_service import team_service
from ..services.chat_service import chat_service
from ..game.enums import ChatChannel

router = APIRouter(prefix="/api/social", tags=["社交"])


class InviteReq(BaseModel):
    target_char_id: int


class AcceptInviteReq(BaseModel):
    invite_id: int


class KickReq(BaseModel):
    member_id: int


@router.post("/team/create")
async def create_team(char: Character = Depends(get_current_char)):
    try:
        return await team_service.create_team(char.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/team/info")
async def team_info(char: Character = Depends(get_current_char)):
    t = await team_service.get_player_team(char.id)
    if not t:
        return {"in_team": False}
    return {"in_team": True, **t}


@router.post("/team/leave")
async def leave_team(char: Character = Depends(get_current_char)):
    try:
        return await team_service.leave_team(char.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/team/disband")
async def disband(char: Character = Depends(get_current_char)):
    try:
        return await team_service.disband_team(char.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class ChatReq(BaseModel):
    channel: str
    content: str
    target_id: int = None


@router.post("/chat/send")
async def send_chat(req: ChatReq, char: Character = Depends(get_current_char)):
    try:
        ch = ChatChannel(req.channel)
        return await chat_service.send_message(char.id, char.name, ch, req.content, req.target_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chat/history")
async def chat_history(channel: str = "world", target_id: int = None, char: Character = Depends(get_current_char)):
    ch = ChatChannel(channel)
    return await chat_service.get_history(ch, char.id, target_id)
