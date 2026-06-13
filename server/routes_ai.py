"""AI session routes — create, stream, answer, cancel, list sessions."""

import json
import logging
from aiohttp import web

logger = logging.getLogger(__name__)


def register_ai_routes(app, ai_manager):
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
        from asyncio import create_task
        create_task(session.start())
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
        from asyncio import create_task
        create_task(session.start())
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

    # Register AI routes
    app.router.add_post("/api/ai/session", handle_ai_session)
    app.router.add_get("/api/ai/stream/{id}", handle_ai_stream)
    app.router.add_post("/api/ai/answer", handle_ai_answer)
    app.router.add_post("/api/ai/cancel", handle_ai_cancel)
    app.router.add_post("/api/sessions/create", handle_sessions_create)
    app.router.add_get("/api/sessions", handle_sessions_list)
    app.router.add_post("/api/sessions/{session_id}/answer", handle_sessions_answer)
    app.router.add_post("/api/sessions/{session_id}/cancel", handle_sessions_cancel)
    app.router.add_get("/api/sessions/stats", handle_sessions_stats)
