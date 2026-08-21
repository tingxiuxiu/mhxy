from fastapi import APIRouter
from . import auth as admin_auth, config, user as admin_user, stats

admin_router = APIRouter()

admin_router.include_router(admin_auth.router, prefix="/auth", tags=["管理后台-认证"])
admin_router.include_router(config.router, prefix="/config", tags=["管理后台-配置"])
admin_router.include_router(admin_user.router, prefix="/user", tags=["管理后台-用户"])
admin_router.include_router(stats.router, prefix="/stats", tags=["管理后台-统计"])
