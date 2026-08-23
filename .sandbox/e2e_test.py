"""真实 E2E 测试：通过 unix socket 访问 docker compose 里的真实后端容器。

覆盖：注册 -> 登录 -> 创建角色 -> 角色列表/详情 -> 地图信息（读真实 PG 种子数据）
     -> WebSocket 连接/ping-pong（覆盖合并中 ws.py 的 get_db 改动）
     -> 登出后 token 拉黑（真实 Redis）
"""
import asyncio
import json
import os
import sys
import time

import httpx

SOCKET = os.environ.get("E2E_SOCKET", "/workspace/.sandbox/shared/app.sock")
BASE = "http://localhost"

passed, failed = [], []


def check(name: str, cond: bool, detail: str = ""):
    tag = "PASS" if cond else "FAIL"
    (passed if cond else failed).append(name)
    print(f"[{tag}] {name}" + (f"  -> {detail}" if detail else ""))


def main():
    transport = httpx.HTTPTransport(uds=SOCKET)
    username = f"e2e_{int(time.time())}"

    with httpx.Client(transport=transport, base_url=BASE, timeout=15) as c:
        # 1. 服务存活（OpenAPI 文档可访问）
        r = c.get("/docs")
        check("HTTP 服务存活 (/docs)", r.status_code == 200, f"status={r.status_code}")

        # 2. 注册
        r = c.post("/api/auth/register", json={"username": username, "password": "pass123456", "email": ""})
        check("注册用户", r.status_code == 200 and r.json().get("success") is True, r.text[:120])

        # 3. 登录
        r = c.post("/api/auth/login", json={"username": username, "password": "pass123456"})
        token = r.json().get("access_token")
        check("登录获取 token", r.status_code == 200 and bool(token), r.text[:120])
        auth = {"Authorization": f"Bearer {token}"}

        # 4. 当前用户信息
        r = c.get("/api/auth/me", headers=auth)
        check("获取当前用户 (/api/auth/me)", r.status_code == 200 and r.json().get("username") == username, r.text[:120])

        # 5. 创建角色（job=1 大唐官府）
        char_name = f"测试侠客{int(time.time()) % 10000}"
        r = c.post("/api/character/create", json={"name": char_name, "job": 1}, headers=auth)
        ok = r.status_code == 200
        check("创建角色", ok, r.text[:160])

        # 6. 角色列表
        r = c.get("/api/character/list", headers=auth)
        chars = r.json() if r.status_code == 200 else []
        check("角色列表", r.status_code == 200 and len(chars) >= 1, r.text[:160])
        char_id = chars[0]["id"] if chars else None

        if char_id:
            h = {**auth, "X-Char-ID": str(char_id)}

            # 7. 角色详情
            r = c.get("/api/character/info", headers=h)
            ok = r.status_code == 200 and r.json().get("name") == char_name
            check("角色详情 (/api/character/info)", ok, r.text[:200])

            # 8. 地图信息（依赖真实 PG 中的种子数据 map_configs/npc_configs）
            r = c.get("/api/map/current", headers=h)
            ok = r.status_code == 200 and r.json().get("name") == "建邺城" and len(r.json().get("npcs", [])) == 2
            check("地图信息含种子数据 NPC (/api/map/current)", ok, r.text[:200])

            # 9. 移动坐标（写库 + 遭遇判定）
            r = c.post("/api/map/move/coord", json={"direction": "up"}, headers=h)
            check("地图移动 (/api/map/move/coord)", r.status_code == 200 and "pos_y" in r.json(), r.text[:160])

            # 9b. 商店（覆盖合并中 economy_service 的 ShopConfig/ShopItem 导入改动）
            r = c.get("/api/economy/shop/1", headers=h)
            shop_items = r.json() if r.status_code == 200 else []
            ok = r.status_code == 200 and len(shop_items) == 2 and shop_items[0].get("name") == "金创药"
            check("商店货架读取真实 PG 种子数据 (/api/economy/shop/1)", ok, r.text[:200])

            r = c.post("/api/economy/shop/buy", json={"item_config_id": 1, "count": 2}, headers=h)
            ok = r.status_code == 200 and r.json().get("cost") == 200
            check("商店购买扣款 (/api/economy/shop/buy)", ok, r.text[:200])

            r = c.get("/api/character/info", headers=h)
            ok = r.status_code == 200 and r.json().get("cash") == 800
            check("购买后金币减少为800", ok, f"cash={r.json().get('cash') if r.status_code == 200 else r.text[:100]}")

            # 10. WebSocket（覆盖 ws.py 的 get_db 导入改动）
            try:
                asyncio.run(ws_test(token, char_id))
            except Exception as e:  # noqa: BLE001
                check("WebSocket 连接与 ping/pong", False, repr(e))

        # 11. 登出 -> token 进黑名单（真实 Redis）
        r = c.post("/api/auth/logout", headers=auth)
        check("登出", r.status_code == 200, r.text[:120])
        r = c.get("/api/auth/me", headers=auth)
        check("登出后 token 被拉黑", r.status_code in (400, 401), f"status={r.status_code} body={r.text[:100]}")

    print(f"\n===== 结果: {len(passed)} 通过 / {len(failed)} 失败 =====")
    if failed:
        print("失败项:", failed)
        sys.exit(1)


async def ws_test(token: str, char_id: int):
    import websockets

    uri = f"ws://localhost/ws?token={token}&char_id={char_id}"
    async with websockets.unix_connect(SOCKET, uri=uri) as ws:
        first = json.loads(await asyncio.wait_for(ws.recv(), 10))
        check("WebSocket 连接成功", first.get("type") == "connected", json.dumps(first, ensure_ascii=False)[:120])
        await ws.send(json.dumps({"type": "ping"}))
        pong = json.loads(await asyncio.wait_for(ws.recv(), 10))
        check("WebSocket ping/pong", pong.get("type") == "pong", json.dumps(pong, ensure_ascii=False)[:120])


if __name__ == "__main__":
    main()
