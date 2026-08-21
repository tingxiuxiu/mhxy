from fastapi import HTTPException, status


class GameException(Exception):
    def __init__(self, code: int, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthException(GameException):
    def __init__(self, message: str = "认证失败"):
        super().__init__(code=401, message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class PermissionDeniedException(GameException):
    def __init__(self, message: str = "权限不足"):
        super().__init__(code=403, message=message, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundException(GameException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=404, message=message, status_code=status.HTTP_404_NOT_FOUND)


class RateLimitException(GameException):
    def __init__(self, message: str = "操作过于频繁，请稍后再试"):
        super().__init__(code=429, message=message, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class ValidationException(GameException):
    def __init__(self, message: str = "参数校验失败"):
        super().__init__(code=400, message=message)


class BattleException(GameException):
    def __init__(self, message: str = "战斗操作无效"):
        super().__init__(code=1001, message=message)


class MapException(GameException):
    def __init__(self, message: str = "地图移动失败"):
        super().__init__(code=1002, message=message)


class ItemException(GameException):
    def __init__(self, message: str = "物品操作失败"):
        super().__init__(code=1003, message=message)


class QuestException(GameException):
    def __init__(self, message: str = "任务操作失败"):
        super().__init__(code=1004, message=message)


class TradeException(GameException):
    def __init__(self, message: str = "交易失败"):
        super().__init__(code=1005, message=message)


class GuildException(GameException):
    def __init__(self, message: str = "帮派操作失败"):
        super().__init__(code=1006, message=message)


class PetException(GameException):
    def __init__(self, message: str = "宠物操作失败"):
        super().__init__(code=1007, message=message)


class BannedException(GameException):
    def __init__(self, message: str = "账号已被封禁"):
        super().__init__(code=403, message=message, status_code=status.HTTP_403_FORBIDDEN)


class AntiCheatException(GameException):
    def __init__(self, message: str = "检测到异常操作，请重新登录"):
        super().__init__(code=403, message=message, status_code=status.HTTP_403_FORBIDDEN)
