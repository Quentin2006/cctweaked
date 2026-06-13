import asyncio
from aiohttp import web
from TurtleManager import TurtleManager, Move

BLOCKS_FILE = "web/blocks.txt"


def create_app(manager):
    app = web.Application()

    async def handle_move(request):
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
            with open(BLOCKS_FILE) as f:
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
        try:
            data = await request.json()
            atype = data["type"]
            direction = data.get("direction", "forward")
            if atype == "dig":
                ok = await manager.dig(direction)
            elif atype == "place":
                ok = await manager.place(direction, block=data.get("block"),
                                          text=data.get("text"))
            elif atype == "attack":
                ok = await manager.attack(direction)
            else:
                return web.json_response({"error": "Use: dig, place, attack"},
                                         status=400)
            return web.json_response({"ok": ok})
        except KeyError:
            return web.json_response({"error": "Missing 'type'"}, status=400)
        except asyncio.TimeoutError:
            return web.json_response({"error": "turtle did not respond"},
                                     status=504)
        except ConnectionError:
            return web.json_response({"error": "turtle not connected"},
                                     status=503)

    async def handle_inventory_get(request):
        try:
            state = await manager.get_inventory_state()
            return web.json_response(state)
        except asyncio.TimeoutError:
            return web.json_response({"error": "turtle did not respond"},
                                     status=504)
        except ConnectionError:
            return web.json_response({"error": "turtle not connected"},
                                     status=503)

    async def handle_position(request):
        return web.json_response({
            "x": manager.x,
            "y": manager.y,
            "z": manager.z,
            "facing": manager.facing,
        })

    async def handle_inventory_post(request):
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
                    {"error": "Unknown operation"}, status=400)
        except KeyError:
            return web.json_response({"error": "Missing 'type' or params"},
                                     status=400)
        except asyncio.TimeoutError:
            return web.json_response({"error": "turtle did not respond"},
                                     status=504)
        except ConnectionError:
            return web.json_response({"error": "turtle not connected"},
                                     status=503)

    app.router.add_get("/", handle_index)
    app.router.add_get("/move.js", lambda _: web.FileResponse("web/move.js"))  # pyright: ignore
    app.router.add_get("/detect.js", lambda _: web.FileResponse("web/detect.js"))  # pyright: ignore
    app.router.add_get("/visualize.js", lambda _: web.FileResponse("web/visualize.js"))  # pyright: ignore
    app.router.add_get("/action.js", lambda _: web.FileResponse("web/action.js"))  # pyright: ignore
    app.router.add_get("/inventory.js", lambda _: web.FileResponse("web/inventory.js"))  # pyright: ignore
    app.router.add_post("/move", handle_move)
    app.router.add_post("/detect", handle_detect)
    app.router.add_get("/blocks", handle_blocks)
    app.router.add_get("/position", handle_position)
    app.router.add_post("/action", handle_action)
    app.router.add_get("/inventory", handle_inventory_get)
    app.router.add_post("/inventory", handle_inventory_post)
    return app


async def handle_index(_):
    return web.FileResponse("web/index.html")


async def start_http(manager):
    app = create_app(manager)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 3001)
    await site.start()
    print("HTTP on :3001")
    await asyncio.Future()


async def main():
    manager = TurtleManager()
    manager.move(Move.UP, 5)

    await asyncio.gather(
        manager.start(),
        start_http(manager),
    )


asyncio.run(main())
