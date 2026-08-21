import pytest
import allure
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import user_service
from app.services.character_service import character_service
from app.game.enums import Gender, Faction
from app.game.formulas import calc_exp_for_level
from app.schemas.user import RegisterRequest


@allure.epic("角色系统")
@allure.feature("角色创建与成长")
class TestCharacterService:

    async def _create_user(self, db: AsyncSession, username: str):
        user = await user_service.register(
            db, RegisterRequest(username=username, password="pass123")
        )
        await db.flush()
        return user

    @allure.story("创建角色")
    @allure.title("成功创建角色并校验初始属性")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.asyncio
    async def test_create_character(self, db_session: AsyncSession, fake_redis):
        with allure.step("注册用户"):
            user = await self._create_user(db_session, "charuser")
            await db_session.commit()
        with allure.step("创建大唐官府角色"):
            char = await character_service.create_character(
                db_session, user, name="剑侠客", gender=Gender.MALE, faction=Faction.DT
            )
            await db_session.commit()
        with allure.step("验证角色初始属性"):
            assert char.name == "剑侠客"
            assert char.level == 1
            assert char.faction == Faction.DT
            assert char.gender == Gender.MALE
            assert char.hp > 0
            assert char.mp > 0
            assert char.cash == 1000

    @allure.story("角色升级")
    @allure.title("获得足够经验后自动升级")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.asyncio
    async def test_level_up(self, db_session: AsyncSession, fake_redis):
        with allure.step("创建角色"):
            user = await self._create_user(db_session, "lvuser")
            await db_session.commit()
            char = await character_service.create_character(
                db_session, user, name="升级角色", gender=Gender.MALE, faction=Faction.DT
            )
            await db_session.commit()
        with allure.step("加载角色stats并计算升级所需经验"):
            from sqlalchemy import select
            from app.models.character import CharacterStats
            stats_result = await db_session.execute(
                select(CharacterStats).where(CharacterStats.character_id == char.id)
            )
            char.stats = stats_result.scalar_one_or_none()
            old_level = char.level
            next_exp = calc_exp_for_level(old_level + 1) - char.exp
        with allure.step(f"给予{next_exp}经验触发升级"):
            result = await character_service.add_exp(db_session, char, next_exp)
        with allure.step("验证升级结果"):
            assert result["leveled_up"] is True
            assert char.level == old_level + 1
            assert char.stats.pot_points > 0

    @allure.story("属性加点")
    @allure.title("使用潜力点加点到属性")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.asyncio
    async def test_allocate_points(self, db_session: AsyncSession, fake_redis):
        with allure.step("创建角色并设置5点潜力"):
            user = await self._create_user(db_session, "allocuser")
            await db_session.commit()
            char = await character_service.create_character(
                db_session, user, name="加点角色", gender=Gender.MALE, faction=Faction.DT
            )
            from sqlalchemy import select
            from app.models.character import CharacterStats
            stats_result = await db_session.execute(
                select(CharacterStats).where(CharacterStats.character_id == char.id)
            )
            char.stats = stats_result.scalar_one_or_none()
            char.stats.pot_points = 5
            await db_session.flush()
            old_str = char.stats.pot_liliang
            old_tz = char.stats.pot_tizhi
        with allure.step("分配3点力量、2点体质"):
            await character_service.add_pot(db_session, char, "liliang", 3)
            await character_service.add_pot(db_session, char, "tizhi", 2)
        with allure.step("验证属性变化"):
            assert char.stats.pot_liliang == old_str + 3
            assert char.stats.pot_tizhi == old_tz + 2
            assert char.stats.pot_points == 0

    @allure.story("金币管理")
    @allure.title("金币增减操作正确")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.asyncio
    async def test_cash_management(self, db_session: AsyncSession, fake_redis):
        with allure.step("创建角色"):
            user = await self._create_user(db_session, "cashuser")
            await db_session.commit()
            char = await character_service.create_character(
                db_session, user, name="金币角色", gender=Gender.MALE, faction=Faction.DT
            )
            await db_session.commit()
        with allure.step("验证初始金币"):
            initial = char.cash
        with allure.step("增加1000金币"):
            await character_service.add_cash(char, 1000)
            assert char.cash == initial + 1000
        with allure.step("扣除500金币"):
            await character_service.add_cash(char, -500)
            assert char.cash == initial + 500
        with allure.step("扣除超出金币后不应为负"):
            await character_service.add_cash(char, -1000000)
            assert char.cash == 0
