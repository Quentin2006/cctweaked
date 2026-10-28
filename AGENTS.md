# Repository Guidelines

## Project and current layout

Turtle Control is a Minecraft CC:Tweaked dashboard with an asyncio/aiohttp Python backend, WebSocket Lua clients, a vanilla JavaScript/Three.js frontend, and optional external OpenCode sessions. It controls game turtles, not physical hardware.

- `server.py` is the guarded startup entry point.
- `server/__init__.py` assembles the app and managers.
- `server/turtle_manager.py` owns WebSocket connections, command correlation, and turtle operations; enums live in `server/enums.py`.
- `server/task_manager.py` owns file-backed task priorities, dependencies, claims, and state transitions.
- `server/ai_agent.py` owns OpenCode subprocess sessions, event translation, cancellation, and watchdogs.
- `server/routes_turtle.py`, `server/routes_tasks.py`, and `server/routes_ai.py` register HTTP/SSE routes.
- `server/session_logger.py` provides a persistence helper; it is not currently wired into the app factory.
- `web/index.html` and `web/js/` contain the dashboard and Three.js view.
- `lua/client.lua` is the CC:Tweaked client; `lua/startup.lua` is an optional startup helper.
- `data/skills/turtle-control.skill.md` is tracked automation guidance. Tasks, sessions, logs, model state, and local credentials are runtime data.

The older single-file `TurtleManager.py` and `cc/` paths are not the current layout. Follow the source rather than stale line-number references.

## Development and validation

```sh
pip install -r requirements.txt
python server.py
```

Starting the app opens services on ports 3000/3001. It is not a passive syntax check. Do not start model-backed sessions, game actions, or a NAS deployment as part of a read-only review.

There is no tracked automated test suite or configured linter/formatter. For a syntax-only check without running application code:

```sh
python -m compileall -q server.py server
```

Report exactly what was checked. Syntax validation does not establish live Minecraft control, model behavior, or rendering performance.

## Code conventions

- Keep asynchronous socket, subprocess, and HTTP work in the existing async APIs.
- Preserve request-ID correlation and the execution lock when changing command dispatch.
- Use `execute()` when a caller needs a confirmed reply; queued movement and optimistic position updates are different contracts.
- Keep task claims and transitions consistent with the status directories and agent ownership naming.
- Preserve the routes' JSON response shapes and HTTP error semantics.
- Keep frontend modules under `web/js/`; classic scripts depend on the helpers defined by `web/index.html`.
- New errors should be logged or surfaced; do not copy silent catches merely because older code has them.

## Runtime data and credentials

Do not commit `.env` files, provider credentials, session transcripts, task state, or OpenCode data. Ignore rules protect the default runtime paths; custom `DATA_DIR` paths need the same care. The tracked skill is source, not a credential store.

The API currently lacks authentication and can execute Lua and launch unrestricted external agent processes. Do not describe it as a hardened public service or a sandbox.

## Deployment

`.github/workflows/deploy.yml` is an active self-hosted NAS deployment on pushes to `main` and manual dispatch. Review its trigger and deployment effect before pushing or merging. Prepare changes on a branch and avoid triggering deployment while doing portfolio/documentation review.
