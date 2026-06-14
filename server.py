"""Entry point — starts WebSocket server and HTTP dashboard concurrently."""

import asyncio
from aiohttp import web
from server import create_app, create_manager, BLOCKS_FILE
from server.bootstrap import bootstrap


async def start_http(manager):
    app, ai_manager = create_app(manager)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 3001)
    await site.start()
    print("HTTP on :3001")
    await asyncio.Future()


async def main():
    bootstrap()
    manager = create_manager(blocks_file=BLOCKS_FILE)
    await asyncio.gather(
        manager.start(),
        start_http(manager),
    )


if __name__ == "__main__":
    asyncio.run(main())
