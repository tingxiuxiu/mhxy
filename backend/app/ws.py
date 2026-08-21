from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import json
import asyncio
from typing import Dict, Set
import time

from .database import get_db
from .models.user import User
from .models.character import Character
from .redis_client import redis_client
from .services.battle_service import battle_service
from .services.chat_service import chat_service
from .game.enums import ChatChannel, BattleState
from sqlalchemy import select


router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: Dict[int, WebSocket] = {}

    async def connect(self, char_id: int, ws: WebSocket):
        await ws.accept()
        self.active[char_id] = ws
        await redis_client.set(f"wx:online:{char_id}", "1", ex=300)

    def disconnect(self, char_id: int):
        if char_id in self.active:
            del self.active[char_id]
        asyncio.create_task(redis_client.delete(f"wx:online:{char_id}"))

    async def send_personal(self, char_id: int, msg: dict):
        ws = self.active.get(char_id)
        if ws:
            try:
                await ws.send_json(msg)
            except Exception:
                pass

    async def broadcast(self, msg: dict, channel: str = "world"):
        key = f"wx:chat:channel:{channel}"
        await redis_client.lpush(key, json.dumps(msg, ensure_ascii=False))
        await redis_client.ltrim(key, 0, 99)
        for cid, ws in list(self.active.items()):
            try:
                await ws.send_json({"type": "chat", "data": msg})
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    char_id: int = Query(...),
):
    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        from jose import jwt
        from .config import settings
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = int(payload.get("sub"))
        except Exception:
            await websocket.close(code=4001)
            return
        user_res = await db.execute(select(User).where(User.id == user_id))
        user = user_res.scalar_one_or_none()
        if not user:
            await websocket.close(code=4001)
            return
        char_res = await db.execute(
            select(Character).where(Character.id == char_id, Character.user_id == user.id, Character.is_deleted == False)
        )
        char = char_res.scalar_one_or_none()
        if not char:
            await websocket.close(code=4003)
            return
        await manager.connect(char_id, websocket)
        await websocket.send_json({"type": "connected", "char_id": char_id, "name": char.name})
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                except Exception:
                    continue
                mtype = msg.get("type", "")
                if mtype == "ping":
                    await websocket.send_json({"type": "pong", "ts": int(time.time())})
                    await redis_client.set(f"wx:online:{char_id}", "1", ex=300)
                elif mtype == "chat":
                    content = msg.get("content", "").strip()
                    channel = msg.get("channel", "world")
                    if content and len(content) <= 200:
                        from .utils.sensitive import sensitive_filter
                        content = sensitive_filter.filter(content)
                        chat_msg = {
                            "channel": channel, "speaker_id": char_id,
                            "speaker_name": char.name, "content": content, "send_time": int(time.time())
                        }
                        if channel == "world":
                            cd_key = f"wx:chat:world:cd:{char_id}"
                            if not await redis_client.exists(cd_key):
                                await redis_client.set(cd_key, "1", ex=30)
                                await manager.broadcast(chat_msg, "world")
                            else:
                                await websocket.send_json({"type": "error", "msg": "世界频道冷却中"})
                        else:
                            await manager.send_personal(char_id, {"type": "chat", "data": chat_msg})
                elif mtype == "battle_command":
                    action = msg.get("action")
                    target = msg.get("target_id")
                    skill_id = msg.get("skill_id")
                    result = await battle_service.submit_command(char_id, char_id, __import__("enum").Enum("A", {"attack":1,"skill":2,"defend":3,"escape":4,"capture":5,"item":6})[action], target, skill_id)
                    await websocket.send_json({"type": "battle", "data": result})
                elif mtype == "battle_resolve":
                    result = await battle_service.resolve_turn(db, char_id)
                    await websocket.send_json({"type": "battle_resolved", "data": result})
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(char_id)
    finally:
        try:
            await db.close()
        except Exception:
            pass
