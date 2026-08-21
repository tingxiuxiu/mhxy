from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from .config import settings
from .redis_client import init_redis, close_redis
from .exceptions import GameException, AuthException, RateLimitException, PermissionDeniedException
from .routers import auth, character, map, item, battle, quest, social, guild, economy
from .ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    yield
    await close_redis()


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - start)
    return response


@app.exception_handler(GameException)
async def game_exception_handler(request: Request, exc: GameException):
    return JSONResponse(status_code=400, content={"success": False, "msg": str(exc), "code": exc.code})


@app.exception_handler(AuthException)
async def auth_exception_handler(request: Request, exc: AuthException):
    return JSONResponse(status_code=401, content={"success": False, "msg": str(exc), "code": 401})


@app.exception_handler(PermissionDeniedException)
async def forbidden_exception_handler(request: Request, exc: PermissionDeniedException):
    return JSONResponse(status_code=403, content={"success": False, "msg": str(exc), "code": 403})


@app.exception_handler(RateLimitException)
async def rate_exception_handler(request: Request, exc: RateLimitException):
    return JSONResponse(status_code=429, content={"success": False, "msg": str(exc), "code": 429})


app.include_router(auth.router)
app.include_router(character.router)
app.include_router(map.router)
app.include_router(item.router)
app.include_router(battle.router)
app.include_router(quest.router)
app.include_router(social.router)
app.include_router(guild.router)
app.include_router(economy.router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "version": "1.0.0", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok", "ts": int(time.time())}
