# PROJECT KNOWLEDGE BASE

**Generated:** 2026-06-13
**Stack:** Python 3.11 + aiohttp + websockets / CC:Tweaked Lua 5.2 / Vanilla HTML/CSS/JS

## OVERVIEW

Web dashboard + Python backend to control a ComputerCraft:Tweaked turtle via WebSocket. The server translates HTTP requests into Lua code, sends it over WebSocket to the turtle, and streams results back.

## STRUCTURE

```
cctweaked/
├── server.py              # HTTP entry point — aiohttp routes, error handling
├── TurtleManager.py       # WebSocket server + Lua dispatch + position tracking
├── cc/
│   ├── client.lua         # Turtle-side WebSocket client (receives + executes Lua)
│   └── startup.lua        # Bootstrapper — syncs client from GitHub Gist
├── web/
│   ├── index.html         # Full dashboard — inline CSS (~1700 lines) + 5 JS files
│   ├── move.js            # D-Pad button handlers
│   ├── detect.js          # Detect button handlers
│   ├── action.js          # Dig/place/attack handlers
│   ├── inventory.js       # Inventory grid + crafting + drag-drop + fuel gauge
│   ├── visualize.js       # Three.js 3D scene (world + blocks)
│   └── blocks.txt         # Persisted block positions (CSV)
├── .github/workflows/deploy.yml  # Self-hosted deploy on push to main
├── .luarc.json            # Lua LSP config — CC:Tweaked globals
├── .sisyphus/plans/       # Architecture plans (AI control, etc.)
├── requirements.txt       # websockets + aiohttp (unpinned)
├── Dockerfile             # python:3.11-slim, single-stage
└── docker-compose.yml     # Single service, ports 3000+3001
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new API endpoint | `server.py:create_app()` | Register with `add_get`/`add_post`, use 4-step try/except chain |
| Add new turtle action | `TurtleManager.py` enum + method | Create Enum with Lua string, add async method using `execute()` |
| Change Lua protocol | `cc/client.lua` | Code-as-data — server sends Lua strings, turtle executes via `load()` |
| Modify movement logic | `TurtleManager.py:_dispatch_loop` | Queued at 0.5s intervals, position updated optimistically |
| Change dashboard layout | `web/index.html` (inline HTML) | All CSS in `<style>` block, JS in separate files |
| Add 3D rendering | `web/visualize.js` | Three.js v0.160, importmap from CDN |
| Modify CI/deploy | `.github/workflows/deploy.yml` | Self-hosted runner, `git pull + docker compose up --build` |
| Change block persistence | `web/blocks.txt` + `TurtleManager.py` | CSV format `x,y,z,name`, flat-file database |

## CODE MAP

### Python — TurtleManager.py
| Symbol | Type | Lines | Role |
|--------|------|-------|------|
| `Move` | Enum | 8-14 | Movement Lua code: forward/back/left/right/up/down |
| `Inspect` | Enum | 17-20 | Inspect Lua code: forward/up/down |
| `Action` | Enum | 23-32 | Dig/place/attack Lua code (3 directions each) |
| `Sense` | Enum | 35-42 | Detect/compare Lua code |
| `InventoryOp` | Enum | 45-54 | Item count/detail/select/transfer Lua code |
| `DropOp` | Enum | 57-61 | Drop Lua code |
| `SuckOp` | Enum | 63-66 | Suck Lua code |
| `FuelOp` | Enum | 69-72 | Fuel level/refuel Lua code |
| `EquipmentOp` | Enum | 75-85 | Equip left/right Lua code |
| `CraftOp` | Enum | 88-89 | Craft Lua code |
| `TurtleManager` | Class | 92-487 | WebSocket server, command dispatch, position tracking, all turtle ops |

### Python — server.py
| Symbol | Type | Lines | Role |
|--------|------|-------|------|
| `BLOCKS_FILE` | Constant | 5 | Path to block persistence file |
| `create_app()` | Function | 8-172 | Routes + handlers factory |
| `handle_index` | Function | 175 | Static file handler for index.html |
| `start_http()` | Function | 179-186 | Starts aiohttp on port 3001 |
| `main()` | Function | 189-196 | Entry point — starts WS + HTTP concurrently |

## CONVENTIONS

### Error handling (server.py — strict ordering)
```
except KeyError:                          → 400 "Use: ..."
except (ValueError, TypeError):           → 400 "must be ..."
except asyncio.TimeoutError:              → 504 "turtle did not respond"
except ConnectionError:                   → 503 "turtle not connected"
```
**NEVER** catch `Exception` generically. **ALWAYS** use this exact chain.

### JS API call pattern (non-module files)
```javascript
try {
  const resp = await fetch(ENDPOINT, { method:"POST", headers:{ "Content-Type":"application/json" }, body });
  const result = await resp.json();
  if (resp.ok) {
    window.flashButton(btn, true);
    window.displayResult("POST /endpoint", result, "type");
  } else {
    window.flashButton(btn, false);
    window.displayResult("POST /endpoint", { error: result.error || "HTTP "+resp.status }, "type");
  }
} catch (err) {
  window.flashButton(btn, false);
  window.displayResult("POST /endpoint", { error: err.message || "Network error" }, "type");
}
```

### Lua code-as-data
All turtle commands are raw Lua strings stored in Python enums. Parameters injected via `.format()`:
```python
FORWARD = "turtle.forward()"          # no params
TRANSFER_TO = "turtle.transferTo({target}{count})"  # format placeholders
```
Optional parameters use empty string when absent: `count_str = count if count is not None else ""`

### Position tracking
- Facing: `0=north(-Z)`, `1=east(+X)`, `2=south(+Z)`, `3=west(-X)`
- Updated **optimistically** — server updates position when command is queued, NOT when turtle confirms
- AI must use `execute()` (awaits result), NOT `move()` (queues silently)

### Direction dispatch (Python)
```python
d = direction.upper()
if d == "UP":      → .up variant
elif d == "DOWN":  → .down variant
else:              → . variant (forward default)
```

### CSS design tokens
- Easing: `--transition-bounce: 200ms cubic-bezier(0.34, 1.56, 0.64, 1)` (interactive)
- Easing: `--transition-smooth: 300ms cubic-bezier(0.4, 0, 0.2, 1)` (hover/transitions)
- Button pattern: glossy `::before` overlay, `translateY(-2px)` hover, `translateY(2px) scale(0.97)` active

### Lua diagnostics (.luarc.json)
- `missing-fields` and `undefined-field` disabled (intentional — CC:Tweaked uses dynamic tables)
- 26 CC:Tweaked globals whitelisted

## ANTI-PATTERNS

- **Empty catch/except**: `inventory.js` and `visualize.js` have 5 empty catch blocks that silently swallow errors.
- **pyright:ignore on lambda routes**: `server.py:160-164` — use async handlers instead of lambdas.
- **No `.gitignore`**: `__pycache__/` and `.env` can be committed.
- **Unpinned deps**: `requirements.txt` has no version pins — build may break on new releases.
- **No `if __name__ == "__main__"`**: `server.py` runs on import.
- **var in action.js**: Only file using `var` instead of `const`.
- **API key in plan file**: `.sisyphus/plans/ai-control-plan.md:250` has a real API key — never commit secrets.

## COMMANDS

```bash
# Run locally
pip install -r requirements.txt
python server.py

# Run with Docker
docker compose up --build
```

## NOTES

- Ports: 3000 (WebSocket to turtle), 3001 (HTTP to browser)
- No tests exist — zero test files
- Git history has non-descriptive commit messages
- The `.dockerignore` excludes `cc/` — Lua client files not in Docker image
- Blocks persisted in flat CSV (`web/blocks.txt`), not a database
- On startup, `server.py` queues 5 `turtle.up()` commands immediately
