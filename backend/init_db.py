import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models import *  # noqa
from app.redis_client import init_redis, close_redis


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")


async def seed_data():
    from app.database import AsyncSessionLocal
    from app.models.map import MapConfig, NpcConfig
    from app.models.monster import MonsterConfig
    from app.models.item import ItemConfig, ShopConfig, ShopItem
    from app.models.skill import SkillConfig
    from app.models.pet import PetConfig
    from app.models.quest import QuestConfig
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(MapConfig).limit(1))
        if existing.scalar_one_or_none():
            print("Seed data already exists, skipping.")
            return

        maps = [
            MapConfig(id=1, name="建邺城", type=1, width=100, height=80, is_dark=False, encounter_rate=0,
                      adjacent_maps=[{"map_id": 2, "entry_x": 50, "entry_y": 70}], description="新手村"),
            MapConfig(id=2, name="江南野外", type=2, width=120, height=100, is_dark=True, encounter_rate=300,
                      adjacent_maps=[{"map_id": 1, "entry_x": 50, "entry_y": 5}, {"map_id": 3, "entry_x": 50, "entry_y": 95}],
                      encounters=[{"monster_id": 1, "weight": 50}, {"monster_id": 2, "weight": 50}], description="初级野外"),
            MapConfig(id=3, name="长安城", type=1, width=150, height=120, is_dark=False, encounter_rate=0,
                      adjacent_maps=[{"map_id": 2, "entry_x": 50, "entry_y": 5}], description="主城"),
        ]
        for m in maps:
            db.add(m)

        npcs = [
            NpcConfig(id=1, name="宠物仙子", title="指引", map_id=1, pos_x=30, pos_y=40, npc_type="guide"),
            NpcConfig(id=2, name="门派传送人", title="传送", map_id=1, pos_x=50, pos_y=50, npc_type="teleport"),
            NpcConfig(id=3, name="钟馗", title="抓鬼", map_id=3, pos_x=80, pos_y=60, npc_type="quest"),
            NpcConfig(id=4, name="门派师傅", title="师门", map_id=3, pos_x=20, pos_y=30, npc_type="quest"),
            NpcConfig(id=5, name="镖头", title="护镖", map_id=3, pos_x=40, pos_y=70, npc_type="quest"),
            NpcConfig(id=99, name="药店老板", title="药店", map_id=3, pos_x=60, pos_y=40, npc_type="shop"),
        ]
        for n in npcs:
            db.add(n)

        items = [
            ItemConfig(id=1, name="金创药", type=3, subtype=1, stackable=True, max_stack=99, sell_price=50, buy_price=100,
                       effect={"hp": 300}, description="回复300气血"),
            ItemConfig(id=2, name="魔法药", type=3, subtype=2, stackable=True, max_stack=99, sell_price=80, buy_price=150,
                       effect={"mp": 200}, description="回复200魔法"),
            ItemConfig(id=3, name="飞行符", type=4, subtype=1, stackable=True, max_stack=99, sell_price=200, buy_price=500,
                       effect={}, description="可快速传送"),
            ItemConfig(id=10, name="青铜剑", type=1, subtype=1, stackable=False, max_stack=1, sell_price=500, buy_price=1000,
                       effect={"damage": 20}, level_req=1, description="初级武器"),
            ItemConfig(id=11, name="布衣", type=1, subtype=4, stackable=False, max_stack=1, sell_price=300, buy_price=600,
                       effect={"defense": 10}, level_req=1, description="初级衣服"),
            ItemConfig(id=20, name="藏宝图", type=4, subtype=2, stackable=True, max_stack=99, sell_price=1000, buy_price=2000,
                       effect={}, description="可能挖出宝贝"),
        ]
        for it in items:
            db.add(it)

        monsters = [
            MonsterConfig(id=1, name="大海龟", level=1, hp=80, mp=20, damage=10, defense=5, speed=5, exp_reward=20,
                          cash_reward=10, skills=[], drops=[{"item_id": 1, "chance": 0.3, "min": 1, "max": 2}]),
            MonsterConfig(id=2, name="巨蛙", level=2, hp=100, mp=30, damage=15, defense=6, speed=8, exp_reward=30,
                          cash_reward=15, skills=[], drops=[{"item_id": 2, "chance": 0.3, "min": 1, "max": 1}]),
            MonsterConfig(id=3, name="野猪", level=3, hp=150, mp=20, damage=20, defense=8, speed=7, exp_reward=50,
                          cash_reward=25, skills=[], drops=[]),
        ]
        for m in monsters:
            db.add(m)

        skills = [
            SkillConfig(id=1, name="普通攻击", type=1, job_req=0, level_req=1, mp_cost=0, target_type=1,
                        damage_factor=1.0, effect={}, description="基础物理攻击"),
            SkillConfig(id=2, name="横扫千军", type=1, job_req=1, level_req=10, mp_cost=30, target_type=1,
                        damage_factor=2.5, effect={}, description="大唐官府绝技"),
        ]
        for s in skills:
            db.add(s)

        pets = [
            PetConfig(id=1, name="大海龟", type=1, level_req=0, base_hp=100, base_mp=30, base_attack=15, base_defense=15,
                      base_speed=5, base_magic=10, growth_rate=1.0, possible_skills=[], capture_rate=600),
        ]
        for p in pets:
            db.add(p)

        quests = [
            QuestConfig(id=1, name="新人引导", type=1, giver_npc_id=1, level_min=1, level_max=5, daily_limit=0,
                        description="跟随指引熟悉游戏",
                        steps=[{"type": "talk", "npc_id": 1}, {"type": "talk", "npc_id": 2}],
                        rewards={"exp": 100, "cash": 100, "items": [{"item_id": 1, "count": 5}]}),
            QuestConfig(id=2, name="师门任务", type=2, giver_npc_id=4, level_min=10, level_max=0, daily_limit=20,
                        description="完成师傅交代的任务",
                        steps=[], rewards={"exp_base": 5000, "cash_base": 3000}),
            QuestConfig(id=3, name="抓鬼任务", type=3, giver_npc_id=3, level_min=20, level_max=0, daily_limit=10,
                        description="捉拿作乱鬼怪", steps=[], rewards={"exp_base": 10000, "cash_base": 5000}),
            QuestConfig(id=4, name="护镖任务", type=4, giver_npc_id=5, level_min=30, level_max=0, daily_limit=5,
                        description="押送镖银", steps=[], rewards={"exp_base": 8000, "cash_base": 10000}),
        ]
        for q in quests:
            db.add(q)

        shop = ShopConfig(id=1, name="建邺药店", npc_id=99, type=1)
        db.add(shop)
        await db.flush()
        shop_items = [
            ShopItem(shop_id=1, item_config_id=1, price=100, stock=-1),
            ShopItem(shop_id=1, item_config_id=2, price=150, stock=-1),
        ]
        for si in shop_items:
            db.add(si)

        await db.commit()
        print("Seed data inserted.")


async def main():
    await init_redis()
    await create_tables()
    await seed_data()
    await close_redis()


if __name__ == "__main__":
    asyncio.run(main())
