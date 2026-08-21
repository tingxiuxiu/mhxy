from fastapi import APIRouter
from .v1 import auth, character, map as map_api, item, pet, quest, social, guild, economy

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(character.router, prefix="/character", tags=["角色"])
api_router.include_router(map_api.router, prefix="/map", tags=["地图"])
api_router.include_router(item.router, prefix="/item", tags=["物品"])
api_router.include_router(pet.router, prefix="/pet", tags=["宠物"])
api_router.include_router(quest.router, prefix="/quest", tags=["任务"])
api_router.include_router(social.router, prefix="/social", tags=["社交"])
api_router.include_router(guild.router, prefix="/guild", tags=["帮派"])
api_router.include_router(economy.router, prefix="/economy", tags=["经济"])
