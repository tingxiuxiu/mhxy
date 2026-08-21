from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional, Dict, Any
from datetime import date
import random

from ..models.quest import QuestConfig, CharacterQuest
from ..models.character import Character
from ..models.map import NpcConfig, MapConfig
from ..game.enums import QuestStatus, QuestType
from ..utils.id_gen import generate_id
from ..exceptions import QuestException, ValidationException
from .character_service import character_service


class QuestService:
    @staticmethod
    async def get_available_quests(db: AsyncSession, char: Character) -> List[Dict[str, Any]]:
        today = date.today()
        result = await db.execute(
            select(QuestConfig).where(
                and_(
                    QuestConfig.is_active == True,
                    QuestConfig.level_min <= char.level,
                    (QuestConfig.level_max >= char.level) | (QuestConfig.level_max == 0),
                )
            )
        )
        configs = list(result.scalars().all())
        available = []
        for cfg in configs:
            if cfg.daily_limit > 0:
                count_key = f"wx:quest:daily:{char.id}:{today}"
                counts = await db.execute(
                    select(CharacterQuest).where(
                        and_(
                            CharacterQuest.character_id == char.id,
                            CharacterQuest.quest_id == cfg.id,
                            CharacterQuest.today_date == today,
                        )
                    )
                )
                done_today = counts.scalars().all()
                done_count = sum(1 for q in done_today if q.status == QuestStatus.COMPLETED)
                if done_count >= cfg.daily_limit:
                    continue
            active = await db.execute(
                select(CharacterQuest).where(
                    and_(
                        CharacterQuest.character_id == char.id,
                        CharacterQuest.quest_id == cfg.id,
                        CharacterQuest.status.in_([QuestStatus.IN_PROGRESS, QuestStatus.CAN_COMPLETE]),
                    )
                )
            )
            if active.scalar_one_or_none():
                continue
            available.append({
                "quest_id": cfg.id,
                "name": cfg.name,
                "type": cfg.type,
                "description": cfg.description,
                "level_min": cfg.level_min,
                "giver_npc_id": cfg.giver_npc_id,
            })
        return available

    @staticmethod
    async def get_current_quests(db: AsyncSession, char: Character) -> List[Dict[str, Any]]:
        result = await db.execute(
            select(CharacterQuest, QuestConfig)
            .join(QuestConfig, CharacterQuest.quest_id == QuestConfig.id)
            .where(
                and_(
                    CharacterQuest.character_id == char.id,
                    CharacterQuest.status.in_([QuestStatus.IN_PROGRESS, QuestStatus.CAN_COMPLETE]),
                )
            )
        )
        quests = []
        for cq, cfg in result.all():
            progress = await QuestService.get_progress(db, char, cq, cfg)
            quests.append({
                "quest_id": cfg.id,
                "name": cfg.name,
                "type": cfg.type,
                "status": cq.status,
                "current_step": cq.current_step,
                "progress_text": progress["text"],
                "progress_detail": cq.step_data,
                "can_complete": cq.status == QuestStatus.CAN_COMPLETE,
                "giver_npc_id": cfg.giver_npc_id,
            })
        return quests

    @staticmethod
    async def accept_quest(db: AsyncSession, char: Character, quest_id: int) -> CharacterQuest:
        cfg_result = await db.execute(select(QuestConfig).where(QuestConfig.id == quest_id))
        cfg = cfg_result.scalar_one_or_none()
        if not cfg or not cfg.is_active:
            raise QuestException("任务不存在")
        if char.level < cfg.level_min or (cfg.level_max > 0 and char.level > cfg.level_max):
            raise QuestException("等级不满足要求")
        existing = await db.execute(
            select(CharacterQuest).where(
                and_(
                    CharacterQuest.character_id == char.id,
                    CharacterQuest.quest_id == quest_id,
                    CharacterQuest.status.in_([QuestStatus.IN_PROGRESS, QuestStatus.CAN_COMPLETE]),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise QuestException("已接取该任务")
        today = date.today()
        if cfg.daily_limit > 0:
            done_result = await db.execute(
                select(CharacterQuest).where(
                    and_(
                        CharacterQuest.character_id == char.id,
                        CharacterQuest.quest_id == quest_id,
                        CharacterQuest.today_date == today,
                        CharacterQuest.status == QuestStatus.COMPLETED,
                    )
                )
            )
            done_count = len(done_result.scalars().all())
            if done_count >= cfg.daily_limit:
                raise QuestException("今日次数已用完")
        cq = CharacterQuest(
            id=generate_id(),
            character_id=char.id,
            quest_id=quest_id,
            status=QuestStatus.IN_PROGRESS,
            current_step=0,
            step_data={},
            today_date=today if cfg.daily_limit > 0 else None,
        )
        await QuestService._init_quest_steps(db, char, cq, cfg)
        db.add(cq)
        await db.flush()
        return cq

    @staticmethod
    async def _init_quest_steps(db: AsyncSession, char: Character, cq: CharacterQuest, cfg: QuestConfig):
        q_type = cfg.type
        if q_type == QuestType.NOVICE:
            cq.step_data = {"steps_total": len(cfg.steps), "steps_done": 0, "current_step_type": "talk",
                            "current_npc": cfg.steps[0].get("npc_id") if cfg.steps else None}
        elif q_type == QuestType.SHIMEN:
            task_type = random.choice(["patrol", "deliver", "collect", "show"])
            if task_type == "patrol":
                cq.step_data = {"sub_type": "patrol", "battles_done": 0, "battles_needed": 3}
            elif task_type == "deliver":
                npc_result = await db.execute(select(NpcConfig).order_by(__import__("sqlalchemy").func.random()).limit(1))
                target_npc = npc_result.scalar_one_or_none()
                cq.step_data = {"sub_type": "deliver", "target_npc_id": target_npc.id if target_npc else 3,
                                "target_npc_name": target_npc.name if target_npc else "未知"}
            elif task_type == "collect":
                items = [1, 2, 3]
                item_id = random.choice(items)
                cq.step_data = {"sub_type": "collect", "item_id": item_id, "item_count": random.randint(1, 3)}
            else:
                map_result = await db.execute(select(MapConfig).where(MapConfig.is_dark == True).order_by(__import__("sqlalchemy").func.random()).limit(1))
                target_map = map_result.scalar_one_or_none()
                cq.step_data = {"sub_type": "show", "target_map_id": target_map.id if target_map else 2,
                                "target_map_name": target_map.name if target_map else "未知"}
        elif q_type == QuestType.ZHUAGUI:
            ghost_types = ["血鬼", "僵尸", "牛头", "马面", "骷髅", "野鬼"]
            ghost = random.choice(ghost_types)
            map_result = await db.execute(select(MapConfig).where(MapConfig.is_dark == True).order_by(__import__("sqlalchemy").func.random()).limit(1))
            target_map = map_result.scalar_one_or_none()
            cq.step_data = {"ghost_type": ghost, "map_id": target_map.id if target_map else 2,
                            "map_name": target_map.name if target_map else "未知",
                            "x": random.randint(10, 90), "y": random.randint(10, 70), "defeated": False}
        elif q_type == QuestType.HUBIAO:
            destinations = [
                {"map_id": 5, "name": "大唐官府", "npc": "程咬金", "npc_id": 10},
                {"map_id": 6, "name": "傲来国", "npc": "驿站老板", "npc_id": 22},
            ]
            dest = random.choice(destinations)
            deposit = char.level * 1000
            cq.step_data = {"target_map_id": dest["map_id"], "target_name": dest["name"],
                            "target_npc": dest["npc"], "target_npc_id": dest["npc_id"],
                            "deposit": deposit, "arrived": False, "danger": random.randint(1, 3)}
        elif q_type == QuestType.DUNGEON:
            cq.step_data = {"fights_done": 0, "fights_total": 4, "boss_defeated": False}

    @staticmethod
    async def get_progress(db: AsyncSession, char: Character, cq: CharacterQuest, cfg: QuestConfig) -> Dict[str, Any]:
        data = cq.step_data
        q_type = cfg.type
        text = ""
        if q_type == QuestType.NOVICE:
            text = f"新手引导，第{data.get('steps_done', 0)+1}步"
        elif q_type == QuestType.SHIMEN:
            sub = data.get("sub_type")
            if sub == "patrol":
                text = f"在门派巡逻，已战斗{data.get('battles_done',0)}/{data.get('battles_needed',3)}场"
            elif sub == "deliver":
                text = f"送信给{data.get('target_npc_name','未知')}"
            elif sub == "collect":
                from .item_service import item_service
                count = await item_service.count_item(db, char, data.get("item_id", 1))
                text = f"寻找物品，已找到{count}/{data.get('item_count',1)}"
            else:
                text = f"去{data.get('target_map_name','未知')}示威"
        elif q_type == QuestType.ZHUAGUI:
            if data.get("defeated"):
                text = "鬼怪已消灭，可以回去找钟馗领奖"
            else:
                text = f"去{data.get('map_name','')}({data.get('x',0)},{data.get('y',0)})捉拿{data.get('ghost_type','')}"
        elif q_type == QuestType.HUBIAO:
            if data.get("arrived"):
                text = "镖银已送达，可以领取奖励"
            else:
                text = f"押送镖银到{data.get('target_name','')}找{data.get('target_npc','')}"
        elif q_type == QuestType.DUNGEON:
            if data.get("boss_defeated"):
                text = "副本已通关，可以领取奖励"
            else:
                text = f"副本进度：小怪{data.get('fights_done',0)}/{data.get('fights_total',4)}"
        return {"text": text}

    @staticmethod
    async def on_battle_win(db: AsyncSession, char: Character, battle_type: int, extra: dict = None):
        extra = extra or {}
        quests = await db.execute(
            select(CharacterQuest, QuestConfig)
            .join(QuestConfig, CharacterQuest.quest_id == QuestConfig.id)
            .where(
                and_(
                    CharacterQuest.character_id == char.id,
                    CharacterQuest.status == QuestStatus.IN_PROGRESS,
                )
            )
        )
        for cq, cfg in quests.all():
            updated = False
            if cfg.type == QuestType.SHIMEN and cq.step_data.get("sub_type") == "patrol":
                cq.step_data["battles_done"] = cq.step_data.get("battles_done", 0) + 1
                if cq.step_data["battles_done"] >= cq.step_data.get("battles_needed", 3):
                    cq.status = QuestStatus.CAN_COMPLETE
                updated = True
            elif cfg.type == QuestType.ZHUAGUI and extra.get("is_zhuagui"):
                cq.step_data["defeated"] = True
                cq.status = QuestStatus.CAN_COMPLETE
                updated = True
            elif cfg.type == QuestType.DUNGEON:
                if extra.get("is_dungeon_boss"):
                    cq.step_data["boss_defeated"] = True
                    cq.status = QuestStatus.CAN_COMPLETE
                elif extra.get("is_dungeon_trash"):
                    cq.step_data["fights_done"] = cq.step_data.get("fights_done", 0) + 1
                    if cq.step_data["fights_done"] >= cq.step_data.get("fights_total", 4):
                        pass
                updated = True
            if updated:
                pass

    @staticmethod
    async def on_npc_talk(db: AsyncSession, char: Character, npc_id: int):
        quests = await db.execute(
            select(CharacterQuest, QuestConfig)
            .join(QuestConfig, CharacterQuest.quest_id == QuestConfig.id)
            .where(
                and_(
                    CharacterQuest.character_id == char.id,
                    CharacterQuest.status.in_([QuestStatus.IN_PROGRESS, QuestStatus.CAN_COMPLETE]),
                )
            )
        )
        for cq, cfg in quests.all():
            if cq.status == QuestStatus.CAN_COMPLETE and cfg.giver_npc_id == npc_id:
                continue
            if cfg.type == QuestType.NOVICE:
                steps = cfg.steps
                if cq.current_step < len(steps) and steps[cq.current_step].get("npc_id") == npc_id:
                    cq.current_step += 1
                    cq.step_data["steps_done"] = cq.current_step
                    if cq.current_step >= len(steps):
                        cq.status = QuestStatus.CAN_COMPLETE
                    else:
                        cq.step_data["current_npc"] = steps[cq.current_step].get("npc_id")
            elif cfg.type == QuestType.SHIMEN and cq.step_data.get("sub_type") == "deliver":
                if cq.step_data.get("target_npc_id") == npc_id:
                    cq.status = QuestStatus.CAN_COMPLETE
            elif cfg.type == QuestType.HUBIAO:
                if cq.step_data.get("target_npc_id") == npc_id:
                    cq.step_data["arrived"] = True
                    cq.status = QuestStatus.CAN_COMPLETE

    @staticmethod
    async def submit_quest(db: AsyncSession, char: Character, quest_id: int) -> dict:
        result = await db.execute(
            select(CharacterQuest, QuestConfig)
            .join(QuestConfig, CharacterQuest.quest_id == QuestConfig.id)
            .where(
                and_(
                    CharacterQuest.character_id == char.id,
                    CharacterQuest.quest_id == quest_id,
                    CharacterQuest.status.in_([QuestStatus.CAN_COMPLETE, QuestStatus.IN_PROGRESS]),
                )
            )
        )
        row = result.first()
        if not row:
            raise QuestException("没有可提交的任务")
        cq, cfg = row
        if cq.status != QuestStatus.CAN_COMPLETE:
            raise QuestException("任务尚未完成")
        rewards = cfg.rewards if isinstance(cfg.rewards, dict) else {}
        exp = rewards.get("exp", 0)
        cash = rewards.get("cash", 0)
        items = rewards.get("items", [])
        round_bonus = 1.0
        if cfg.type == QuestType.SHIMEN:
            today = date.today()
            key = f"wx:quest:shimen:round:{char.id}:{today}"
            import redis
            round_num = await redis_client.incr(key) if False else 1
            today_result = await db.execute(
                select(CharacterQuest).where(
                    and_(CharacterQuest.character_id == char.id, CharacterQuest.quest_id == cfg.id,
                         CharacterQuest.today_date == today, CharacterQuest.status == QuestStatus.COMPLETED)
                )
            )
            round_num = len(today_result.scalars().all()) + 1
            round_bonus = 1 + (round_num - 1) * 0.1
            exp = int(rewards.get("exp_base", 5000) * round_bonus)
            cash = int(rewards.get("cash_base", 3000) * round_bonus)
            if cq.step_data.get("sub_type") == "deliver":
                deposit_return = cq.step_data.get("deposit", 0)
                cash += deposit_return
        if cfg.type == QuestType.ZHUAGUI:
            today_result = await db.execute(
                select(CharacterQuest).where(
                    and_(CharacterQuest.character_id == char.id, CharacterQuest.quest_id == cfg.id,
                         CharacterQuest.today_date == date.today(), CharacterQuest.status == QuestStatus.COMPLETED)
                )
            )
            round_num = len(today_result.scalars().all()) + 1
            round_bonus = 1 + (round_num - 1) * 0.15
            exp = int(rewards.get("exp_base", 10000) * round_bonus)
            cash = int(rewards.get("cash_base", 5000) * round_bonus)
            if round_num == 10:
                items = [{"item_id": 3, "count": 2}, {"item_id": 20, "count": 1}]
        level_result = await character_service.add_exp(db, char, exp)
        await character_service.add_cash(char, cash)
        from .item_service import item_service
        got_items = []
        for it in items:
            try:
                await item_service.add_item(db, char, it["item_id"], it.get("count", 1))
                got_items.append(it)
            except Exception:
                pass
        cq.status = QuestStatus.COMPLETED
        cq.completed_at = __import__("datetime").datetime.utcnow()
        cq.times_completed += 1
        return {
            "exp_gained": exp,
            "cash_gained": cash,
            "items": got_items,
            "leveled_up": level_result.get("leveled_up", False),
            "new_level": level_result.get("new_level", char.level),
        }


from ..redis_client import redis_client
quest_service = QuestService()
