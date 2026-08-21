from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Dict, Optional
import json

from ..models.social import FriendRequest, TeamInvite
from ..models.character import Character
from ..game.enums import RequestStatus
from ..utils.id_gen import generate_id
from ..exceptions import SocialException, ValidationException
from ..redis_client import redis_client


class TeamService:
    TEAM_CACHE_PREFIX = "wx:team:"

    @staticmethod
    async def create_team(leader_id: int) -> dict:
        team_key = f"{TeamService.TEAM_CACHE_PREFIX}{leader_id}"
        if await redis_client.exists(team_key):
            raise SocialException("你已经在队伍中了")
        existing_team = await TeamService.get_player_team(leader_id)
        if existing_team:
            raise SocialException("你已经在队伍中了")
        team = {"team_id": leader_id, "leader_id": leader_id, "members": [leader_id]}
        await redis_client.set(team_key, json.dumps(team))
        await redis_client.set(f"wx:player:team:{leader_id}", str(leader_id))
        return team

    @staticmethod
    async def get_player_team(player_id: int) -> Optional[dict]:
        team_id = await redis_client.get(f"wx:player:team:{player_id}")
        if not team_id:
            return None
        team_key = f"{TeamService.TEAM_CACHE_PREFIX}{team_id}"
        data = await redis_client.get(team_key)
        if not data:
            await redis_client.delete(f"wx:player:team:{player_id}")
            return None
        try:
            return json.loads(data)
        except Exception:
            return None

    @staticmethod
    async def invite(db: AsyncSession, leader_id: int, target_char_id: int) -> dict:
        team = await TeamService.get_player_team(leader_id)
        if not team or team["leader_id"] != leader_id:
            raise SocialException("只有队长可以邀请")
        if len(team["members"]) >= 5:
            raise SocialException("队伍已满")
        if target_char_id in team["members"]:
            raise SocialException("该玩家已在队伍中")
        target_team = await TeamService.get_player_team(target_char_id)
        if target_team:
            raise SocialException("对方已有队伍")
        invite = TeamInvite(
            id=generate_id(), from_char_id=leader_id, to_char_id=target_char_id,
            target_type="team", target_id=team["team_id"], status=RequestStatus.PENDING
        )
        db.add(invite)
        return {"invite_id": invite.id}

    @staticmethod
    async def accept_invite(db: AsyncSession, invite_id: int, char_id: int) -> dict:
        result = await db.execute(select(TeamInvite).where(TeamInvite.id == invite_id))
        invite = result.scalar_one_or_none()
        if not invite or invite.to_char_id != char_id:
            raise SocialException("邀请不存在")
        if invite.status != RequestStatus.PENDING:
            raise SocialException("邀请已处理")
        team = await TeamService.get_player_team(invite.from_char_id)
        if not team:
            invite.status = RequestStatus.EXPIRED
            raise SocialException("队伍已解散")
        if len(team["members"]) >= 5:
            invite.status = RequestStatus.REJECTED
            raise SocialException("队伍已满")
        my_team = await TeamService.get_player_team(char_id)
        if my_team:
            invite.status = RequestStatus.REJECTED
            raise SocialException("你已在队伍中")
        team["members"].append(char_id)
        team_key = f"{TeamService.TEAM_CACHE_PREFIX}{team['team_id']}"
        await redis_client.set(team_key, json.dumps(team))
        await redis_client.set(f"wx:player:team:{char_id}", str(team["team_id"]))
        invite.status = RequestStatus.ACCEPTED
        return team

    @staticmethod
    async def leave_team(char_id: int) -> dict:
        team = await TeamService.get_player_team(char_id)
        if not team:
            raise SocialException("你不在队伍中")
        if team["leader_id"] == char_id:
            return await TeamService.disband_team(char_id)
        team["members"] = [m for m in team["members"] if m != char_id]
        team_key = f"{TeamService.TEAM_CACHE_PREFIX}{team['team_id']}"
        await redis_client.set(team_key, json.dumps(team))
        await redis_client.delete(f"wx:player:team:{char_id}")
        return {"success": True, "action": "left"}

    @staticmethod
    async def kick_member(leader_id: int, member_id: int) -> dict:
        team = await TeamService.get_player_team(leader_id)
        if not team or team["leader_id"] != leader_id:
            raise SocialException("只有队长可以踢人")
        if member_id == leader_id:
            raise SocialException("不能踢自己")
        if member_id not in team["members"]:
            raise SocialException("不在队伍中")
        team["members"] = [m for m in team["members"] if m != member_id]
        team_key = f"{TeamService.TEAM_CACHE_PREFIX}{team['team_id']}"
        await redis_client.set(team_key, json.dumps(team))
        await redis_client.delete(f"wx:player:team:{member_id}")
        return {"success": True}

    @staticmethod
    async def disband_team(leader_id: int) -> dict:
        team = await TeamService.get_player_team(leader_id)
        if not team or team["leader_id"] != leader_id:
            raise SocialException("你不是队长")
        for m in team["members"]:
            await redis_client.delete(f"wx:player:team:{m}")
        team_key = f"{TeamService.TEAM_CACHE_PREFIX}{team['team_id']}"
        await redis_client.delete(team_key)
        return {"success": True, "action": "disbanded"}


class FriendService:
    @staticmethod
    async def add_friend(db: AsyncSession, char_id: int, target_char_id: int) -> dict:
        if char_id == target_char_id:
            raise SocialException("不能添加自己")
        result = await db.execute(select(Character).where(Character.id == target_char_id))
        if not result.scalar_one_or_none():
            raise SocialException("玩家不存在")
        return {"success": True, "friend_id": target_char_id}

    @staticmethod
    async def get_friends_online() -> List[int]:
        cursor = b"0"
        friends = []
        return friends


class TradeService:
    LOCK_KEY = "wx:trade:lock:"
    PREFIX = "wx:trade:"

    @staticmethod
    async def start_trade(char_id: int, target_id: int) -> dict:
        if char_id == target_id:
            raise SocialException("不能和自己交易")
        lock_key = f"{TradeService.LOCK_KEY}{min(char_id, target_id)}:{max(char_id, target_id)}"
        locked = await redis_client.set(lock_key, "1", nx=True, ex=300)
        if not locked:
            raise SocialException("正在交易中")
        trade_id = f"{char_id}:{target_id}"
        trade = {"initiator": char_id, "target": target_id, "confirm_a": False, "confirm_b": False,
                 "items_a": [], "items_b": [], "gold_a": 0, "gold_b": 0}
        await redis_client.set(f"{TradeService.PREFIX}{trade_id}", json.dumps(trade), ex=300)
        return {"trade_id": trade_id}


team_service = TeamService()
friend_service = FriendService()
trade_service = TradeService()
