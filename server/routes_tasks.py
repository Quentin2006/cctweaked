"""Task management routes — CRUD for multi-turtle task queue."""

import json
import logging
from aiohttp import web

logger = logging.getLogger(__name__)


def register_task_routes(app, task_manager):
    async def handle_tasks_list(request):
        status = request.query.get("status")
        task_type = request.query.get("type")
        tasks = task_manager.list_tasks(status, task_type)
        return web.json_response({"tasks": tasks})

    async def handle_tasks_create(request):
        try:
            data = await request.json()
            task = task_manager.create_task(
                task_type=data["type"],
                goal=data["goal"],
                priority=data.get("priority", 5),
                depends_on=data.get("depends_on", []),
                params=data.get("params", {}),
            )
            return web.json_response({"task": task})
        except KeyError:
            return web.json_response(
                {"error": "Use: type, goal"}, status=400
            )

    async def handle_tasks_claim(request):
        try:
            data = await request.json()
            task = task_manager.claim_task(
                agent_id=data["agent_id"],
                task_types=data.get("task_types"),
            )
            return web.json_response({"task": task})
        except KeyError:
            return web.json_response(
                {"error": "Use: agent_id"}, status=400
            )

    async def handle_tasks_complete(request):
        try:
            data = await request.json()
            ok = task_manager.complete_task(
                task_id=data["task_id"],
                agent_id=data["agent_id"],
                result=data.get("result"),
            )
            return web.json_response({"ok": ok})
        except KeyError:
            return web.json_response(
                {"error": "Use: task_id, agent_id"}, status=400
            )

    async def handle_tasks_fail(request):
        try:
            data = await request.json()
            ok = task_manager.fail_task(
                task_id=data["task_id"],
                agent_id=data["agent_id"],
                error=data["error"],
            )
            return web.json_response({"ok": ok})
        except KeyError:
            return web.json_response(
                {"error": "Use: task_id, agent_id, error"}, status=400
            )

    async def handle_tasks_stats(request):
        stats = task_manager.get_stats()
        return web.json_response({"stats": stats})

    # Register task routes
    app.router.add_get("/api/tasks", handle_tasks_list)
    app.router.add_post("/api/tasks/create", handle_tasks_create)
    app.router.add_post("/api/tasks/claim", handle_tasks_claim)
    app.router.add_post("/api/tasks/complete", handle_tasks_complete)
    app.router.add_post("/api/tasks/fail", handle_tasks_fail)
    app.router.add_get("/api/tasks/stats", handle_tasks_stats)
