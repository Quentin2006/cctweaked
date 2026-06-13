"""Turtle Control server package — app factory and route registration."""

import os
import logging
from aiohttp import web

from server.turtle_manager import TurtleManager
from server.ai_agent import AISessionManager
from server.task_manager import TaskManager
from server.routes_turtle import register_turtle_routes
from server.routes_ai import register_ai_routes
from server.routes_tasks import register_task_routes

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_DIR", "data")
BLOCKS_FILE = os.getenv("BLOCKS_FILE", os.path.join(DATA_DIR, "blocks.txt"))

task_manager = TaskManager()


def handle_index(_):
    return web.FileResponse("web/index.html")


def create_app(manager, ai_manager=None):
    app = web.Application()
    ai_manager = ai_manager or AISessionManager()

    # Static file handlers
    static_files = {
        "/move.js": "web/js/move.js",
        "/detect.js": "web/js/detect.js",
        "/action.js": "web/js/action.js",
        "/visualize.js": "web/js/visualize.js",
        "/inventory.js": "web/js/inventory.js",
        "/ai.js": "web/js/ai.js",
        "/turtles.js": "web/js/turtles.js",
    }

    async def make_static_handler(path):
        async def handler(_):
            return web.FileResponse(path)
        return handler

    import asyncio
    for route, fpath in static_files.items():
        app.router.add_get(route, asyncio.run(make_static_handler(fpath)))

    app.router.add_get("/", handle_index)

    # Register route groups
    register_turtle_routes(app, manager, ai_manager, BLOCKS_FILE)
    register_ai_routes(app, ai_manager)
    register_task_routes(app, task_manager)

    return app, ai_manager


def create_manager(blocks_file=None):
    return TurtleManager(blocks_file=blocks_file or BLOCKS_FILE)
