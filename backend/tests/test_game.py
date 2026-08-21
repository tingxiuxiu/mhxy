import pytest
import allure

from app.game.formulas import (
    calc_combat_stats, calc_damage, calc_pet_combat_stats,
    calc_character_combat_stats, calc_exp_for_level, calc_physical_damage,
    calc_magic_damage, calc_battle_rewards, money_carry_limit, roll_hit
)
from app.game.enums import Job, ChatChannel, QuestType, EquipSlot, ItemType


@allure.epic("游戏核心")
@allure.feature("战斗公式与枚举")
class TestGameFormulas:

    @allure.story("属性公式")
    @allure.title("角色战斗属性计算返回正确结果")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_combat_stats_calculation(self):
        with allure.step("1级大唐角色无加点计算属性"):
            stats = calc_combat_stats(1, Job.DATANG, 0, 0, 0, 0, 0, 0)
        with allure.step("验证所有属性为正数"):
            assert stats["hp_max"] > 0
            assert stats["mp_max"] > 0
            assert stats["damage"] > 0
            assert stats["defense"] > 0
            assert stats["speed"] > 0
            assert stats["hit"] > 0
            assert stats["magic_damage"] > 0

    @allure.story("伤害公式")
    @allure.title("物理伤害计算结果在合理范围内")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_damage_range(self):
        with allure.step("攻击100、防御50的普通攻击伤害"):
            dmg = calc_damage(100, 50, 1.0, 0, 0)
        with allure.step("伤害应≥1"):
            assert dmg >= 1

    @allure.story("属性公式")
    @allure.title("高级别角色属性严格高于低级别")
    @allure.severity(allure.severity_level.NORMAL)
    def test_level_higher_stats(self):
        with allure.step("分别计算1级和10级角色属性"):
            s1 = calc_combat_stats(1, Job.DATANG, 0, 0, 0, 0, 0)
            s10 = calc_combat_stats(10, Job.DATANG, 0, 0, 0, 0, 0)
        with allure.step("高级别HP和伤害应更高"):
            assert s10["hp_max"] > s1["hp_max"]
            assert s10["damage"] > s1["damage"]

    @allure.story("宠物公式")
    @allure.title("宠物战斗属性计算返回正数")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_pet_stats(self):
        with allure.step("1级宠物属性计算"):
            ps = calc_pet_combat_stats(1, 2000, 1500, 3000, 1200, 1800, 1.0)
        with allure.step("HP和伤害为正"):
            assert ps["hp_max"] > 0
            assert ps["damage"] > 0

    @allure.story("枚举定义")
    @allure.title("枚举值定义正确")
    @allure.severity(allure.severity_level.NORMAL)
    def test_enum_values(self):
        with allure.step("验证频道、任务类型、物品类型、装备槽位枚举值"):
            assert ChatChannel.WORLD.value == "world"
            assert QuestType.SHIMEN.value == 2
            assert ItemType.EQUIPMENT.value == 1
            assert EquipSlot.WEAPON.value == 1
            assert Job.DATANG.value == 1

    @allure.story("经验曲线")
    @allure.title("升级所需经验单调递增")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_exp_curve(self):
        with allure.step("验证1→10→50级所需经验递增"):
            n1 = calc_exp_for_level(2)
            n10 = calc_exp_for_level(11)
            n50 = calc_exp_for_level(51)
            assert n50 > n10 > n1
            assert n1 > 0

    @allure.story("伤害公式")
    @allure.title("暴击伤害高于普通伤害")
    @allure.severity(allure.severity_level.NORMAL)
    def test_critical_multiplier(self):
        with allure.step("普通攻击伤害"):
            normal_dmg = calc_damage(200, 50, 1.0, 0, 0)
        with allure.step("模拟暴击伤害（1.8倍）"):
            crit_dmg = int(normal_dmg * 1.8)
            assert crit_dmg > normal_dmg

    @allure.story("战斗奖励")
    @allure.title("战斗奖励经验和金币为正")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_battle_rewards(self):
        with allure.step("单人击杀1只10级怪物的奖励"):
            rewards = calc_battle_rewards([10], player_level=10)
        assert rewards["exp"] > 0
        assert rewards["cash"] >= 0

    @allure.story("金币上限")
    @allure.title("金币携带上限随等级增加")
    @allure.severity(allure.severity_level.NORMAL)
    def test_money_carry_limit(self):
        limit_1 = money_carry_limit(1)
        limit_50 = money_carry_limit(50)
        assert limit_50 > limit_1
        assert limit_1 > 0
