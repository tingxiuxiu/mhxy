from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from ..game.enums import BattleSide, BattleCharType, ActionType, BattleState as BattleStateEnum
import copy


@dataclass
class BuffState:
    buff_id: int
    name: str
    duration: int
    effect: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BattleUnit:
    unit_id: str
    char_type: BattleCharType
    side: BattleSide
    position: int
    char_id: int
    name: str
    level: int
    hp: int
    mp: int
    hp_max: int
    mp_max: int
    damage: int
    defense: int
    speed: int
    magic_damage: int
    magic_defense: int
    hit: int
    practice_phys: int = 0
    practice_def: int = 0
    is_dead: bool = False
    is_alive: bool = True
    buffs: List[BuffState] = field(default_factory=list)
    skills: List[int] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "unit_id": self.unit_id,
            "char_type": self.char_type.value,
            "side": self.side.value,
            "position": self.position,
            "char_id": self.char_id,
            "name": self.name,
            "level": self.level,
            "hp": self.hp,
            "mp": self.mp,
            "hp_max": self.hp_max,
            "mp_max": self.mp_max,
            "damage": self.damage,
            "defense": self.defense,
            "speed": self.speed,
            "magic_damage": self.magic_damage,
            "magic_defense": self.magic_defense,
            "is_alive": self.is_alive and not self.is_dead,
        }


@dataclass
class BattleCommand:
    unit_id: str
    action_type: ActionType
    target_id: Optional[str] = None
    skill_id: Optional[int] = None
    item_id: Optional[int] = None
    pet_id: Optional[int] = None


@dataclass
class ActionResult:
    actor_id: str
    action_type: ActionType
    success: bool
    message: str
    targets: List[Dict[str, Any]] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BattleState:
    battle_id: int
    battle_type: int
    map_id: int
    state: BattleStateEnum = BattleStateEnum.ONGOING
    turn: int = 0
    player_units: List[BattleUnit] = field(default_factory=list)
    enemy_units: List[BattleUnit] = field(default_factory=list)
    commands: Dict[str, BattleCommand] = field(default_factory=dict)
    turn_actions: List[ActionResult] = field(default_factory=list)
    extra_data: Dict[str, Any] = field(default_factory=dict)
    round_start_ts: float = 0

    @property
    def units(self) -> List[BattleUnit]:
        return self.player_units + self.enemy_units

    def get_unit(self, unit_id: str) -> Optional[BattleUnit]:
        for u in self.units:
            if u.unit_id == unit_id:
                return u
        return None

    def get_player_unit(self, char_id: int) -> Optional[BattleUnit]:
        for u in self.player_units:
            if u.char_id == char_id:
                return u
        return None

    def get_alive_enemies(self) -> List[BattleUnit]:
        return [u for u in self.enemy_units if u.is_alive and not u.is_dead]

    def get_alive_players(self) -> List[BattleUnit]:
        return [u for u in self.player_units if u.is_alive and not u.is_dead]

    def is_battle_over(self) -> Optional[BattleStateEnum]:
        if not self.get_alive_players():
            return BattleStateEnum.PLAYER_LOSE
        if not self.get_alive_enemies():
            return BattleStateEnum.PLAYER_WIN
        return None
