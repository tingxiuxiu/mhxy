import json
import os
from sqlalchemy import select
from ..enums import MapType, NpcType, ItemType, EquipSlot, SkillType, Faction
from ...models.map import MapConfig, NpcConfig
from ...models.item import ItemConfig
from ...models.skill import SkillConfig
from ...models.pet import PetConfig
from ...models.monster import MonsterConfig
from ...models.quest import QuestConfig
from ...database import AsyncSessionLocal


INITIAL_DATA_DIR = os.path.dirname(os.path.abspath(__file__))


async def load_or_create(session, model, defaults: dict, **filters):
    result = await session.execute(select(model).filter_by(**filters))
    obj = result.scalar_one_or_none()
    if obj is None:
        obj = model(**defaults, **filters)
        session.add(obj)
        return obj
    return obj


async def init_maps(session):
    maps = [
        {"id": 1, "name": "建邺城", "type": MapType.CITY, "width": 80, "height": 60,
         "adjacent_maps": [{"map_id": 2, "entry_x": 5, "entry_y": 30}],
         "is_dark": False, "encounter_rate": 0, "encounters": []},
        {"id": 2, "name": "东海湾", "type": MapType.FIELD, "width": 100, "height": 80,
         "adjacent_maps": [{"map_id": 1, "entry_x": 75, "entry_y": 30}, {"map_id": 3, "entry_x": 50, "entry_y": 5}],
         "is_dark": True, "encounter_rate": 300,
         "encounters": [{"monster_id": 1, "weight": 50}, {"monster_id": 2, "weight": 30}, {"monster_id": 3, "weight": 20}]},
        {"id": 3, "name": "长安城", "type": MapType.CITY, "width": 120, "height": 100,
         "adjacent_maps": [{"map_id": 2, "entry_x": 50, "entry_y": 95},
                          {"map_id": 4, "entry_x": 5, "entry_y": 50},
                          {"map_id": 6, "entry_x": 115, "entry_y": 50}],
         "is_dark": False, "encounter_rate": 0, "encounters": []},
        {"id": 4, "name": "大唐国境", "type": MapType.FIELD, "width": 100, "height": 80,
         "adjacent_maps": [{"map_id": 3, "entry_x": 95, "entry_y": 50}, {"map_id": 5, "entry_x": 50, "entry_y": 5}],
         "is_dark": True, "encounter_rate": 200,
         "encounters": [{"monster_id": 4, "weight": 40}, {"monster_id": 5, "weight": 35}, {"monster_id": 6, "weight": 25}]},
        {"id": 5, "name": "大唐官府", "type": MapType.FACTION, "width": 60, "height": 60,
         "adjacent_maps": [{"map_id": 4, "entry_x": 30, "entry_y": 55}],
         "is_dark": False, "encounter_rate": 0, "encounters": []},
        {"id": 6, "name": "傲来国", "type": MapType.CITY, "width": 80, "height": 70,
         "adjacent_maps": [{"map_id": 3, "entry_x": 5, "entry_y": 50}],
         "is_dark": False, "encounter_rate": 0, "encounters": []},
        {"id": 100, "name": "建邺城副本", "type": MapType.DUNGEON, "width": 50, "height": 50,
         "adjacent_maps": [], "is_dark": False, "encounter_rate": 0, "encounters": []},
    ]
    for m in maps:
        await load_or_create(session, MapConfig, m, id=m["id"])


async def init_npcs(session):
    npcs = [
        {"id": 1, "name": "宠物仙子", "title": "宠物领取", "map_id": 1, "pos_x": 20, "pos_y": 20,
         "npc_type": NpcType.FUNCTION, "dialog": "欢迎来到建邺城！需要领养一只宠物吗？",
         "functions": ["get_pet"]},
        {"id": 2, "name": "建邺守卫", "title": "城门守卫", "map_id": 1, "pos_x": 75, "pos_y": 30,
         "npc_type": NpcType.TELEPORT, "dialog": "去东海湾吗？", "teleport_to": {"map_id": 2, "x": 5, "y": 30}},
        {"id": 3, "name": "药店老板", "title": "回春堂", "map_id": 1, "pos_x": 40, "pos_y": 25,
         "npc_type": NpcType.SHOP, "dialog": "客官，需要点什么药？",
         "shop_items": [{"item_id": 1, "price": 100}, {"item_id": 2, "price": 150}]},
        {"id": 4, "name": "武器店老板", "title": "神兵阁", "map_id": 1, "pos_x": 50, "pos_y": 35,
         "npc_type": NpcType.SHOP, "dialog": "打造神兵利器，尽在此处！",
         "shop_items": [{"item_id": 10, "price": 500}, {"item_id": 11, "price": 500}]},
        {"id": 10, "name": "程咬金", "title": "大唐国师", "map_id": 5, "pos_x": 30, "pos_y": 20,
         "npc_type": NpcType.QUEST, "dialog": "我大唐官府，惩恶扬善！想学本领吗？",
         "functions": ["learn_skill"], "quest_ids": [201]},
        {"id": 20, "name": "钟馗", "title": "捉鬼天师", "map_id": 3, "pos_x": 50, "pos_y": 40,
         "npc_type": NpcType.QUEST, "dialog": "阴间小鬼作祟，大侠可愿前往捉鬼？",
         "quest_ids": [202]},
        {"id": 21, "name": "郑镖头", "title": "长风镖局", "map_id": 3, "pos_x": 60, "pos_y": 60,
         "npc_type": NpcType.QUEST, "dialog": "保镖护院，义不容辞！",
         "quest_ids": [203]},
        {"id": 22, "name": "门派接送人", "title": "各门派传送", "map_id": 3, "pos_x": 30, "pos_y": 30,
         "npc_type": NpcType.TELEPORT, "dialog": "请问要去哪个门派？",
         "teleport_to": {"map_id": 5, "x": 30, "y": 30}},
    ]
    for n in npcs:
        await load_or_create(session, NpcConfig, n, id=n["id"])


