import random
import math
from typing import Tuple

from .constants import (
    EXP_TABLE, HP_PER_TIZHI, MP_PER_MOLI, DAMAGE_PER_LILIANG, DEFENSE_PER_NAILI,
    SPEED_PER_MINJIE, MAGIC_DAMAGE_PER_MOLI, MAGIC_DEFENSE_PER_MOLI,
    BASE_HIT_RATE, CRITICAL_MULTIPLIER, LEVEL_UP_POT_POINTS
)


def calc_exp_for_level(level: int) -> int:
    if level < 1 or level >= len(EXP_TABLE):
        return 0
    return EXP_TABLE[level]


def calc_level_from_exp(exp: int) -> Tuple[int, int]:
    level = 1
    for i in range(1, len(EXP_TABLE)):
        if exp >= EXP_TABLE[i]:
            level = i
        else:
            break
    next_exp = EXP_TABLE[level + 1] if level + 1 < len(EXP_TABLE) else EXP_TABLE[level]
    return level, next_exp


def get_pot_points_for_level(level: int) -> int:
    for level_range, points in LEVEL_UP_POT_POINTS.items():
        if level in level_range:
            return points
    return 7


def calc_character_combat_stats(
    race: int,
    level: int,
    base_hp: int,
    base_mp: int,
    base_hit: int,
    base_damage: int,
    base_defense: int,
    base_speed: int,
    base_magic_damage: int,
    base_magic_defense: int,
    pot_tizhi: int,
    pot_moli: int,
    pot_liliang: int,
    pot_naili: int,
    pot_minjie: int,
    equip_bonus: dict | None = None,
    buff_bonus: dict | None = None,
) -> dict:
    equip_bonus = equip_bonus or {}
    buff_bonus = buff_bonus or {}

    hp_rate = HP_PER_TIZHI.get(race, 5)
    mp_rate = MP_PER_MOLI.get(race, 4)
    damage_rate = DAMAGE_PER_LILIANG.get(race, 0.7)
    defense_rate = DEFENSE_PER_NAILI.get(race, 1.5)
    speed_rate = SPEED_PER_MINJIE.get(race, 0.7)
    mdamage_rate = MAGIC_DAMAGE_PER_MOLI.get(race, 0.5)
    mdefense_rate = MAGIC_DEFENSE_PER_MOLI.get(race, 0.2)

    hp_max = int(base_hp + level * 5 + pot_tizhi * hp_rate * 5 + equip_bonus.get("hp", 0))
    mp_max = int(base_mp + level * 3 + pot_moli * mp_rate * 3 + equip_bonus.get("mp", 0))
    hit = int(base_hit + pot_liliang * 0.3 + level + equip_bonus.get("hit", 0))
    damage = int(base_damage + pot_liliang * damage_rate + equip_bonus.get("damage", 0))
    defense = int(base_defense + pot_naili * defense_rate + equip_bonus.get("defense", 0))
    speed = int(base_speed + pot_minjie * speed_rate + equip_bonus.get("speed", 0))
    magic_damage = int(base_magic_damage + pot_moli * mdamage_rate + equip_bonus.get("magic_damage", 0))
    magic_defense = int(base_magic_defense + pot_moli * mdefense_rate + level * 0.3 + equip_bonus.get("magic_defense", 0))

    hp_max += buff_bonus.get("hp_percent", 0) / 100 * hp_max + buff_bonus.get("hp_flat", 0)
    mp_max += buff_bonus.get("mp_percent", 0) / 100 * mp_max + buff_bonus.get("mp_flat", 0)
    damage += buff_bonus.get("damage_percent", 0) / 100 * damage + buff_bonus.get("damage_flat", 0)
    defense += buff_bonus.get("defense_percent", 0) / 100 * defense + buff_bonus.get("defense_flat", 0)
    speed += buff_bonus.get("speed_percent", 0) / 100 * speed + buff_bonus.get("speed_flat", 0)
    magic_damage += buff_bonus.get("mdamage_percent", 0) / 100 * magic_damage + buff_bonus.get("mdamage_flat", 0)
    magic_defense += buff_bonus.get("mdefense_percent", 0) / 100 * magic_defense + buff_bonus.get("mdefense_flat", 0)

    return {
        "hp_max": max(1, int(hp_max)),
        "mp_max": max(0, int(mp_max)),
        "hit": max(1, int(hit)),
        "damage": max(1, int(damage)),
        "defense": max(0, int(defense)),
        "speed": max(1, int(speed)),
        "magic_damage": max(1, int(magic_damage)),
        "magic_defense": max(0, int(magic_defense)),
    }


