from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional, Tuple
import json

from ..models.item import ItemConfig, CharacterItem
from ..models.character import Character
from ..game.enums import ItemType, EquipSlot, SlotType
from ..game.constants import MAX_BAG_SIZE, MAX_STORAGE_SIZE
from ..utils.id_gen import generate_id
from ..exceptions import ItemException, ValidationException
from ..redis_client import redis_client


class ItemService:
    @staticmethod
    async def get_item_config(db: AsyncSession, item_config_id: int) -> Optional[ItemConfig]:
        result = await db.execute(select(ItemConfig).where(ItemConfig.id == item_config_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_bag_items(db: AsyncSession, char: Character) -> List[CharacterItem]:
        result = await db.execute(
            select(CharacterItem)
            .where(and_(CharacterItem.character_id == char.id, CharacterItem.slot_type == SlotType.BAG))
            .order_by(CharacterItem.slot_index)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_equipped_items(db: AsyncSession, char: Character) -> dict:
        result = await db.execute(
            select(CharacterItem)
            .where(and_(CharacterItem.character_id == char.id, CharacterItem.slot_type == SlotType.EQUIP))
        )
        items = list(result.scalars().all())
        equipped = {}
        for item in items:
            cfg_result = await db.execute(select(ItemConfig).where(ItemConfig.id == item.item_config_id))
            cfg = cfg_result.scalar_one_or_none()
            if cfg:
                equipped[cfg.subtype] = {
                    "instance_id": item.id,
                    "config_id": cfg.id,
                    "name": cfg.name,
                    "type": cfg.type,
                    "slot": cfg.subtype,
                    "effect": cfg.effect,
                    "extra_attr": item.extra_attr,
                }
        return equipped

    @staticmethod
    async def get_item_bonus(db: AsyncSession, char: Character) -> dict:
        bonus = {"hp": 0, "mp": 0, "damage": 0, "defense": 0, "speed": 0,
                 "magic_damage": 0, "magic_defense": 0, "hit": 0}
        result = await db.execute(
            select(CharacterItem, ItemConfig)
            .join(ItemConfig, CharacterItem.item_config_id == ItemConfig.id)
            .where(and_(CharacterItem.character_id == char.id, CharacterItem.slot_type == SlotType.EQUIP))
        )
        for item, cfg in result.all():
            effect = cfg.effect if isinstance(cfg.effect, dict) else {}
            for k in bonus:
                bonus[k] += effect.get(k, 0)
        return bonus

    @staticmethod
    async def add_item(db: AsyncSession, char: Character, item_config_id: int, count: int = 1,
                       bind_type: int = 0, extra_attr: dict = None) -> List[CharacterItem]:
        cfg = await ItemService.get_item_config(db, item_config_id)
        if not cfg:
            raise ItemException("物品不存在")
        extra_attr = extra_attr or {}
        added = []
        if cfg.stackable:
            existing = await db.execute(
                select(CharacterItem).where(
                    and_(
                        CharacterItem.character_id == char.id,
                        CharacterItem.item_config_id == item_config_id,
                        CharacterItem.slot_type == SlotType.BAG,
                        CharacterItem.quantity < cfg.max_stack,
                    )
                )
            )
            for stack in existing.scalars().all():
                can_add = min(count, cfg.max_stack - stack.quantity)
                if can_add > 0:
                    stack.quantity += can_add
                    count -= can_add
                    added.append(stack)
                    if count <= 0:
                        return added
        while count > 0:
            slot_idx = await ItemService._find_empty_slot(db, char, SlotType.BAG)
            if slot_idx is None:
                raise ItemException("背包已满")
            add_count = min(count, cfg.max_stack)
            item = CharacterItem(
                id=generate_id(),
                character_id=char.id,
                item_config_id=item_config_id,
                slot_type=SlotType.BAG,
                slot_index=slot_idx,
                quantity=add_count,
                bind_type=bind_type,
                extra_attr=extra_attr,
            )
            db.add(item)
            added.append(item)
            count -= add_count
        return added

    @staticmethod
    async def _find_empty_slot(db: AsyncSession, char: Character, slot_type: SlotType, max_size: int = 0) -> Optional[int]:
        if slot_type == SlotType.BAG:
            max_size = MAX_BAG_SIZE
        elif slot_type == SlotType.STORAGE:
            max_size = MAX_STORAGE_SIZE
        result = await db.execute(
            select(CharacterItem.slot_index)
            .where(and_(CharacterItem.character_id == char.id, CharacterItem.slot_type == slot_type))
        )
        used = set(r[0] for r in result.all())
        for i in range(max_size):
            if i not in used:
                return i
        return None

    @staticmethod
    async def remove_item(db: AsyncSession, char: Character, item_config_id: int, count: int = 1) -> bool:
        remaining = count
        result = await db.execute(
            select(CharacterItem).where(
                and_(
                    CharacterItem.character_id == char.id,
                    CharacterItem.item_config_id == item_config_id,
                    CharacterItem.slot_type.in_([SlotType.BAG, SlotType.EQUIP]),
                )
            ).order_by(CharacterItem.slot_type, CharacterItem.slot_index)
        )
        items = list(result.scalars().all())
        total = sum(i.quantity for i in items)
        if total < count:
            return False
        for item in items:
            if remaining <= 0:
                break
            take = min(item.quantity, remaining)
            item.quantity -= take
            remaining -= take
            if item.quantity <= 0:
                await db.delete(item)
        return True

    @staticmethod
    async def remove_item_by_instance(db: AsyncSession, char: Character, char_item_id: int, count: int = 1) -> bool:
        result = await db.execute(
            select(CharacterItem).where(
                and_(
                    CharacterItem.id == char_item_id,
                    CharacterItem.character_id == char.id,
                )
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            return False
        if item.quantity < count:
            return False
        item.quantity -= count
        if item.quantity <= 0:
            await db.delete(item)
        return True

    @staticmethod
    async def use_item(db: AsyncSession, char: Character, char_item_id: int, target_id: Optional[int] = None) -> dict:
        result = await db.execute(
            select(CharacterItem, ItemConfig)
            .join(ItemConfig, CharacterItem.item_config_id == ItemConfig.id)
            .where(and_(CharacterItem.id == char_item_id, CharacterItem.character_id == char.id))
        )
        row = result.first()
        if not row:
            raise ItemException("物品不存在")
        item, cfg = row
        effect = cfg.effect if isinstance(cfg.effect, dict) else {}
        message = ""
        if cfg.type == ItemType.MEDICINE:
            hp_heal = effect.get("hp", 0)
            mp_heal = effect.get("mp", 0)
            combat_bonus = await ItemService.get_item_bonus(db, char)
            hp_max = char.hp
            from .character_service import character_service
            stats = character_service.get_combat_stats(char)
            hp_max = stats["hp_max"] + combat_bonus.get("hp", 0)
            mp_max = stats["mp_max"] + combat_bonus.get("mp", 0)
            if hp_heal > 0:
                old_hp = char.hp
                char.hp = min(hp_max, char.hp + hp_heal)
                message += f"恢复了{char.hp - old_hp}点气血！"
            if mp_heal > 0:
                old_mp = char.mp
                char.mp = min(mp_max, char.mp + mp_heal)
                message += f"恢复了{char.mp - old_mp}点魔法！"
            await ItemService.remove_item_by_instance(db, char, char_item_id, 1)
            return {"success": True, "message": message, "hp": char.hp, "mp": char.mp}
        elif cfg.type == ItemType.EQUIPMENT:
            return await ItemService.equip_item(db, char, item)
        else:
            raise ItemException("该物品无法直接使用")

    @staticmethod
    async def equip_item(db: AsyncSession, char: Character, item: CharacterItem) -> dict:
        cfg_result = await db.execute(select(ItemConfig).where(ItemConfig.id == item.item_config_id))
        cfg = cfg_result.scalar_one_or_none()
        if not cfg or cfg.type != ItemType.EQUIPMENT:
            raise ItemException("不是装备")
        slot = cfg.subtype
        if slot not in [s.value for s in EquipSlot]:
            raise ItemException("装备位置无效")
        old_result = await db.execute(
            select(CharacterItem).where(
                and_(
                    CharacterItem.character_id == char.id,
                    CharacterItem.slot_type == SlotType.EQUIP,
                    CharacterItem.slot_index == slot,
                )
            )
        )
        old_item = old_result.scalar_one_or_none()
        bag_slot = item.slot_index
        item.slot_type = SlotType.EQUIP
        item.slot_index = slot
        if old_item:
            empty = await ItemService._find_empty_slot(db, char, SlotType.BAG)
            if empty is None:
                raise ItemException("背包空间不足")
            old_item.slot_type = SlotType.BAG
            old_item.slot_index = empty
        else:
            pass
        return {"success": True, "message": f"装备了{cfg.name}"}

    @staticmethod
    async def unequip_item(db: AsyncSession, char: Character, slot: int) -> dict:
        result = await db.execute(
            select(CharacterItem).where(
                and_(
                    CharacterItem.character_id == char.id,
                    CharacterItem.slot_type == SlotType.EQUIP,
                    CharacterItem.slot_index == slot,
                )
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise ItemException("该位置没有装备")
        empty = await ItemService._find_empty_slot(db, char, SlotType.BAG)
        if empty is None:
            raise ItemException("背包空间不足")
        item.slot_type = SlotType.BAG
        item.slot_index = empty
        cfg_result = await db.execute(select(ItemConfig).where(ItemConfig.id == item.item_config_id))
        cfg = cfg_result.scalar_one_or_none()
        return {"success": True, "message": f"卸下了{cfg.name if cfg else '装备'}"}

    @staticmethod
    async def get_char_item(db: AsyncSession, char_item_id: int, char: Character) -> Optional[Tuple[CharacterItem, ItemConfig]]:
        result = await db.execute(
            select(CharacterItem, ItemConfig)
            .join(ItemConfig, CharacterItem.item_config_id == ItemConfig.id)
            .where(and_(CharacterItem.id == char_item_id, CharacterItem.character_id == char.id))
        )
        return result.first()

    @staticmethod
    async def count_item(db: AsyncSession, char: Character, item_config_id: int) -> int:
        result = await db.execute(
            select(CharacterItem).where(
                and_(
                    CharacterItem.character_id == char.id,
                    CharacterItem.item_config_id == item_config_id,
                    CharacterItem.slot_type.in_([SlotType.BAG]),
                )
            )
        )
        return sum(i.quantity for i in result.scalars().all())


item_service = ItemService()
