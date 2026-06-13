# Connecting to the CC:Tweaked Container

The server runs in a Docker container on the TrueNAS server at `100.102.127.19`.

## Quick Reference

| Detail | Value |
|--------|-------|
| Server address | `100.102.127.19` |
| Web dashboard | `http://100.102.127.19:3001/` |
| WebSocket (turtle) | `ws://100.102.127.19:3000` |
| SSH host | `192.168.0.47` (TrueNAS) |
| SSH user | `root` |
| SSH key | `~/.ssh/truenas` |
| Repo path (host) | `/mnt/Safe/data/cctweaked/` |
| Container name | `cctweaked-cc-server-1` |
| Container image | `cctweaked-cc-server` |

## SSH into TrueNAS

```bash
ssh truenas
```

(Configured in `~/.ssh/config` as `root@192.168.0.47` with the `truenas` key.)

## View Container Logs

```bash
# Last 50 lines
ssh truenas 'docker logs cctweaked-cc-server-1 --tail 50'

# Follow logs in real-time
ssh truenas 'docker logs cctweaked-cc-server-1 -f'

# AI session logs (inside container)
ssh truenas 'docker exec cctweaked-cc-server-1 cat /app/data/opencode/sessions/*/opencode/log/opencode.log'
```

## Execute Commands in the Container

```bash
# Open a shell
ssh truenas 'docker exec -it cctweaked-cc-server-1 sh'

# Run a single command
ssh truenas 'docker exec cctweaked-cc-server-1 python3 -c "print(\"hello\")"'

# Check environment variables
ssh truenas 'docker exec cctweaked-cc-server-1 env | grep OPENCODE'

# Check opencode is available
ssh truenas 'docker exec cctweaked-cc-server-1 which opencode && opencode --version'
```

## Check Server Status

```bash
# Is the container running?
ssh truenas 'docker ps --filter name=cc-server'

# Resource usage
ssh truenas 'docker stats --no-stream cctweaked-cc-server-1'

# Restart the container
ssh truenas 'cd /mnt/Safe/data/cctweaked && docker compose restart'
```

## Rebuild and Deploy

```bash
# Manual deploy from the NAS
ssh truenas 'cd /mnt/Safe/data/cctweaked && \
  git pull && \
  docker compose down && \
  docker compose up -d --build'
```

## Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 3000 | WebSocket | Turtle connection (Lua execution) |
| 3001 | HTTP | Web dashboard + REST API |

## Project Layout (inside container)

```
/app/
├── server.py              # Entry point
├── server/                # Python package
│   ├── __init__.py        # App factory
│   ├── enums.py           # Turtle command enums
│   ├── turtle_manager.py  # WebSocket + Lua dispatch
│   ├── ai_agent.py        # AI session management
│   ├── task_manager.py    # Task queue
│   ├── routes_turtle.py   # Move/detect/action/inventory endpoints
│   ├── routes_ai.py       # AI session endpoints
│   ├── routes_tasks.py    # Task management endpoints
│   ├── bootstrap.py       # First-run setup
│   └── session_logger.py  # Session logging
├── web/                   # Dashboard frontend
│   ├── index.html
│   └── js/
│       ├── move.js, detect.js, action.js, inventory.js
│       ├── visualize.js, ai.js, turtles.js
│       └── blocks.txt
├── skills/                # Agent skill files
├── data/                  # Persistent data (Docker volume)
│   └── skills/turtle-control.skill.md
├── lua/                   # Turtle Lua client
└── data.defaults/         # Default files for bootstrap
```

## Troubleshooting

**"port already allocated" on deploy:**
An old container is still running. Stop it first:
```bash
ssh truenas 'docker stop <old-container-name> && docker rm <old-container-name>'
```

**AI session stuck at "init":**
Check if opencode is hanging. The fix was:
- `stdin=DEVNULL` (prevents blocking on empty stdin pipe)
- `stderr=PIPE` with background reader (prevents pipe buffer deadlock)
- `--pure` flag (disables oh-my-openagent plugin)
- Per-session `XDG_DATA_HOME` (isolates SQLite databases)

**Runner not registering:**
The GitHub Actions runner (`ix-cctweaked-runner-runner-1`) needs a valid ACCESS_TOKEN.
Update it in TrueNAS Scale app settings under Environment Variables.
