from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from ..exceptions import GameException

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except GameException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"code": e.code, "message": e.message, "data": None}
            )
        except Exception as e:
            logger.exception(f"Unhandled exception: {e}")
            return JSONResponse(
                status_code=500,
                content={"code": 500, "message": "服务器内部错误", "data": None}
            )
