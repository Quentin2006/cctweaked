# Turtle Control

A real-time Minecraft CC:Tweaked turtle-control dashboard. A Python asyncio/aiohttp backend translates browser requests into Lua commands sent over WebSockets, while a Three.js view displays discovered blocks and turtle positions.

## Implemented features

- Movement, block inspection, digging/placing, inventory operations, crafting, and fuel controls.
- Request IDs and serialized command execution for correlating turtle replies, with disconnect handling.
- Multiple turtle connections and a browser turtle list.
- A filesystem-backed task queue with priorities, dependencies, atomic claiming, and completion/failure states.
- Optional OpenCode-driven automation sessions, with actions/results streamed to the browser using server-sent events.
- Per-session agent data directories, cancellation, and idle/session watchdogs.

These are Minecraft game turtles, not physical robots. The agent integration delegates execution to the external OpenCode CLI.

## Architecture

```text
CC:Tweaked Lua client <-> WebSocket :3000 <-> Python server
                                                  ^
                                                  | HTTP :3001 + SSE
                                                  v
                                  Browser dashboard / Three.js
```

Tasks and block positions use local files under `DATA_DIR` (default: `data/`), and OpenCode receives a separate data directory per session. The app keeps its active AI-session registry in memory; there is no database service.

## Run locally

Python 3.11 or newer is the container's baseline. Install the Python dependencies and start from the repository root:

```sh
pip install -r requirements.txt
python server.py
```

Open `http://localhost:3001`. Copy `lua/client.lua` to the CC:Tweaked turtle, configure its `SERVER_URL` for your server's WebSocket address (`ws://YOUR_SERVER:3000`), and run it in-game.

Manual controls do not require a model provider. AI sessions additionally require the OpenCode CLI, a configured provider/model compatible with the invocation in `server/ai_agent.py`, and `DATA_DIR/skills/turtle-control.skill.md`. The repository includes that skill under `data/skills/`. Keep provider credentials outside Git.

## Docker

```sh
docker compose up --build
```

Compose exposes ports 3000 and 3001 and stores runtime data in the `cc-data` volume. It accepts `OPENCODE_API_KEY` from the local environment. The current Dockerfile does not seed `data/skills/` into a fresh volume: provision `skills/turtle-control.skill.md` in that volume before starting an AI session. The basic dashboard and agent-backed execution are separate capabilities; this is not a claim that a fresh container has been validated end to end with a model or game server.

## Main API surfaces

| Surface | Purpose |
| --- | --- |
| `/move`, `/detect`, `/action`, `/inventory` | Turtle commands and inventory |
| `/blocks`, `/position`, `/api/turtles` | World and connection state |
| `/api/tasks/*` | Create, claim, complete, fail, and inspect tasks |
| `/api/ai/*`, `/api/sessions/*` | Start, stream, answer, cancel, and inspect agent sessions |

See `server/routes_turtle.py`, `server/routes_tasks.py`, and `server/routes_ai.py` for the exact methods and payloads.

## Source map

- `server.py`: guarded entry point; starts WebSocket and HTTP services.
- `server/__init__.py`: application assembly and manager creation.
- `server/turtle_manager.py`, `server/enums.py`: connections, Lua dispatch, position/inventory operations.
- `server/task_manager.py`: filesystem task lifecycle and dependency checks.
- `server/ai_agent.py`: OpenCode subprocess lifecycle and event translation.
- `server/session_logger.py`: session-persistence helper, not currently wired into the app factory.
- `server/routes_*.py`: HTTP and SSE handlers.
- `lua/`: CC:Tweaked client and optional startup helper.
- `web/index.html`, `web/js/`: dashboard, controls, agent display, and Three.js visualization.
- `data/skills/`: tracked automation instructions; other agent/session runtime data belongs outside Git.

## Validation and limitations

No automated test suite is currently tracked. A source review is not a live-model, Minecraft, or rendering-performance benchmark. Python dependencies are currently unpinned.

Run on a trusted network. The API has no authentication layer, sends executable Lua to the game clients, and can start OpenCode with unrestricted permissions. It is a personal prototype rather than an authenticated public service.

## Deployment workflow

`.github/workflows/deploy.yml` runs on pushes to `main` and manual dispatch, using a self-hosted runner to update a NAS deployment. Review that workflow before pushing or merging deployment-affecting changes. Merely cloning or reading this repository does not run it.