def calc_pet_combat_stats(
    level: int,
    gz: int,
    fy: int,
    tz: int,
    sd: int,
    fz: int,
    growth: float,
) -> dict:
    hp_max = int(tz / 1000 * growth * level * 6 + level * 20)
    mp_max = int(fz / 1000 * growth * level * 4 + level * 10)
    damage = int(gz / 1000 * growth * level * 1.2 + level * 5)
    defense = int(fy / 1000 * growth * level * 1.5 + level * 3)
    speed = int(sd / 1000 * growth * level * 0.8 + level * 2)
    magic_damage = int(fz / 1000 * growth * level * 0.8 + level * 3)
    magic_defense = int(fz / 1000 * growth * level * 0.5 + level * 2)

    return {
        "hp_max": max(1, hp_max),
        "mp_max": max(0, mp_max),
        "hit": max(1, int(damage * 1.5)),
        "damage": max(1, damage),
        "defense": max(0, defense),
        "speed": max(1, speed),
        "magic_damage": max(1, magic_damage),
        "magic_defense": max(0, magic_defense),
    }


def calc_physical_damage(
    attacker_damage: int,
    defender_defense: int,
    attacker_practice: int = 0,
    defender_practice: int = 0,
    is_crit: bool = False,
    skill_multiplier: float = 1.0,
) -> Tuple[int, bool, float]:
    practice_diff = attacker_practice - defender_practice
    practice_factor = 1 + practice_diff * 0.02
    practice_factor = max(0.2, min(2.0, practice_factor))

    base_damage = attacker_damage * skill_multiplier - defender_defense * 0.8
    base_damage = max(1, base_damage)
    rand_factor = random.uniform(0.9, 1.1)
    damage = int(base_damage * practice_factor * rand_factor)
    damage = max(1, damage)

    if is_crit:
        damage = int(damage * CRITICAL_MULTIPLIER)

    return damage, is_crit, rand_factor


def calc_magic_damage(
    attacker_mdamage: int,
    defender_mdefense: int,
    attacker_practice: int = 0,
    defender_practice: int = 0,
    skill_multiplier: float = 1.0,
    target_count: int = 1,
) -> int:
    practice_diff = attacker_practice - defender_practice
    practice_factor = 1 + practice_diff * 0.02
    practice_factor = max(0.2, min(2.0, practice_factor))

    decay = 1.0
    if target_count > 1:
        decay = 1 - (target_count - 1) * 0.1
        decay = max(0.6, decay)

    base_damage = (attacker_mdamage * skill_multiplier - defender_mdefense * 0.7) * decay
    base_damage = max(1, base_damage)
    rand_factor = random.uniform(0.9, 1.1)
    damage = int(base_damage * practice_factor * rand_factor)
    return max(1, damage)


def roll_hit(attacker_hit: int, defender_speed: int, attacker_level: int, defender_level: int) -> bool:
    hit_chance = BASE_HIT_RATE
    hit_chance += (attacker_hit - defender_speed) * 0.1
    hit_chance += (attacker_level - defender_level) * 1.5
    hit_chance = max(10, min(95, hit_chance))
    return random.randint(1, 100) <= hit_chance


def roll_crit(base_crit_rate: int = 5) -> bool:
    return random.randint(1, 100) <= base_crit_rate


def roll_escape(attacker_level: int, defender_level: int) -> bool:
    escape_chance = 50
    escape_chance += (attacker_level - defender_level) * 2
    escape_chance = max(10, min(90, escape_chance))
    return random.randint(1, 100) <= escape_chance


def roll_capture(pet_level: int, pet_hp_percent: float, practice_capture: int = 0) -> bool:
    base_rate = 20
    base_rate += practice_capture * 2
    hp_factor = 1 - pet_hp_percent * 0.5
    final_rate = base_rate * hp_factor
    final_rate = max(5, min(80, final_rate))
    return random.randint(1, 100) <= final_rate