async def init_items(session):
    items = [
        {"id": 1, "name": "四叶花", "type": ItemType.MEDICINE, "subtype": 0, "stackable": True, "max_stack": 99,
         "sell_price": 20, "buy_price": 100, "effect": {"hp": 100}, "description": "恢复100点气血"},
        {"id": 2, "name": "七叶莲", "type": ItemType.MEDICINE, "subtype": 0, "stackable": True, "max_stack": 99,
         "sell_price": 30, "buy_price": 150, "effect": {"mp": 80}, "description": "恢复80点魔法"},
        {"id": 3, "name": "金疮药", "type": ItemType.MEDICINE, "subtype": 0, "stackable": True, "max_stack": 30,
         "sell_price": 80, "buy_price": 400, "effect": {"hp": 400}, "description": "恢复400点气血"},
        {"id": 10, "name": "青铜短剑", "type": ItemType.EQUIPMENT, "subtype": EquipSlot.WEAPON,
         "level_req": 0, "stackable": False, "max_stack": 1, "sell_price": 100, "buy_price": 500,
         "effect": {"damage": 20}, "description": "新手武器"},
        {"id": 11, "name": "布衣", "type": ItemType.EQUIPMENT, "subtype": EquipSlot.ARMOR,
         "level_req": 0, "stackable": False, "max_stack": 1, "sell_price": 80, "buy_price": 400,
         "effect": {"defense": 10}, "description": "新手衣服"},
        {"id": 12, "name": "布帽", "type": ItemType.EQUIPMENT, "subtype": EquipSlot.HELMET,
         "level_req": 0, "stackable": False, "max_stack": 1, "sell_price": 50, "buy_price": 250,
         "effect": {"defense": 5}, "description": "新手帽子"},
        {"id": 20, "name": "飞行符", "type": ItemType.MISC, "subtype": 0, "stackable": True, "max_stack": 99,
         "sell_price": 10, "buy_price": 50, "effect": {"teleport": True}, "description": "瞬间回到长安城"},
        {"id": 30, "name": "魔兽要诀", "type": ItemType.MISC, "subtype": 0, "stackable": False, "max_stack": 1,
         "sell_price": 10000, "buy_price": 0, "effect": {"pet_skill": True}, "description": "记载宠物技能的要诀"},
    ]
    for i in items:
        await load_or_create(session, ItemConfig, i, id=i["id"])


async def init_skills(session):
    skills = [
        {"id": 101, "name": "横扫千军", "type": 1, "faction": Faction.DT, "mp_cost": 30,
         "target_type": 1, "target_count": 1, "effect_type": 1,
         "effect_value": {"multiplier": [0.8, 1.0, 1.2], "hits": 3}, "level_req": 10,
         "description": "连续攻击目标3次，使用后休息一回合"},
        {"id": 102, "name": "后发制人", "type": 1, "faction": Faction.DT, "mp_cost": 20,
         "target_type": 1, "target_count": 1, "effect_type": 1,
         "effect_value": {"multiplier": 1.5, "delay": 1}, "level_req": 5,
         "description": "本回合防御，下回合自动攻击，伤害提升50%"},
        {"id": 201, "name": "龙卷雨击", "type": 1, "faction": Faction.LG, "mp_cost": 20,
         "target_type": 6, "target_count": 3, "effect_type": 2,
         "effect_value": {"multiplier": 0.8}, "level_req": 10,
         "description": "水系法术攻击多个目标"},
        {"id": 301, "name": "狮搏", "type": 1, "faction": Faction.STL, "mp_cost": 20,
         "target_type": 1, "target_count": 1, "effect_type": 1,
         "effect_value": {"multiplier": 1.5, "ignore_defense": 0.2}, "level_req": 10,
         "description": "提高暴击几率攻击目标"},
        {"id": 1, "name": "普通攻击", "type": 1, "faction": 0, "mp_cost": 0,
         "target_type": 1, "target_count": 1, "effect_type": 1,
         "effect_value": {"multiplier": 1.0}, "level_req": 1,
         "description": "普通物理攻击"},
    ]
    for s in skills:
        await load_or_create(session, SkillConfig, s, id=s["id"])


