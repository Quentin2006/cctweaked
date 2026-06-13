# Turtle Control

A real-time web dashboard for controlling a ComputerCraft: Tweaked turtle from your browser. Move, dig, place, attack, inspect blocks, manage inventory, craft items, and visualize the world in 3D.

## Architecture

```
┌─────────────────────┐     WebSocket (3000)     ┌─────────────────────┐
│  CC:Tweaked Turtle   │ ◄──────────────────────► │   Python Server     │
│  (cc/client.lua)     │    Lua code execution    │   (server.py)       │
│                      │                          │   TurtleManager.py  │
└──────────────────────┘                          └────────┬────────────┘
                                                           │ HTTP (3001)
                                                           ▼
                                                  ┌─────────────────────┐
                                                  │   Web Dashboard     │
                                                  │  (Vanilla HTML/CSS) │
                                                  │  - Movement (D-Pad) │
                                                  │  - Detect/Inspect   │
                                                  │  - Dig/Place/Attack │
                                                  │  - Inventory + Drag │
                                                  │  - Crafting         │
                                                  │  - 3D World (Three) │
                                                  │  - Fuel Gauge       │
                                                  └─────────────────────┘
```

The system has two communication channels:

- **WebSocket (port 3000)** — Lua code is sent to the turtle for execution (movement, sensing, actions, inventory). The turtle receives code as strings, compiles and runs them via `load()`, and sends back results as JSON.
- **HTTP (port 3001)** — The web dashboard communicates with the Python server via REST endpoints. The server translates HTTP requests into Lua code sent over the WebSocket.

## Quick Start

### 1. Set up the turtle

Copy `cc/client.lua` to your CC:Tweaked turtle. Edit the `SERVER_URL` at the top of the file to point to your server's IP:

```lua
local SERVER_URL = "ws://192.168.0.47:3000"
```

Run the script on the turtle. It will connect and wait for commands.

> **Tip**: If your CC:Tweaked computer has internet access, you can use `cc/startup.lua` to auto-sync client code from a GitHub Gist on boot.

### 2. Start the server

```bash
pip install -r requirements.txt
python server.py
```

The server starts on two ports:

- `3000` — WebSocket for the turtle connection
- `3001` — HTTP for the web dashboard

Open `http://localhost:3001` in your browser.

### 3. Using Docker

```bash
docker compose up --build
```

## Dashboard Features

### Movement (D-Pad)

Six directional buttons: Up, Down, Left, Right, Forward, Back. Each click sends a move command to the turtle. The turtle's position (x, y, z) and facing direction are tracked server-side.

### Detect

Inspect blocks in front, above, or below the turtle. Detected blocks are saved to `web/blocks.txt` and appear in the 3D view.

### Actions

- **Dig** — Break a block in the chosen direction
- **Place** — Place a block from the selected inventory slot
- **Attack** — Attack an entity in the chosen direction

Each action has a direction selector (Front / Up / Down).

### Inventory

A 4×4 grid showing the turtle's 16 inventory slots. Features:

- **Drag-and-drop** — Move items between slots (click and drag on desktop)
- **Slot selection** — Click a slot to select it (highlighted with cyan glow)
- **Item details** — Name and count displayed per slot

### Crafting

A 2×2 crafting grid (slots 1-4) matching CC:Tweaked's built-in crafting UI. Place items in the grid, then click **Craft** to craft the recipe.

### Fuel

A fuel gauge showing the turtle's current fuel level. Animates smoothly and pulses when fuel is low.

### 3D World

A Three.js 3D scene showing:

- Detected blocks at their world positions
- The turtle as an emerald-green model with a directional indicator
- A grid floor for spatial reference

The view updates every 3 seconds for blocks and 1.5 seconds for the turtle position.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/move` | Queue movement commands |
| `POST` | `/detect` | Inspect a block in a direction |
| `POST` | `/action` | Execute dig/place/attack |
| `GET` | `/inventory` | Get full inventory state |
| `POST` | `/inventory` | Select slot, craft, transfer, drop, suck, refuel, equip |
| `GET` | `/blocks` | Get all detected block positions |
| `GET` | `/position` | Get the turtle's current position and facing |

## Lua Client (`cc/client.lua`)

The turtle runs a Lua script that:

1. Connects to the server via WebSocket
2. Listens for incoming JSON messages with Lua code and optional request IDs
3. Executes code via `load()` inside a `pcall()` for error handling
4. Sends results back as JSON

All `turtle.*` API functions are available — dig, place, attack, detect, inspect, getItemDetail, select, transferTo, craft, refuel, equipLeft/Right, etc.

## Project Structure

```
├── server.py              # HTTP server (aiohttp) with all API endpoints
├── TurtleManager.py       # Turtle connection, command dispatch, position tracking
├── requirements.txt       # Python dependencies (aiohttp, websockets)
├── Dockerfile             # Container build
├── docker-compose.yml     # Container orchestration
├── cc/
│   ├── client.lua         # Lua WebSocket client for the turtle
│   └── startup.lua        # Auto-sync client from GitHub Gist on boot
├── web/
│   ├── index.html         # Dashboard (all CSS inline, ~2100 lines)
│   ├── move.js            # Movement button handlers
│   ├── detect.js          # Detect button handlers
│   ├── action.js          # Dig/place/attack button handlers
│   ├── inventory.js       # Inventory grid, crafting, drag-and-drop
│   ├── visualize.js       # Three.js 3D scene
│   └── blocks.txt         # Persisted block positions (x,y,z,name)
```

## Tech Stack

- **Backend**: Python 3.11, aiohttp, websockets
- **Frontend**: Vanilla HTML/CSS/JS (no frameworks)
- **3D Rendering**: Three.js (CDN, v0.160.0)
- **Turtle**: CC:Tweaked Lua 5.2
