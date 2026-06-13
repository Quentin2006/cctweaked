# Tester Skill — Turtle Control API Testing

You are a QA agent for the CC:Tweaked turtle control system.
You test the HTTP API at http://localhost:3001 (or the remote host).

## Prerequisites

- Python 3.11+ with `aiohttp` and `websockets`
- Server running (`python server.py` or Docker)
- Turtle connected via WebSocket on port 3000 (optional — some tests work without)

## Quick Test — Server Health

```bash
# Server responds
curl -s http://localhost:3001/ | head -5

# Position endpoint (no turtle needed)
curl -s http://localhost:3001/position

# Blocks endpoint (no turtle needed)
curl -s http://localhost:3001/blocks
```

## Movement Tests (need turtle)

```bash
# Move forward one step
curl -s -X POST http://localhost:3001/move \
  -H "Content-Type: application/json" \
  -d '{"direction":"FORWARD","distance":1}'

# Move up
curl -s -X POST http://localhost:3001/move \
  -H "Content-Type: application/json" \
  -d '{"direction":"UP","distance":1}'
```

Expected: `{"status":"queued"}`

## Sensing Tests (need turtle)

```bash
# Detect block in front
curl -s -X POST http://localhost:3001/detect \
  -H "Content-Type: application/json" \
  -d '{"direction":"FORWARD"}'

# Inspect up
curl -s -X POST http://localhost:3001/detect \
  -H "Content-Type: application/json" \
  -d '{"direction":"UP"}'
```

Expected: `{"block":"minecraft:stone"}` or `{"block":null}`

## Action Tests (need turtle)

```bash
# Dig forward
curl -s -X POST http://localhost:3001/action \
  -H "Content-Type: application/json" \
  -d '{"type":"dig","direction":"forward"}'

# Place block from selected slot
curl -s -X POST http://localhost:3001/action \
  -H "Content-Type: application/json" \
  -d '{"type":"place","direction":"forward"}'
```

Expected: `{"ok":true}` or `{"ok":false}`

## Inventory Tests (need turtle)

```bash
# Get full inventory state
curl -s http://localhost:3001/inventory

# Select slot 3
curl -s -X POST http://localhost:3001/inventory \
  -H "Content-Type: application/json" \
  -d '{"type":"select","slot":3}'

# Craft (uses slots 1-4)
curl -s -X POST http://localhost:3001/inventory \
  -H "Content-Type: application/json" \
  -d '{"type":"craft","limit":64}'

# Drop items forward
curl -s -X POST http://localhost:3001/inventory \
  -H "Content-Type: application/json" \
  -d '{"type":"drop","direction":"forward","count":1}'
```

## AI Control Tests (no turtle needed for init)

```bash
# Start AI session (will run opencode CLI)
curl -s -X POST http://localhost:3001/api/ai/session \
  -H "Content-Type: application/json" \
  -d '{"goal":"say hello"}'

# Response contains session_id, then connect to SSE stream:
# GET /api/ai/stream/{session_id}

# Cancel session
curl -s -X POST http://localhost:3001/api/ai/cancel \
  -H "Content-Type: application/json" \
  -d '{"session_id":"YOUR_SESSION_ID"}'
```

## Error Case Tests

```bash
# Missing direction → 400
curl -s -X POST http://localhost:3001/move \
  -H "Content-Type: application/json" \
  -d '{}'

# Invalid direction → 400
curl -s -X POST http://localhost:3001/move \
  -H "Content-Type: application/json" \
  -d '{"direction":"DIAGONAL","distance":1}'

# Invalid distance → 400
curl -s -X POST http://localhost:3001/move \
  -H "Content-Type: application/json" \
  -d '{"direction":"FORWARD","distance":-1}'

# Unknown action type → 400
curl -s -X POST http://localhost:3001/action \
  -H "Content-Type: application/json" \
  -d '{"type":"fly"}'

# Missing goal → 400
curl -s -X POST http://localhost:3001/api/ai/session \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Test Categories

| Category | Requires Turtle | Endpoints |
|----------|---------------|-----------|
| Health | No | GET /, GET /position, GET /blocks |
| Movement | Yes | POST /move |
| Sensing | Yes | POST /detect |
| Actions | Yes | POST /action |
| Inventory | Yes | GET /inventory, POST /inventory |
| AI | No* | POST /api/ai/session, GET /api/ai/stream/{id} |
| Errors | No | Various malformed requests |

*AI session starts opencode which requires the API key env var.

## Test Procedure

1. **Basic health check** — verify server is running
2. **Error handling** — verify 400/503/504 responses
3. **Functional tests** — verify operations work (if turtle is available)
4. **AI flow** — verify session creation and SSE streaming
