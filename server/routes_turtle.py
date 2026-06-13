"""Turtle operation routes — move, detect, action, inventory, position, blocks."""

import asyncio
import json
import os
import logging
from aiohttp import web
from server.enums import Move

logger = logging.getLogger(__name__)


async def check_ai_lock(request, ai_manager):
    if request.remote not in ("127.0.0.1", "::1") and ai_manager and ai_manager.active:
        return web.json_response(
            {"error": "AI session active — manual controls locked"},
            status=409,
        )
    return None


def register_turtle_routes(app, manager, ai_manager, blocks_file):
    async def handle_move(request):
        lock = await check_ai_lock(request, ai_manager)
        if lock:
            return lock
        try:
            data = await request.json()
            direction = Move[data["direction"].upper()]
            distance = int(data["distance"])
            manager.move(direction, distance)
            return web.json_response({"status": "queued"})
        except KeyError:
            return web.json_response(
                {"error": "Use: FORWARD, BACK, LEFT, RIGHT, UP, DOWN"},
                status=400,
            )
        except (ValueError, TypeError):
            return web.json_response(
                {"error": "distance must be a non-negative integer"},
                status=400,
            )

    async def handle_detect(request):
        lock = await check_ai_lock(request, ai_manager)
        if lock:
            return lock
        try:
            data = await request.json()
            direction = data["direction"].upper()
            block = await manager.inspect_block(direction)
            return web.json_response({"block": block})
        except KeyError:
            return web.json_response({"error": "Use: FORWARD, UP, DOWN"}, status=400)
        except asyncio.TimeoutError:
            return web.json_response({"error": "turtle did not respond"}, status=504)
        except ConnectionError:
            return web.json_response({"error": "turtle not connected"}, status=503)

    async def handle_blocks(request):
        blocks = []
        try:
            with open(blocks_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",", 3)
                    if len(parts) == 4:
                        blocks.append({
                            "x": int(parts[0]),
                            "y": int(parts[1]),
                            "z": int(parts[2]),
                            "name": parts[3],
                        })
        except FileNotFoundError:
            pass
        return web.json_response({"blocks": blocks})

    async def handle_action(request):
        lock = await check_ai_lock(request, ai_manager)
        if lock:
            return lock
        try:
            data = await request.json()
            atype = data["type"]
            direction = data.get("direction", "forward")
            if atype == "dig":
                ok = await manager.dig(direction)
            elif atype == "place":
                ok = await manager.place(
                    direction, block=data.get("block"), text=data.get("text")
                )
            elif atype == "attack":
                ok = await manager.attack(direction)
            else:
                return web.json_response(
                    {"error": "Use: dig, place, attack"}, status=400
                )
            return web.json_response({"ok": ok})
        except KeyError:
            return web.json_response({"error": "Missing 'type'"}, status=400)
        except asyncio.TimeoutError:
            return web.json_response({"error": "turtle did not respond"}, status=504)
        except ConnectionError:
            return web.json_response({"error": "turtle not connected"}, status=503)

    async def handle_inventory_get(request):
        try:
            state = await manager.get_inventory_state()
            return web.json_response(state)
        except asyncio.TimeoutError:
            return web.json_response({"error": "turtle did not respond"}, status=504)
        except ConnectionError:
            return web.json_response({"error": "turtle not connected"}, status=503)

    async def handle_position(request):
        return web.json_response({
            "x": manager.x,
            "y": manager.y,
            "z": manager.z,
            "facing": manager.facing,
        })

    async def handle_inventory_post(request):
        lock = await check_ai_lock(request, ai_manager)
        if lock:
            return lock
        try:
            data = await request.json()
            op = data["type"]
            if op == "select":
                await manager.select_slot(int(data["slot"]))
                return web.json_response({"ok": True})
            elif op == "craft":
                limit = int(data.get("limit", 64))
                ok = await manager.craft(limit)
                return web.json_response({"ok": ok})
            elif op == "transfer":
                ok = await manager.transfer_to(
                    int(data["slot"]),
                    count=int(data["count"]) if "count" in data else None,
                )
                return web.json_response({"ok": ok})
            elif op == "drop":
                ok = await manager.drop(
                    data.get("direction", "forward"),
                    count=int(data["count"]) if "count" in data else None,
                )
                return web.json_response({"ok": ok})
            elif op == "suck":
                ok = await manager.suck(
                    data.get("direction", "forward"),
                    count=int(data["count"]) if "count" in data else None,
                )
                return web.json_response({"ok": ok})
            elif op == "refuel":
                ok = await manager.refuel(
                    count=int(data["count"]) if "count" in data else None,
                )
                return web.json_response({"ok": ok})
            elif op == "equipLeft":
                ok = await manager.equip_left()
                return web.json_response({"ok": ok})
            elif op == "equipRight":
                ok = await manager.equip_right()
                return web.json_response({"ok": ok})
            else:
                return web.json_response(
                    {"error": "Unknown operation"}, status=400
                )
        except KeyError:
            return web.json_response(
                {"error": "Missing 'type' or params"}, status=400
            )
        except asyncio.TimeoutError:
            return web.json_response({"error": "turtle did not respond"}, status=504)
        except ConnectionError:
            return web.json_response({"error": "turtle not connected"}, status=503)

    async def handle_turtles_list(request):
        turtles = manager.list_turtles()
        return web.json_response({
            "turtles": turtles,
            "count": manager.turtle_count,
        })

    # Register routes
    app.router.add_post("/move", handle_move)
    app.router.add_post("/detect", handle_detect)
    app.router.add_get("/blocks", handle_blocks)
    app.router.add_get("/position", handle_position)
    app.router.add_post("/action", handle_action)
    app.router.add_get("/inventory", handle_inventory_get)
    app.router.add_post("/inventory", handle_inventory_post)
    app.router.add_get("/api/turtles", handle_turtles_list)
