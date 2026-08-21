import pytest
import allure
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import user_service
from app.schemas.user import RegisterRequest, LoginRequest


@allure.epic("用户系统")
@allure.feature("用户注册登录")
class TestUserService:

    @allure.story("用户注册")
    @allure.title("正常注册用户")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.asyncio
    async def test_register_user(self, db_session: AsyncSession, fake_redis):
        with allure.step("调用register接口注册新用户"):
            user = await user_service.register(
                db_session, RegisterRequest(username="testuser", password="password123")
            )
        with allure.step("验证返回用户对象"):
            assert user is not None
            assert user.username == "testuser"
            assert user.id is not None

    @allure.story("用户登录")
    @allure.title("注册后正常登录返回Token")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.asyncio
    async def test_login_user(self, db_session: AsyncSession, fake_redis):
        with allure.step("先注册一个用户"):
            await user_service.register(
                db_session, RegisterRequest(username="loginuser", password="pass123")
            )
            await db_session.commit()
        with allure.step("调用login接口登录"):
            tokens = await user_service.login(
                db_session, LoginRequest(username="loginuser", password="pass123")
            )
        with allure.step("验证返回的Token"):
            assert tokens.access_token
            assert tokens.refresh_token
            assert tokens.token_type == "bearer"
            assert tokens.expires_in > 0

    @allure.story("用户登录")
    @allure.title("错误密码登录应抛出异常")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, db_session: AsyncSession, fake_redis):
        with allure.step("注册一个用户"):
            await user_service.register(
                db_session, RegisterRequest(username="wrongpassuser", password="correctpass")
            )
            await db_session.commit()
        with allure.step("用错误密码登录应抛出认证异常"):
            from app.exceptions import AuthException
            with pytest.raises(AuthException):
                await user_service.login(
                    db_session, LoginRequest(username="wrongpassuser", password="wrongpass")
                )

    @allure.story("用户注册")
    @allure.title("重复用户名注册应抛出异常")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.asyncio
    async def test_duplicate_register(self, db_session: AsyncSession, fake_redis):
        with allure.step("第一次注册成功"):
            await user_service.register(
                db_session, RegisterRequest(username="dupuser", password="pass123")
            )
            await db_session.commit()
        with allure.step("重复注册同名用户应抛出验证异常"):
            from app.exceptions import ValidationException
            with pytest.raises(ValidationException):
                await user_service.register(
                    db_session, RegisterRequest(username="dupuser", password="pass123")
                )
