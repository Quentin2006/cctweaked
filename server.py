import asyncio
from aiohttp import web
from TurtleManager import TurtleManager, Move, Detect


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
            side = Detect[data["side"].upper()]
            is_block_ahead = manager.detect(side)
            return web.json_response(is_block_ahead)
        except KeyError:
            return web.json_response({"error": "Use: FRONT, UP, DOWN"}, status=400)

    app.router.add_get("/", handle_index)
    app.router.add_post("/move", handle_move)
    app.router.add_post("/detect", handle_detect)
    return app


async def handle_index(_):
    return web.FileResponse("index.html")


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
