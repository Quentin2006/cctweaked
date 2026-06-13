import asyncio
from aiohttp import web
from TurtleManager import TurtleManager, Move


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
                {"error": "Use: FORWARD, BACKWARD, LEFT, RIGHT, UP, DOWN"},
                status=400,
            )
        except (ValueError, TypeError):
            return web.json_response(
                {"error": "distance must be a non-negative integer"},
                status=400,
            )

    app.router.add_post("/move", handle_move)
    return app


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
