from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List

from ..models.character import Character, CharacterStats
from ..models.user import User
from ..models.pet import PetConfig, CharacterPet
from ..models.item import ItemConfig, CharacterItem
from ..models.map import MapConfig
from ..game.enums import Faction, Gender, Race, SlotType, EquipSlot
from ..game.constants import FACTION_NAMES, FACTION_RACE, MAX_BAG_SIZE
from ..game.formulas import calc_character_combat_stats, calc_level_from_exp, calc_exp_for_level, get_pot_points_for_level
from ..utils.id_gen import generate_id
from ..exceptions import ValidationException, NotFoundException
import random


class CharacterService:
    @staticmethod
    async def create_character(
        db: AsyncSession,
        user: User,
        name: str,
        gender: int,
        faction: int,
    ) -> Character:
        if len(name) < 2 or len(name) > 12:
            raise ValidationException("角色名长度2-12字")
        if gender not in [Gender.MALE, Gender.FEMALE]:
            raise ValidationException("性别无效")
        if faction not in FACTION_RACE:
            raise ValidationException("门派无效")

        count_result = await db.execute(select(Character).where(Character.user_id == user.id))
        existing_chars = count_result.scalars().all()
        if len(existing_chars) >= 3:
            raise ValidationException("一个账号最多创建3个角色")

        name_check = await db.execute(select(Character).where(Character.name == name))
        if name_check.scalar_one_or_none():
            raise ValidationException("角色名已存在")

        race = FACTION_RACE[Faction(faction)]

        base_stats = {
            1: {"base_hp": 120, "base_mp": 60, "base_hit": 25, "base_damage": 35, "base_defense": 25,
                 "base_speed": 12, "base_magic_damage": 12, "base_magic_defense": 15},
            2: {"base_hp": 100, "base_mp": 100, "base_hit": 20, "base_damage": 25, "base_defense": 20,
                 "base_speed": 12, "base_magic_damage": 25, "base_magic_defense": 20},
            3: {"base_hp": 150, "base_mp": 40, "base_hit": 22, "base_damage": 40, "base_defense": 20,
                 "base_speed": 10, "base_magic_damage": 10, "base_magic_defense": 12},
        }
        stats = base_stats[race]

        char = Character(
            id=generate_id(),
            user_id=user.id,
            name=name,
            gender=gender,
            race=race,
            faction=faction,
            level=1,
            exp=0,
            map_id=1,
            pos_x=20,
            pos_y=30,
            cash=1000,
            reserve_cash=500,
            hp=stats["base_hp"],
            mp=stats["base_mp"],
            anger=0,
        )
        db.add(char)
        await db.flush()

        char_stats = CharacterStats(
            character_id=char.id,
            pot_points=0,
            **stats,
        )
        db.add(char_stats)

        starter_items = [
            {"item_config_id": 10, "slot_type": SlotType.EQUIP, "slot_index": EquipSlot.WEAPON},
            {"item_config_id": 11, "slot_type": SlotType.EQUIP, "slot_index": EquipSlot.ARMOR},
            {"item_config_id": 12, "slot_type": SlotType.EQUIP, "slot_index": EquipSlot.HELMET},
            {"item_config_id": 1, "slot_type": SlotType.BAG, "slot_index": 0, "quantity": 10},
            {"item_config_id": 2, "slot_type": SlotType.BAG, "slot_index": 1, "quantity": 5},
        ]
        for idx, item_data in enumerate(starter_items):
            slot_idx = item_data.get("slot_index", idx)
            if item_data["slot_type"] == SlotType.BAG:
                slot_idx = idx
            db.add(CharacterItem(
                id=generate_id(),
                character_id=char.id,
                item_config_id=item_data["item_config_id"],
                slot_type=item_data["slot_type"],
                slot_index=slot_idx,
                quantity=item_data.get("quantity", 1),
            ))

        pet_result = await db.execute(select(PetConfig).where(PetConfig.id == 1))
        pet_cfg = pet_result.scalar_one_or_none()
        if pet_cfg:
            db.add(CharacterPet(
                id=generate_id(),
                character_id=char.id,
                pet_config_id=pet_cfg.id,
                nickname=pet_cfg.name,
                level=1,
                exp=0,
                hp=pet_cfg.base_hp // 10,
                mp=pet_cfg.base_mp // 10,
                loyalty=100,
                life=10000,
                is_battle=True,
                slot_index=0,
                skills=[],
                attr_gz=pet_cfg.base_attack,
                attr_fy=pet_cfg.base_defense,
                attr_tz=pet_cfg.base_hp,
                attr_fz=pet_cfg.base_magic,
                attr_sd=pet_cfg.base_speed,
                growth=pet_cfg.growth_rate,
            ))

        return char

    @staticmethod
    async def get_user_characters(db: AsyncSession, user: User) -> List[Character]:
        result = await db.execute(
            select(Character)
            .where(Character.user_id == user.id)
            .options(selectinload(Character.stats))
        )
        return list(result.scalars().all())

    @staticmethod
    async def select_character(db: AsyncSession, user: User, char_id: int) -> Character:
        result = await db.execute(
            select(Character)
            .options(selectinload(Character.stats))
            .where(and_(Character.id == char_id, Character.user_id == user.id))
        )
        char = result.scalar_one_or_none()
        if not char:
            raise NotFoundException("角色不存在")
        await db.execute(
            __import__("sqlalchemy").update(Character)
            .where(Character.user_id == user.id)
            .values(is_online=False)
        )
        char.is_online = True
        char.in_battle_id = None
        return char

    @staticmethod
    async def get_character_info(db: AsyncSession, char: Character) -> dict:
        combat = CharacterService.get_combat_stats(char)
        map_result = await db.execute(select(MapConfig).where(MapConfig.id == char.map_id))
        map_cfg = map_result.scalar_one_or_none()
        return {
            "id": char.id,
            "name": char.name,
            "gender": char.gender,
            "race": char.race,
            "faction": char.faction,
            "faction_name": FACTION_NAMES.get(Faction(char.faction), ""),
            "level": char.level,
            "exp": char.exp,
            "exp_for_next": calc_exp_for_level(char.level + 1),
            "map_id": char.map_id,
            "map_name": map_cfg.name if map_cfg else "",
            "pos_x": char.pos_x,
            "pos_y": char.pos_y,
            "hp": char.hp,
            "mp": char.mp,
            "hp_max": combat["hp_max"],
            "mp_max": combat["mp_max"],
            "anger": char.anger,
            "cash": char.cash,
            "reserve_cash": char.reserve_cash,
            "jade": char.jade,
            "team_id": char.team_id,
            "guild_id": char.guild_id,
            "pot_points": char.stats.pot_points if char.stats else 0,
            "combat": combat,
            "practice": {
                "phys": char.stats.practice_phys if char.stats else 0,
                "def": char.stats.practice_def if char.stats else 0,
                "mdef": char.stats.practice_mdef if char.stats else 0,
                "capture": char.stats.practice_capture if char.stats else 0,
            },
        }

    @staticmethod
    def get_combat_stats(char: Character) -> dict:
        if not char.stats:
            return {
                "hp_max": char.hp, "mp_max": char.mp, "hit": 20, "damage": 30,
                "defense": 20, "speed": 10, "magic_damage": 15, "magic_defense": 15
            }
        return calc_character_combat_stats(
            race=char.race,
            level=char.level,
            base_hp=char.stats.base_hp,
            base_mp=char.stats.base_mp,
            base_hit=char.stats.base_hit,
            base_damage=char.stats.base_damage,
            base_defense=char.stats.base_defense,
            base_speed=char.stats.base_speed,
            base_magic_damage=char.stats.base_magic_damage,
            base_magic_defense=char.stats.base_magic_defense,
            pot_tizhi=char.stats.pot_tizhi,
            pot_moli=char.stats.pot_moli,
            pot_liliang=char.stats.pot_liliang,
            pot_naili=char.stats.pot_naili,
            pot_minjie=char.stats.pot_minjie,
        )

    @staticmethod
    async def add_exp(db: AsyncSession, char: Character, exp_amount: int) -> dict:
        char.exp += exp_amount
        leveled_up = False
        new_pot = 0
        old_level = char.level
        while True:
            next_exp = calc_exp_for_level(char.level + 1)
            if char.exp >= next_exp and char.level < 175:
                char.level += 1
                pot = get_pot_points_for_level(char.level)
                char.stats.pot_points += pot
                new_pot += pot
                leveled_up = True
            else:
                break
        if leveled_up:
            combat = CharacterService.get_combat_stats(char)
            char.hp = combat["hp_max"]
            char.mp = combat["mp_max"]
        return {
            "exp_gained": exp_amount,
            "old_level": old_level,
            "new_level": char.level,
            "leveled_up": leveled_up,
            "new_pot_points": new_pot,
        }

    @staticmethod
    async def add_pot(db: AsyncSession, char: Character, attr: str, points: int = 1):
        if char.stats.pot_points < points:
            raise ValidationException("潜力点不足")
        attr_map = {
            "tizhi": "pot_tizhi",
            "moli": "pot_moli",
            "liliang": "pot_liliang",
            "naili": "pot_naili",
            "minjie": "pot_minjie",
        }
        if attr not in attr_map:
            raise ValidationException("属性无效")
        setattr(char.stats, attr_map[attr], getattr(char.stats, attr_map[attr]) + points)
        char.stats.pot_points -= points
        combat = CharacterService.get_combat_stats(char)
        if char.hp > combat["hp_max"]:
            char.hp = combat["hp_max"]
        if char.mp > combat["mp_max"]:
            char.mp = combat["mp_max"]

    @staticmethod
    async def add_cash(char: Character, amount: int, is_reserve: bool = False):
        if is_reserve:
            char.reserve_cash += amount
        else:
            char.cash += amount
            if char.cash < 0:
                char.cash = 0
        if char.reserve_cash < 0:
            char.reserve_cash = 0

    @staticmethod
    async def spend_cash(char: Character, amount: int, prefer_reserve: bool = True) -> bool:
        if prefer_reserve:
            from_reserve = min(char.reserve_cash, amount)
            char.reserve_cash -= from_reserve
            remaining = amount - from_reserve
            if remaining > 0:
                if char.cash < remaining:
                    char.reserve_cash += from_reserve
                    return False
                char.cash -= remaining
        else:
            if char.cash < amount:
                return False
            char.cash -= amount
        return True

    @staticmethod
    async def update_position(char: Character, map_id: int, x: int, y: int):
        char.map_id = map_id
        char.pos_x = x
        char.pos_y = y

    @staticmethod
    async def heal_full(char: Character):
        combat = CharacterService.get_combat_stats(char)
        char.hp = combat["hp_max"]
        char.mp = combat["mp_max"]
        char.anger = 0


character_service = CharacterService()
