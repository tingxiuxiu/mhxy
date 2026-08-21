from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from typing import List, Optional, Dict, Any
import json

from ..models.guild import Guild, GuildMember, GuildLog
from ..models.character import Character
from ..game.enums import GuildPosition
from ..utils.id_gen import generate_id
from ..exceptions import GuildException, ValidationException
from ..redis_client import redis_client


class GuildService:
    @staticmethod
    async def create_guild(db: AsyncSession, char: Character, name: str, description: str = "") -> Guild:
        if char.level < 30:
            raise GuildException("创建帮派需要30级以上")
        if char.cash < 1000000:
            raise GuildException("创建帮派需要100万游戏币")
        existing = await db.execute(select(Guild).where(Guild.name == name))
        if existing.scalar_one_or_none():
            raise GuildException("帮派名称已存在")
        if not (2 <= len(name) <= 12):
            raise ValidationException("帮派名称2-12字")
        char.cash -= 1000000
        guild = Guild(
            id=generate_id(), name=name, leader_id=char.id, level=1,
            members_count=1, funds=0, current_notice="欢迎加入！", description=description
        )
        db.add(guild)
        await db.flush()
        member = GuildMember(
            id=generate_id(), guild_id=guild.id, character_id=char.id,
            position=GuildPosition.LEADER, contribution=0
        )
        db.add(member)
        log = GuildLog(
            id=generate_id(), guild_id=guild.id, char_id=char.id,
            action_type="guild_create", content=f"{char.name}创建了帮派{name}"
        )
        db.add(log)
        await db.flush()
        return guild

    @staticmethod
    async def get_guild_info(db: AsyncSession, guild_id: int) -> Optional[Dict[str, Any]]:
        result = await db.execute(select(Guild).where(Guild.id == guild_id))
        g = result.scalar_one_or_none()
        if not g:
            return None
        members_result = await db.execute(
            select(GuildMember, Character)
            .join(Character, GuildMember.character_id == Character.id)
            .where(GuildMember.guild_id == guild_id)
        )
        members = []
        leader_name = ""
        for m, c in members_result.all():
            members.append({
                "char_id": c.id, "name": c.name, "level": c.level, "job": c.job,
                "position": m.position, "contribution": m.contribution, "joined_at": m.joined_at
            })
            if c.id == g.leader_id:
                leader_name = c.name
        return {
            "id": g.id, "name": g.name, "level": g.level, "leader_id": g.leader_id, "leader_name": leader_name,
            "members_count": g.members_count, "funds": g.funds, "notice": g.current_notice,
            "description": g.description, "members": members,
        }

    @staticmethod
    async def get_char_guild(db: AsyncSession, char: Character) -> Optional[Dict[str, Any]]:
        result = await db.execute(
            select(GuildMember).where(GuildMember.character_id == char.id)
        )
        m = result.scalar_one_or_none()
        if not m:
            return None
        info = await GuildService.get_guild_info(db, m.guild_id)
        if info:
            info["my_position"] = m.position
            info["my_contribution"] = m.contribution
        return info

    @staticmethod
    async def invite_member(db: AsyncSession, char: Character, target_char_id: int) -> dict:
        my_result = await db.execute(select(GuildMember).where(GuildMember.character_id == char.id))
        me = my_result.scalar_one_or_none()
        if not me:
            raise GuildException("你还没有帮派")
        if me.position not in [GuildPosition.LEADER, GuildPosition.DEPUTY]:
            raise GuildException("只有帮主/副帮主可以邀请")
        target_result = await db.execute(
            select(Character, GuildMember)
            .outerjoin(GuildMember, GuildMember.character_id == Character.id)
            .where(Character.id == target_char_id)
        )
        row = target_result.first()
        if not row:
            raise GuildException("玩家不存在")
        target_c, target_m = row
        if target_m:
            raise GuildException("对方已有帮派")
        if target_c.level < 10:
            raise GuildException("对方等级不足10级")
        return {"target_name": target_c.name, "target_id": target_c.id}

    @staticmethod
    async def join_guild(db: AsyncSession, char: Character, guild_id: int) -> GuildMember:
        existing = await db.execute(select(GuildMember).where(GuildMember.character_id == char.id))
        if existing.scalar_one_or_none():
            raise GuildException("你已有帮派")
        g_result = await db.execute(select(Guild).where(Guild.id == guild_id))
        g = g_result.scalar_one_or_none()
        if not g:
            raise GuildException("帮派不存在")
        if g.members_count >= g.level * 50:
            raise GuildException("帮派已满员")
        member = GuildMember(
            id=generate_id(), guild_id=guild_id, character_id=char.id,
            position=GuildPosition.MEMBER, contribution=0
        )
        db.add(member)
        g.members_count += 1
        log = GuildLog(
            id=generate_id(), guild_id=guild_id, char_id=char.id,
            action_type="member_join", content=f"{char.name}加入了帮派"
        )
        db.add(log)
        await db.flush()
        return member

    @staticmethod
    async def leave_guild(db: AsyncSession, char: Character):
        my_result = await db.execute(select(GuildMember).where(GuildMember.character_id == char.id))
        me = my_result.scalar_one_or_none()
        if not me:
            raise GuildException("你没有帮派")
        g_result = await db.execute(select(Guild).where(Guild.id == me.guild_id))
        g = g_result.scalar_one_or_none()
        if g and g.leader_id == char.id:
            raise GuildException("帮主不能退帮，请先转让或解散")
        await db.delete(me)
        if g:
            g.members_count -= 1
            log = GuildLog(
                id=generate_id(), guild_id=g.id, char_id=char.id,
                action_type="member_leave", content=f"{char.name}离开了帮派"
            )
            db.add(log)


guild_service = GuildService()
