from enum import IntEnum, Enum


class Gender(IntEnum):
    MALE = 1
    FEMALE = 2


class Job(IntEnum):
    DATANG = 1
    FANGCUN = 2
    HUASHENG = 3
    NVER = 4
    TIANGONG = 5
    LONGGONG = 6


class Race(IntEnum):
    HUMAN = 1
    FAIRY = 2
    DEMON = 3


class Faction(IntEnum):
    DT = 1
    HS = 2
    LG = 3
    PT = 4
    STL = 5
    PSD = 6


class MapType(IntEnum):
    CITY = 1
    FIELD = 2
    FACTION = 3
    DUNGEON = 4
    SPECIAL = 5


class ItemType(IntEnum):
    EQUIPMENT = 1
    MEDICINE = 2
    COOKING = 3
    DART = 4
    MISC = 5
    QUEST = 6


class EquipSlot(IntEnum):
    WEAPON = 1
    HELMET = 2
    ARMOR = 3
    BELT = 4
    BOOTS = 5
    NECKLACE = 6


class SlotType(IntEnum):
    BAG = 1
    EQUIP = 2
    STORAGE = 3
    PET_EQUIP = 4


class BattleType(IntEnum):
    WILD = 1
    ZHUAGUI = 2
    QUEST = 3
    DUNGEON = 4
    PK = 5
    HUBIAO = 6


class BattleState(str, Enum):
    ONGOING = "ongoing"
    PLAYER_WIN = "player_win"
    PLAYER_LOSE = "player_lose"
    ESCAPED = "escaped"


class BattleSide(IntEnum):
    OUR = 1
    ENEMY = 2


class BattleCharType(IntEnum):
    PLAYER = 1
    PET = 2
    MONSTER = 3


class ActionType(str, Enum):
    ATTACK = "attack"
    SKILL = "skill"
    ITEM = "item"
    DEFEND = "defend"
    SUMMON = "summon"
    ESCAPE = "escape"
    CAPTURE = "capture"


class BattleActionType(IntEnum):
    ATTACK = 1
    SKILL = 2
    ITEM = 3
    DEFEND = 4
    SUMMON = 5
    ESCAPE = 6
    CAPTURE = 7


class QuestStatus(IntEnum):
    IN_PROGRESS = 1
    CAN_COMPLETE = 2
    COMPLETED = 3
    ABANDONED = 4
    FAILED = 5


class QuestType(IntEnum):
    NOVICE = 1
    SHIMEN = 2
    ZHUAGUI = 3
    HUBIAO = 4
    STORY = 5
    DUNGEON = 6
    GUILD = 7


class RequestStatus(IntEnum):
    PENDING = 0
    ACCEPTED = 1
    REJECTED = 2
    EXPIRED = 3
    CANCELLED = 4


class ChatChannel(str, Enum):
    CURRENT = "current"
    WORLD = "world"
    FACTION = "faction"
    TEAM = "team"
    GUILD = "guild"
    PRIVATE = "private"
    SYSTEM = "system"
    RUMOR = "rumor"


class MarketStatus(IntEnum):
    LISTED = 1
    SOLD = 2
    CANCELLED = 3


class GuildPosition(IntEnum):
    LEADER = 1
    DEPUTY = 2
    VICE_LEADER = 2
    ELDER = 3
    HALL_MASTER = 4
    ELITE = 5
    MEMBER = 6


class TradeStatus(IntEnum):
    REQUESTED = 1
    ACCEPTED = 2
    CONFIRMED = 3
    COMPLETED = 4
    CANCELLED = 5


class RechargeStatus(IntEnum):
    PENDING = 1
    PAID = 2
    DELIVERED = 3
    FAILED = 4
    REFUNDED = 5


class BanType(IntEnum):
    TEMP = 1
    PERMANENT = 2
    MUTE = 3


class AdminRole(IntEnum):
    SUPER_ADMIN = 1
    GM = 2
    OPERATOR = 3
