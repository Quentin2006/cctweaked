"""HTTP server for Turtle Control — API endpoints, AI session management, static files."""
import asyncio
import json
import logging
import os
from aiohttp import web
from TurtleManager import TurtleManager, Move
from bootstrap import bootstrap
from ai_agent import AISessionManager
from task_manager import TaskManager
from agent_registry import get_agent_type, list_agent_types

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_DIR", "data")
BLOCKS_FILE = os.getenv("BLOCKS_FILE", os.path.join(DATA_DIR, "blocks.txt"))

task_manager = TaskManager()


async def handle_index(_):
    return web.FileResponse("web/index.html")


def create_app(manager, ai_manager=None):
    app = web.Application()
    ai_manager = ai_manager or AISessionManager()

    async def check_ai_lock(request):
        if ai_manager and ai_manager.active:
            return web.json_response(
                {"error": "AI session active — manual controls locked"},
                status=409,
            )
        return None

    async def handle_move(request):
        lock = await check_ai_lock(request)
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
        lock = await check_ai_lock(request)
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
        lock = await check_ai_lock(request)
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
        lock = await check_ai_lock(request)
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

    # AI routes
    async def handle_ai_session(request):
        try:
            data = await request.json()
            goal = data["goal"]
        except (KeyError, json.JSONDecodeError):
            return web.json_response(
                {"error": "Missing 'goal' field"}, status=400
            )
        try:
            session = ai_manager.create(goal)
        except RuntimeError:
            return web.json_response(
                {"error": "AI session already active"}, status=409
            )
        asyncio.create_task(session.start())
        return web.json_response({"session_id": session.id})

    async def handle_ai_stream(request):
        session_id = request.match_info["id"]
        session = ai_manager.get(session_id)
        if not session:
            return web.json_response(
                {"error": "Session not found"}, status=404
            )
        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        await response.prepare(request)
        async for event in session.stream_events():
            await response.write(
                f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode()
            )
        return response

    async def handle_ai_answer(request):
        try:
            data = await request.json()
            session = ai_manager.get(data["session_id"])
            if not session:
                return web.json_response(
                    {"error": "Session not found"}, status=404
                )
            await session.answer_question(data["answer"])
            return web.json_response({"ok": True})
        except KeyError:
            return web.json_response(
                {"error": "Missing 'session_id' or 'answer'"}, status=400
            )

    async def handle_ai_cancel(request):
        try:
            data = await request.json()
            ai_manager.cancel(data["session_id"])
            return web.json_response({"ok": True})
        except KeyError:
            return web.json_response(
                {"error": "Missing 'session_id'"}, status=400
            )

    # ---- Task Manager routes ------------------------------------------------

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

    # ---- New AI Session routes ----------------------------------------------

    async def handle_sessions_create(request):
        try:
            data = await request.json()
            goal = data["goal"]
        except KeyError:
            return web.json_response(
                {"error": "Use: goal"}, status=400
            )
        try:
            session = ai_manager.create(goal)
        except RuntimeError as e:
            return web.json_response(
                {"error": str(e)}, status=503
            )
        asyncio.create_task(session.start())
        return web.json_response({"session_id": session.id, "status": "running"})

    async def handle_sessions_list(request):
        status = request.query.get("status")
        sessions = ai_manager.list_sessions(status)
        return web.json_response({"sessions": sessions})

    async def handle_sessions_answer(request):
        try:
            data = await request.json()
            answer = data["answer"]
            session_id = request.match_info["session_id"]
            session = ai_manager._sessions[session_id]
            await session.answer_question(answer)
            return web.json_response({"ok": True})
        except KeyError:
            return web.json_response(
                {"error": "Session not found"}, status=404
            )

    async def handle_sessions_cancel(request):
        session_id = request.match_info["session_id"]
        ai_manager.cancel(session_id)
        return web.json_response({"ok": True})

    async def handle_sessions_stats(request):
        stats = ai_manager.get_stats()
        return web.json_response({"stats": stats})

    # ---- Turtle routes ------------------------------------------------------

    async def handle_turtles_list(request):
        turtles = manager.list_turtles()
        return web.json_response({
            "turtles": turtles,
            "count": manager.turtle_count,
        })

    # Static file handlers (replacing lambdas)
    async def handle_move_js(_):
        return web.FileResponse("web/move.js")

    async def handle_detect_js(_):
        return web.FileResponse("web/detect.js")

    async def handle_visualize_js(_):
        return web.FileResponse("web/visualize.js")

    async def handle_action_js(_):
        return web.FileResponse("web/action.js")

    async def handle_inventory_js(_):
        return web.FileResponse("web/inventory.js")

    async def handle_ai_js(_):
        return web.FileResponse("web/ai.js")

    async def handle_turtles_js(_):
        return web.FileResponse("web/turtles.js")

    # Route registrations
    app.router.add_get("/", handle_index)
    app.router.add_get("/move.js", handle_move_js)
    app.router.add_get("/detect.js", handle_detect_js)
    app.router.add_get("/visualize.js", handle_visualize_js)
    app.router.add_get("/action.js", handle_action_js)
    app.router.add_get("/inventory.js", handle_inventory_js)
    app.router.add_get("/ai.js", handle_ai_js)
    app.router.add_get("/turtles.js", handle_turtles_js)
    app.router.add_post("/move", handle_move)
    app.router.add_post("/detect", handle_detect)
    app.router.add_get("/blocks", handle_blocks)
    app.router.add_get("/position", handle_position)
    app.router.add_post("/action", handle_action)
    app.router.add_get("/inventory", handle_inventory_get)
    app.router.add_post("/inventory", handle_inventory_post)
    app.router.add_post("/api/ai/session", handle_ai_session)
    app.router.add_get("/api/ai/stream/{id}", handle_ai_stream)
    app.router.add_post("/api/ai/answer", handle_ai_answer)
    app.router.add_post("/api/ai/cancel", handle_ai_cancel)
    # Task routes
    app.router.add_get("/api/tasks", handle_tasks_list)
    app.router.add_post("/api/tasks/create", handle_tasks_create)
    app.router.add_post("/api/tasks/claim", handle_tasks_claim)
    app.router.add_post("/api/tasks/complete", handle_tasks_complete)
    app.router.add_post("/api/tasks/fail", handle_tasks_fail)
    app.router.add_get("/api/tasks/stats", handle_tasks_stats)
    # AI session routes
    app.router.add_post("/api/sessions/create", handle_sessions_create)
    app.router.add_get("/api/sessions", handle_sessions_list)
    app.router.add_post("/api/sessions/{session_id}/answer", handle_sessions_answer)
    app.router.add_post("/api/sessions/{session_id}/cancel", handle_sessions_cancel)
    app.router.add_get("/api/sessions/stats", handle_sessions_stats)
    # Turtle routes
    app.router.add_get("/api/turtles", handle_turtles_list)

    return app, ai_manager


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
    manager = TurtleManager(blocks_file=BLOCKS_FILE)
    manager.move(Move.UP, 5)
    await asyncio.gather(
        manager.start(),
        start_http(manager),
    )


if __name__ == "__main__":
    asyncio.run(main())
