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

    app.router.add_get("/", handle_index)
    app.router.add_get("/move.js", lambda _: web.FileResponse("web/move.js"))  # pyright: ignore
    app.router.add_get("/detect.js", lambda _: web.FileResponse("web/detect.js"))  # pyright: ignore
    app.router.add_get("/visualize.js", lambda _: web.FileResponse("web/visualize.js"))  # pyright: ignore
    app.router.add_post("/move", handle_move)
    app.router.add_post("/detect", handle_detect)
    app.router.add_get("/blocks", handle_blocks)
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