async def init_monsters(session):
    monsters = [
        {"id": 1, "name": "大海龟", "level": 2, "hp": 80, "mp": 30, "damage": 15, "defense": 20,
         "speed": 5, "magic_damage": 8, "magic_defense": 15, "skills": [],
         "exp_reward": 30, "cash_reward": 20,
         "drop_items": [{"item_id": 1, "rate": 10, "min_count": 1, "max_count": 2}]},
        {"id": 2, "name": "巨蛙", "level": 3, "hp": 70, "mp": 50, "damage": 18, "defense": 10,
         "speed": 8, "magic_damage": 15, "magic_defense": 10, "skills": [],
         "exp_reward": 40, "cash_reward": 25,
         "drop_items": [{"item_id": 2, "rate": 8, "min_count": 1, "max_count": 1}]},
        {"id": 3, "name": "海毛虫", "level": 5, "hp": 100, "mp": 20, "damage": 25, "defense": 8,
         "speed": 12, "magic_damage": 5, "magic_defense": 8, "skills": [],
         "exp_reward": 60, "cash_reward": 35,
         "drop_items": [{"item_id": 1, "rate": 15, "min_count": 1, "max_count": 2}]},
        {"id": 4, "name": "野猪", "level": 8, "hp": 180, "mp": 30, "damage": 35, "defense": 20,
         "speed": 10, "magic_damage": 10, "magic_defense": 15, "skills": [],
         "exp_reward": 100, "cash_reward": 60,
         "drop_items": []},
        {"id": 5, "name": "树怪", "level": 9, "hp": 200, "mp": 40, "damage": 30, "defense": 35,
         "speed": 6, "magic_damage": 15, "magic_defense": 25, "skills": [],
         "exp_reward": 120, "cash_reward": 70,
         "drop_items": []},
        {"id": 100, "name": "妖风", "level": 10, "hp": 800, "mp": 200, "damage": 50, "defense": 30,
         "speed": 15, "magic_damage": 40, "magic_defense": 30, "skills": [101],
         "exp_reward": 2000, "cash_reward": 1000, "is_boss": True,
         "drop_items": [{"item_id": 3, "rate": 50, "min_count": 2, "max_count": 5}]},
    ]
    for m in monsters:
        await load_or_create(session, MonsterConfig, m, id=m["id"])


async def init_pets(session):
    pets = [
        {"id": 1, "name": "大海龟", "level_req": 0,
         "base_hp": 1200, "base_mp": 600, "base_attack": 800, "base_defense": 1200,
         "base_speed": 500, "base_magic": 600, "growth_rate": 0.9,
         "possible_skills": ["防御", "反震"], "capture_rate": 70},
        {"id": 2, "name": "海毛虫", "level_req": 5,
         "base_hp": 800, "base_mp": 400, "base_attack": 1400, "base_defense": 600,
         "base_speed": 1200, "base_magic": 400, "growth_rate": 1.0,
         "possible_skills": ["必杀", "夜战"], "capture_rate": 40},
    ]
    for p in pets:
        await load_or_create(session, PetConfig, p, id=p["id"])


async def init_quests(session):
    quests = [
        {"id": 1, "name": "新手引导", "type": 1, "level_min": 1, "level_max": 10,
         "repeatable": False, "daily_limit": 0, "giver_npc_id": 1,
         "steps": [{"type": "talk", "npc_id": 1}, {"type": "talk", "npc_id": 3}],
         "rewards": {"exp": 500, "cash": 500, "items": [{"item_id": 10, "count": 1}, {"item_id": 11, "count": 1}]},
         "description": "熟悉建邺城，与NPC对话"},
        {"id": 201, "name": "师门任务", "type": 2, "level_min": 10, "level_max": 175,
         "repeatable": True, "daily_limit": 20, "giver_npc_id": 10,
         "steps": [], "rewards": {"exp_base": 5000, "cash_base": 3000},
         "description": "完成师门交代的任务"},
        {"id": 202, "name": "抓鬼任务", "type": 3, "level_min": 20, "level_max": 175,
         "repeatable": True, "daily_limit": 50, "giver_npc_id": 20,
         "steps": [], "rewards": {"exp_base": 10000, "cash_base": 5000},
         "description": "捉拿作乱的鬼怪"},
        {"id": 203, "name": "护镖任务", "type": 4, "level_min": 30, "level_max": 175,
         "repeatable": True, "daily_limit": 50, "giver_npc_id": 21,
         "steps": [], "rewards": {"cash_base": 20000},
         "description": "押送镖银到目的地"},
        {"id": 301, "name": "建邺城除妖", "type": 6, "level_min": 10, "level_max": 175,
         "repeatable": True, "daily_limit": 1, "giver_npc_id": 1,
         "steps": [{"type": "dungeon_fight", "fights": 4, "boss_id": 100}],
         "rewards": {"exp": 20000, "cash": 10000},
         "description": "建邺城副本，消灭妖风"},
    ]
    for q in quests:
        await load_or_create(session, QuestConfig, q, id=q["id"])


async def init_default_configs():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await init_maps(session)
            await init_npcs(session)
            await init_items(session)
            await init_skills(session)
            await init_monsters(session)
            await init_pets(session)
            await init_quests(session)
        await session.commit()
