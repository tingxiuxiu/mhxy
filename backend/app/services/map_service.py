from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Tuple, Optional
import random

from ..models.map import MapConfig, NpcConfig
from ..models.monster import MonsterConfig
from ..models.character import Character
from ..game.enums import MapType
from ..exceptions import MapException, ValidationException
from ..config import settings
from ..redis_client import redis_client


class MapService:
    @staticmethod
    async def get_all_maps(db: AsyncSession) -> List[MapConfig]:
        result = await db.execute(select(MapConfig).where(MapConfig.is_active == True))
        return list(result.scalars().all())

    @staticmethod
    async def get_map(db: AsyncSession, map_id: int) -> Optional[MapConfig]:
        result = await db.execute(select(MapConfig).where(and_(MapConfig.id == map_id, MapConfig.is_active == True)))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_current_map_info(db: AsyncSession, char: Character) -> dict:
        map_cfg = await MapService.get_map(db, char.map_id)
        if not map_cfg:
            raise MapException("地图不存在")
        npcs_result = await db.execute(
            select(NpcConfig).where(and_(NpcConfig.map_id == map_cfg.id, NpcConfig.is_active == True))
        )
        npcs = list(npcs_result.scalars().all())
        return {
            "map_id": map_cfg.id,
            "name": map_cfg.name,
            "type": map_cfg.type,
            "width": map_cfg.width,
            "height": map_cfg.height,
            "pos_x": char.pos_x,
            "pos_y": char.pos_y,
            "is_dark": map_cfg.is_dark,
            "npcs": [{"id": n.id, "name": n.name, "title": n.title, "x": n.pos_x, "y": n.pos_y, "type": n.npc_type}
                     for n in npcs],
            "adjacent_maps": map_cfg.adjacent_maps,
        }

    @staticmethod
    async def get_map_npcs(db: AsyncSession, map_id: int) -> List[NpcConfig]:
        result = await db.execute(
            select(NpcConfig).where(and_(NpcConfig.map_id == map_id, NpcConfig.is_active == True))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_npc(db: AsyncSession, npc_id: int) -> Optional[NpcConfig]:
        result = await db.execute(select(NpcConfig).where(and_(NpcConfig.id == npc_id, NpcConfig.is_active == True)))
        return result.scalar_one_or_none()

    @staticmethod
    async def move_to_map(db: AsyncSession, char: Character, target_map_id: int) -> Tuple[MapConfig, int, int]:
        current_map = await MapService.get_map(db, char.map_id)
        target_map = await MapService.get_map(db, target_map_id)
        if not target_map:
            raise MapException("目标地图不存在")
        if not current_map:
            raise MapException("当前地图异常")
        can_move = False
        entry_x, entry_y = 10, 10
        for adj in current_map.adjacent_maps:
            if adj.get("map_id") == target_map_id:
                can_move = True
                break
        if not can_move:
            reverse_adj = any(adj.get("map_id") == char.map_id for adj in target_map.adjacent_maps)
            if not reverse_adj:
                raise MapException("不能直接前往该地图")
        for adj in target_map.adjacent_maps:
            if adj.get("map_id") == current_map.id:
                entry_x = adj.get("entry_x", 10)
                entry_y = adj.get("entry_y", 10)
                break
        return target_map, entry_x, entry_y

    @staticmethod
    async def move_coord(char: Character, direction: str, map_cfg: MapConfig):
        dx, dy = 0, 0
        if direction in ["东", "e", "right"]:
            dx = 1
        elif direction in ["西", "w", "left"]:
            dx = -1
        elif direction in ["南", "s", "down"]:
            dy = 1
        elif direction in ["北", "n", "up"]:
            dy = -1
        else:
            try:
                parts = direction.split()
                if len(parts) == 2:
                    dx = int(parts[0])
                    dy = int(parts[1])
            except Exception:
                raise ValidationException("移动方向无效")
        new_x = char.pos_x + dx
        new_y = char.pos_y + dy
        if new_x < 0 or new_x >= map_cfg.width or new_y < 0 or new_y >= map_cfg.height:
            raise MapException("已到达地图边界")
        char.pos_x = new_x
        char.pos_y = new_y

    @staticmethod
    async def check_encounter(db: AsyncSession, map_cfg: MapConfig) -> Optional[List[Tuple[MonsterConfig, int]]]:
        if not map_cfg.is_dark or map_cfg.encounter_rate <= 0:
            return None
        if random.randint(1, 1000) > map_cfg.encounter_rate:
            return None
        encounters = map_cfg.encounters
        if not encounters:
            return None
        total_weight = sum(e["weight"] for e in encounters)
        r = random.randint(1, total_weight)
        current = 0
        selected_monster_id = encounters[0]["monster_id"]
        for e in encounters:
            current += e["weight"]
            if r <= current:
                selected_monster_id = e["monster_id"]
                break
        result = await db.execute(select(MonsterConfig).where(MonsterConfig.id == selected_monster_id))
        monster_cfg = result.scalar_one_or_none()
        if not monster_cfg:
            return None
        monster_count = random.randint(1, 3)
        monsters = []
        for _ in range(monster_count):
            level_var = random.randint(-2, 2)
            monsters.append((monster_cfg, max(1, monster_cfg.level + level_var)))
        return monsters

    @staticmethod
    async def teleport(char: Character, map_id: int, x: int, y: int, map_cfg: Optional[MapConfig] = None):
        char.map_id = map_id
        char.pos_x = x
        char.pos_y = y


map_service = MapService()
