from .enums import Faction


FACTION_NAMES = {
    Faction.DT: "大唐官府",
    Faction.HS: "化生寺",
    Faction.LG: "龙宫",
    Faction.PT: "普陀山",
    Faction.STL: "狮驼岭",
    Faction.PSD: "盘丝洞",
}

FACTION_RACE = {
    Faction.DT: 1,
    Faction.HS: 1,
    Faction.LG: 2,
    Faction.PT: 2,
    Faction.STL: 3,
    Faction.PSD: 3,
}

EXP_TABLE = [0]
for i in range(1, 176):
    if i <= 30:
        exp = int(i * i * i * 12 + i * i * 80 + i * 100)
    elif i <= 50:
        exp = int(i * i * i * 20 + i * i * 100 + i * 200)
    elif i <= 100:
        exp = int(i * i * i * 40 + i * i * 200 + i * 500)
    else:
        exp = int(i * i * i * 80 + i * i * 400 + i * 1000)
    EXP_TABLE.append(exp)

LEVEL_UP_POT_POINTS = {
    range(1, 10): 5,
    range(10, 30): 6,
    range(30, 176): 7,
}

HP_PER_TIZHI = {
    1: 5,
    2: 4.5,
    3: 6,
}
MP_PER_MOLI = {
    1: 3,
    2: 5,
    3: 2.5,
}
DAMAGE_PER_LILIANG = {
    1: 0.7,
    2: 0.5,
    3: 0.8,
}
DEFENSE_PER_NAILI = {
    1: 1.6,
    2: 1.2,
    3: 1.4,
}
SPEED_PER_MINJIE = {
    1: 0.7,
    2: 0.7,
    3: 0.7,
}
MAGIC_DAMAGE_PER_MOLI = {
    1: 0.4,
    2: 0.7,
    3: 0.5,
}
MAGIC_DEFENSE_PER_MOLI = {
    1: 0.2,
    2: 0.3,
    3: 0.2,
}

BASE_HIT_RATE = 85
BASE_ESCAPE_RATE = 50
CRITICAL_MULTIPLIER = 1.8

MAX_BAG_SIZE = 20
MAX_STORAGE_SIZE = 40
MAX_PET_BATTLE = 3
MAX_PET_TOTAL = 8

SHIMEN_DAILY_ROUNDS = 20
ZHUAGUI_DAILY_ROUNDS = 50
HUBIAO_DAILY_ROUNDS = 50

TEAM_MAX_MEMBERS = 5

CHAT_WORLD_MIN_LEVEL = 10

TRADE_MAX_DISTANCE = 5

MOVE_COST_MP = 0

MONEY_CARRY_LIMIT_BASE = 100000
MONEY_CARRY_LIMIT_PER_LEVEL = 100000