def calc_battle_rewards(
    monster_levels: list[int],
    player_level: int,
    is_team: bool = False,
    team_size: int = 1,
    double_exp: bool = False,
) -> dict:
    total_base_exp = 0
    total_base_cash = 0
    for mlv in monster_levels:
        level_diff = player_level - mlv
        exp_factor = 1.0
        cash_factor = 1.0
        if level_diff > 10:
            exp_factor = max(0.1, 1 - level_diff * 0.05)
            cash_factor = max(0.1, 1 - level_diff * 0.05)
        elif level_diff < -5:
            exp_factor = min(2.0, 1 + abs(level_diff) * 0.1)
            cash_factor = min(2.0, 1 + abs(level_diff) * 0.1)
        total_base_exp += int(mlv * 50 * exp_factor)
        total_base_cash += int(mlv * 30 * cash_factor)

    if is_team and team_size > 1:
        team_bonus = 1 + (team_size - 1) * 0.1
        total_base_exp = int(total_base_exp * team_bonus / team_size)
        total_base_cash = int(total_base_cash * team_bonus / team_size)

    if double_exp:
        total_base_exp *= 2

    return {
        "exp": total_base_exp,
        "cash": total_base_cash,
    }


def roll_drop(drop_table: list[dict]) -> list[dict]:
    drops = []
    for drop in drop_table:
        rate = drop.get("rate", 0)
        if random.randint(1, 10000) <= rate * 100:
            min_count = drop.get("min_count", 1)
            max_count = drop.get("max_count", 1)
            count = random.randint(min_count, max_count)
            drops.append({
                "item_config_id": drop["item_id"],
                "count": count,
            })
    return drops


def money_carry_limit(level: int) -> int:
    from .constants import MONEY_CARRY_LIMIT_BASE, MONEY_CARRY_LIMIT_PER_LEVEL
    return MONEY_CARRY_LIMIT_BASE + level * MONEY_CARRY_LIMIT_PER_LEVEL


def calc_combat_stats(level: int, job: int, strength: int, magic: int, vitality: int,
                      endurance: int, agility: int, practice_phys: int = 0, equip_bonus: dict = None) -> dict:
    race = 1
    base_hp = 100 if job in [1, 3] else 80
    base_mp = 50 if job in [2, 6] else 30
    base_hit = 80
    base_damage = 10 + level * 2
    base_defense = 5 + level
    base_speed = 10
    base_mdmg = 5 + level
    base_mdef = 3
    return calc_character_combat_stats(
        race, level, base_hp, base_mp, base_hit, base_damage, base_defense, base_speed,
        base_mdmg, base_mdef, vitality, magic, strength, endurance, agility, equip_bonus or {}
    )


def calc_damage(attacker_damage: int, defender_defense: int, skill_multiplier: float = 1.0,
                attacker_practice: int = 0, defender_practice: int = 0) -> int:
    dmg, _, _ = calc_physical_damage(attacker_damage, defender_defense, attacker_practice, defender_practice, False, skill_multiplier)
    return dmg


def calc_hit(attacker_hit: int, defender_speed: int, attacker_level: int = 1, defender_level: int = 1) -> int:
    chance = BASE_HIT_RATE + (attacker_hit - defender_speed) * 0.1 + (attacker_level - defender_level) * 1.5
    return int(max(10, min(95, chance)))


def calc_crit() -> bool:
    return roll_crit(10)


def calc_monster_stats(mcfg, level: int) -> dict:
    hp_max = int(mcfg.hp * (1 + (level - mcfg.level) * 0.15))
    mp_max = int(mcfg.mp * (1 + (level - mcfg.level) * 0.1))
    damage = int(mcfg.damage * (1 + (level - mcfg.level) * 0.1))
    defense = int(mcfg.defense * (1 + (level - mcfg.level) * 0.1))
    speed = int(mcfg.speed * (1 + (level - mcfg.level) * 0.05))
    exp_reward = int(mcfg.exp_reward * (1 + (level - mcfg.level) * 0.2))
    cash_reward = int(mcfg.cash_reward * (1 + (level - mcfg.level) * 0.15))
    return {
        "hp_max": max(1, hp_max), "mp_max": max(0, mp_max), "hit": 80,
        "damage": max(1, damage), "defense": max(0, defense), "speed": max(1, speed),
        "magic_damage": damage, "magic_defense": defense,
        "exp_reward": max(1, exp_reward), "cash_reward": max(0, cash_reward),
    }
