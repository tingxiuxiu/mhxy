from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Tuple, Optional, Dict, Any
import random
import time
import json

from .battle_state import BattleState, BattleUnit, BattleCommand, ActionResult, BuffState
from ..models.character import Character
from ..models.monster import MonsterConfig
from ..models.pet import PetConfig, CharacterPet
from ..game.enums import BattleSide, BattleCharType, ActionType, BattleType, BattleState as BattleStateEnum
from ..game.formulas import calc_damage, calc_hit, calc_crit, calc_combat_stats, calc_monster_stats, calc_pet_combat_stats
from ..exceptions import BattleException
from ..redis_client import redis_client
from ..utils.id_gen import generate_id
from .character_service import character_service
from .item_service import item_service
from .pet_service import pet_service
from .quest_service import quest_service


BATTLE_KEY_PREFIX = "wx:battle:"


class BattleService:
    @staticmethod
    async def _save_battle(state: BattleState):
        data = {
            "battle_id": state.battle_id,
            "battle_type": state.battle_type,
            "map_id": state.map_id,
            "state": state.state.value,
            "turn": state.turn,
            "round_start_ts": state.round_start_ts,
            "extra_data": state.extra_data,
            "player_units": [BattleService._unit_to_dict(u) for u in state.player_units],
            "enemy_units": [BattleService._unit_to_dict(u) for u in state.enemy_units],
        }
        key = f"{BATTLE_KEY_PREFIX}{state.battle_id}"
        await redis_client.set(key, json.dumps(data, ensure_ascii=False), ex=1800)

    @staticmethod
    def _unit_to_dict(u: BattleUnit) -> dict:
        return {
            "unit_id": u.unit_id, "char_type": u.char_type.value, "side": u.side.value, "position": u.position,
            "char_id": u.char_id, "name": u.name, "level": u.level, "hp": u.hp, "mp": u.mp,
            "hp_max": u.hp_max, "mp_max": u.mp_max, "damage": u.damage, "defense": u.defense,
            "speed": u.speed, "magic_damage": u.magic_damage, "magic_defense": u.magic_defense,
            "hit": u.hit, "is_dead": u.is_dead, "is_alive": u.is_alive, "skills": u.skills, "extra": u.extra,
        }

    @staticmethod
    def _unit_from_dict(d: dict) -> BattleUnit:
        return BattleUnit(
            unit_id=d["unit_id"], char_type=BattleCharType(d["char_type"]), side=BattleSide(d["side"]),
            position=d["position"], char_id=d["char_id"], name=d["name"], level=d["level"],
            hp=d["hp"], mp=d["mp"], hp_max=d["hp_max"], mp_max=d["mp_max"], damage=d["damage"],
            defense=d["defense"], speed=d["speed"], magic_damage=d.get("magic_damage", 0),
            magic_defense=d.get("magic_defense", 0), hit=d.get("hit", 80), is_dead=d.get("is_dead", False),
            is_alive=d.get("is_alive", True), skills=d.get("skills", []), extra=d.get("extra", {}),
        )

    @staticmethod
    async def get_battle(battle_id_or_char: int) -> Optional[BattleState]:
        if isinstance(battle_id_or_char, int) and await redis_client.exists(f"{BATTLE_KEY_PREFIX}{battle_id_or_char}"):
            key = f"{BATTLE_KEY_PREFIX}{battle_id_or_char}"
        else:
            cursor = b"0"
            found = None
            # simple lookup by char id through player_units is complex; use char mapping
            mapping_key = f"wx:char:battle:{battle_id_or_char}"
            bid = await redis_client.get(mapping_key)
            if not bid:
                return None
            key = f"{BATTLE_KEY_PREFIX}{bid.decode() if isinstance(bid, bytes) else bid}"
        data = await redis_client.get(key)
        if not data:
            return None
        try:
            d = json.loads(data)
            state = BattleState(
                battle_id=d["battle_id"], battle_type=d["battle_type"], map_id=d["map_id"],
                state=BattleStateEnum(d["state"]), turn=d["turn"], round_start_ts=d.get("round_start_ts", 0),
                extra_data=d.get("extra_data", {}),
                player_units=[BattleService._unit_from_dict(u) for u in d.get("player_units", [])],
                enemy_units=[BattleService._unit_from_dict(u) for u in d.get("enemy_units", [])],
            )
            return state
        except Exception:
            return None

    @staticmethod
    async def _bind_char(char_id: int, battle_id: int):
        await redis_client.set(f"wx:char:battle:{char_id}", str(battle_id), ex=1800)

    @staticmethod
    async def _unbind_char(char_id: int):
        await redis_client.delete(f"wx:char:battle:{char_id}")

    @staticmethod
    async def start_battle(db: AsyncSession, char: Character, monsters: List[Tuple[MonsterConfig, int]],
                           battle_type: int = BattleType.WILD, extra: dict = None) -> dict:
        existing = await BattleService.get_battle(char.id)
        if existing:
            raise BattleException("已在战斗中")
        battle_id = generate_id()
        player_units = []
        stats = calc_combat_stats(char.level, char.job, char.strength, char.magic, char.vitality, char.endurance, char.agility, char.practice_phys)
        bonus = await item_service.get_item_bonus(db, char)
        player_units.append(BattleUnit(
            unit_id=f"p_{char.id}", char_type=BattleCharType.PLAYER, side=BattleSide.OUR,
            position=0, char_id=char.id, name=char.name, level=char.level,
            hp=char.hp, mp=char.mp,
            hp_max=stats["hp_max"] + bonus.get("hp", 0), mp_max=stats["mp_max"] + bonus.get("mp", 0),
            damage=stats["damage"] + bonus.get("damage", 0), defense=stats["defense"] + bonus.get("defense", 0),
            speed=stats["speed"] + bonus.get("speed", 0),
            magic_damage=stats["magic_damage"] + bonus.get("magic_damage", 0),
            magic_defense=stats["magic_defense"] + bonus.get("magic_defense", 0),
            hit=90,
        ))
        pet_row = await pet_service.get_battle_pet(db, char)
        if pet_row:
            pet, pet_cfg = pet_row
            ps = calc_pet_combat_stats(pet.level, pet.attr_gz, pet.attr_fy, pet.attr_tz, pet.attr_sd, pet.attr_fz, pet.growth)
            player_units.append(BattleUnit(
                unit_id=f"pet_{pet.id}", char_type=BattleCharType.PET, side=BattleSide.OUR,
                position=1, char_id=pet.id, name=pet.nickname, level=pet.level,
                hp=pet.hp, mp=pet.mp, hp_max=ps["hp_max"], mp_max=ps["mp_max"],
                damage=ps["damage"], defense=ps["defense"], speed=ps["speed"],
                magic_damage=ps["magic_damage"], magic_defense=ps["magic_defense"], hit=85,
            ))
        enemy_units = []
        for i, (mcfg, level) in enumerate(monsters):
            mstats = calc_monster_stats(mcfg, level)
            enemy_units.append(BattleUnit(
                unit_id=f"m_{mcfg.id}_{i}", char_type=BattleCharType.MONSTER, side=BattleSide.ENEMY,
                position=i, char_id=mcfg.id, name=mcfg.name, level=level,
                hp=mstats["hp_max"], mp=mstats["mp_max"], hp_max=mstats["hp_max"], mp_max=mstats["mp_max"],
                damage=mstats["damage"], defense=mstats["defense"], speed=mstats["speed"],
                magic_damage=mstats["magic_damage"], magic_defense=mstats["magic_defense"], hit=80,
                extra={"exp": mstats["exp_reward"], "cash": mstats["cash_reward"],
                       "drops": mcfg.drops, "monster_id": mcfg.id},
            ))
        state = BattleState(
            battle_id=battle_id, battle_type=battle_type, map_id=char.map_id,
            state=BattleStateEnum.ONGOING, turn=1, player_units=player_units, enemy_units=enemy_units,
            round_start_ts=time.time(), extra_data=extra or {},
        )
        await BattleService._save_battle(state)
        for u in player_units:
            await BattleService._bind_char(u.char_id, battle_id)
        return {"battle_id": battle_id, "turn": 1,
                "player_units": [u.to_dict() for u in player_units],
                "enemy_units": [u.to_dict() for u in enemy_units]}

    @staticmethod
    async def submit_command(char_id: int, unit_id: str, action: ActionType,
                             target_id: Optional[str] = None, skill_id: Optional[int] = None,
                             item_id: Optional[int] = None) -> dict:
        state = await BattleService.get_battle(char_id)
        if not state:
            raise BattleException("不在战斗中")
        if state.state != BattleStateEnum.ONGOING:
            raise BattleException("战斗已结束")
        unit = state.get_player_unit(char_id)
        if not unit or not unit.is_alive:
            raise BattleException("无法操作")
        if not target_id and action in [ActionType.ATTACK, ActionType.SKILL]:
            enemies = state.get_alive_enemies()
            if enemies:
                target_id = enemies[0].unit_id
        cmd = BattleCommand(unit_id=unit.unit_id, action_type=action, target_id=target_id,
                            skill_id=skill_id, item_id=item_id)
        state.commands[unit.unit_id] = cmd
        await BattleService._save_battle(state)
        return {"accepted": True, "action": action.value}

    @staticmethod
    async def resolve_turn(db: AsyncSession, char_id: int) -> dict:
        state = await BattleService.get_battle(char_id)
        if not state:
            raise BattleException("不在战斗中")
        if state.state != BattleStateEnum.ONGOING:
            return {"ended": True, "state": state.state.value}
        all_actions: List[Tuple[BattleUnit, BattleCommand]] = []
        for u in state.player_units:
            if u.is_alive:
                cmd = state.commands.get(u.unit_id)
                if not cmd:
                    enemies = state.get_alive_enemies()
                    cmd = BattleCommand(unit_id=u.unit_id, action_type=ActionType.ATTACK,
                                       target_id=enemies[0].unit_id if enemies else None)
                all_actions.append((u, cmd))
        for u in state.enemy_units:
            if u.is_alive:
                targets = state.get_alive_players()
                target = random.choice(targets) if targets else None
                cmd = BattleCommand(unit_id=u.unit_id, action_type=ActionType.ATTACK,
                                   target_id=target.unit_id if target else None)
                all_actions.append((u, cmd))
        all_actions.sort(key=lambda x: x[0].speed + random.randint(-5, 5), reverse=True)
        action_results: List[ActionResult] = []
        logs = []
        for actor, cmd in all_actions:
            if not actor.is_alive:
                continue
            over = state.is_battle_over()
            if over:
                break
            if cmd.action_type == ActionType.ATTACK:
                target = state.get_unit(cmd.target_id) if cmd.target_id else None
                if not target or not target.is_alive:
                    targets = state.get_alive_enemies() if actor.side == BattleSide.OUR else state.get_alive_players()
                    target = random.choice(targets) if targets else None
                if not target:
                    continue
                result = await BattleService._execute_attack(state, actor, target)
                action_results.append(result)
                logs.append(result.message)
            elif cmd.action_type == ActionType.DEFEND:
                action_results.append(ActionResult(
                    actor_id=actor.unit_id, action_type=ActionType.DEFEND, success=True,
                    message=f"{actor.name}进入防御姿态",
                ))
                logs.append(f"{actor.name}防御！")
            elif cmd.action_type == ActionType.ESCAPE:
                if actor.side == BattleSide.OUR:
                    if random.random() < 0.5:
                        state.state = BattleStateEnum.ESCAPED
                        action_results.append(ActionResult(
                            actor_id=actor.unit_id, action_type=ActionType.ESCAPE, success=True,
                            message=f"{actor.name}逃跑成功！",
                        ))
                        logs.append("逃跑成功！")
                        break
                    else:
                        action_results.append(ActionResult(
                            actor_id=actor.unit_id, action_type=ActionType.ESCAPE, success=False,
                            message=f"{actor.name}逃跑失败！",
                        ))
                        logs.append("逃跑失败！")
        state.turn_actions = action_results
        state.commands = {}
        state.turn += 1
        result_end = state.is_battle_over()
        ended = False
        rewards = {}
        if result_end:
            state.state = result_end
            ended = True
            if result_end == BattleStateEnum.PLAYER_WIN:
                rewards = await BattleService._grant_rewards(db, state)
                logs.append(f"战斗胜利！获得经验{rewards.get('exp',0)}，金币{rewards.get('cash',0)}")
        await BattleService._save_battle(state)
        if ended:
            await BattleService._sync_char_state(db, state)
            for u in state.player_units:
                await BattleService._unbind_char(u.char_id)
            await redis_client.delete(f"{BATTLE_KEY_PREFIX}{state.battle_id}")
        return {
            "ended": ended, "fled": state.state == BattleStateEnum.ESCAPED,
            "state": state.state.value, "logs": logs, "actions": [a.message for a in action_results],
            "exp_gained": rewards.get("exp", 0), "cash_gained": rewards.get("cash", 0),
            "items_gained": rewards.get("items", []),
            "player_units": [u.to_dict() for u in state.player_units],
            "enemy_units": [u.to_dict() for u in state.enemy_units],
        }

    @staticmethod
    async def _execute_attack(state: BattleState, actor: BattleUnit, target: BattleUnit) -> ActionResult:
        hit_chance = calc_hit(actor.hit, 80)
        if random.randint(1, 100) > hit_chance:
            return ActionResult(actor_id=actor.unit_id, action_type=ActionType.ATTACK, success=False,
                               message=f"{actor.name}攻击{target.name}，未命中！")
        is_crit = random.randint(1, 100) <= 10
        dmg = calc_damage(actor.damage, target.defense, 1.0, 0, 1.0)
        if is_crit:
            dmg = int(dmg * 1.5)
        target.hp = max(0, target.hp - dmg)
        crit_msg = "暴击！" if is_crit else ""
        msg = f"{actor.name}攻击{target.name}，{crit_msg}造成{dmg}点伤害！"
        if target.hp <= 0:
            target.is_dead = True
            target.is_alive = False
            msg += f"{target.name}倒下了！"
        return ActionResult(actor_id=actor.unit_id, action_type=ActionType.ATTACK, success=True,
                           message=msg, targets=[{"unit_id": target.unit_id, "damage": dmg, "hp": target.hp}])

    @staticmethod
    async def _grant_rewards(db: AsyncSession, state: BattleState) -> dict:
        total_exp = 0
        total_cash = 0
        items = []
        for u in state.enemy_units:
            total_exp += u.extra.get("exp", 0)
            total_cash += u.extra.get("cash", 0)
            drops = u.extra.get("drops", [])
            for drop in drops:
                if random.randint(1, 10000) <= int(drop.get("chance", 0) * 100):
                    cnt = random.randint(drop.get("min", 1), drop.get("max", 1))
                    items.append({"item_id": drop["item_id"], "count": cnt})
        player = state.player_units[0]
        char_result = await db.execute(select(Character).where(Character.id == player.char_id))
        char = char_result.scalar_one_or_none()
        if char:
            total_exp = max(1, int(total_exp * (1.0 + (len(state.player_units) - 1) * 0.2 / max(1, len([p for p in state.player_units if p.char_type == BattleCharType.PLAYER])))))
            level_result = await character_service.add_exp(db, char, total_exp)
            await character_service.add_cash(char, total_cash)
            for it in items:
                try:
                    await item_service.add_item(db, char, it["item_id"], it["count"])
                except Exception:
                    pass
            await quest_service.on_battle_win(db, char, state.battle_type, state.extra_data)
        return {"exp": total_exp, "cash": total_cash, "items": items}

    @staticmethod
    async def _sync_char_state(db: AsyncSession, state: BattleState):
        for u in state.player_units:
            if u.char_type == BattleCharType.PLAYER:
                result = await db.execute(select(Character).where(Character.id == u.char_id))
                c = result.scalar_one_or_none()
                if c:
                    c.hp = max(1, u.hp)
                    c.mp = max(0, u.mp)
            elif u.char_type == BattleCharType.PET:
                result = await db.execute(select(CharacterPet).where(CharacterPet.id == u.char_id))
                p = result.scalar_one_or_none()
                if p:
                    p.hp = max(0, u.hp)
                    p.mp = max(0, u.mp)


battle_service = BattleService()
