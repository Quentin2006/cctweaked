"""AI session manager — spawns opencode CLI, parses output, manages lifecycle."""
import asyncio
import json
import logging
import os
import uuid
from pathlib import Path

DATA_DIR = os.getenv("DATA_DIR", "data")
SKILL_FILE = os.path.join(DATA_DIR, "skills", "turtle-control.skill.md")
MAX_STEPS = 100
IDLE_TIMEOUT = 300
SESSION_TIMEOUT = 1800

logger = logging.getLogger(__name__)


class AISession:
    def __init__(self, session_id, goal):
        self.id = session_id
        self.goal = goal
        self.proc = None
        self.step = 0
        self.events = asyncio.Queue()
        self._cancelled = False

    async def start(self):
        """Spawn opencode CLI subprocess."""
        if not os.path.exists(SKILL_FILE):
            await self.events.put(
                {"type": "error", "content": f"Skill file not found at {SKILL_FILE}"}
            )
            return

        # Verify opencode is installed
        proc = await asyncio.create_subprocess_exec(
            "which", "opencode",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()
        if proc.returncode != 0:
            await self.events.put(
                {
                    "type": "error",
                    "content": "opencode CLI not found. Install: curl -fsSL https://opencode.ai/install | bash",
                }
            )
            return

        opencode_home = os.path.join(DATA_DIR, "opencode")
        self.proc = await asyncio.create_subprocess_exec(
            "opencode", "run",
            "--format", "json",
            "--dangerously-skip-permissions",
            "--file", SKILL_FILE,
            f"goal: {self.goal}",
            stdout=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={
                **os.environ,
                "OPENCODE_HOME": opencode_home,
            },
        )

        # Read stdout in background task
        asyncio.create_task(self._read_stdout())

    async def _read_stdout(self):
        """Read JSON lines from opencode stdout."""
        while self.proc and self.proc.stdout and not self._cancelled:
            line = await self.proc.stdout.readline()
            if not line:
                break
            line = line.decode().strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            self.step += 1
            await self.events.put({**event, "session_id": self.id, "step": self.step})

            # Handle question — wait for answer (reader pauses until answer_question called)
            if event.get("type") == "question":
                pass  # CLI is blocked on stdin read — answer_question() unblocks it

        # Process ended
        await self.events.put({
            "type": "done",
            "content": "Session ended",
            "session_id": self.id,
        })

    async def answer_question(self, answer):
        """Write user's answer to CLI stdin."""
        if self.proc and self.proc.stdin:
            self.proc.stdin.write((answer + "\n").encode())
            await self.proc.stdin.drain()

    async def cancel(self):
        self._cancelled = True
        if self.proc:
            self.proc.kill()
            await self.proc.wait()

    def stream_events(self):
        """Generator for SSE streaming."""
        return self._stream()

    async def _stream(self):
        while True:
            event = await self.events.get()
            yield event
            if event.get("type") in ("done", "error"):
                break


class AISessionManager:
    def __init__(self):
        self._sessions = {}

    def create(self, goal):
        if self._sessions:
            raise RuntimeError("Session already active")
        session_id = uuid.uuid4().hex[:8]
        session = AISession(session_id, goal)
        self._sessions[session_id] = session
        return session

    def get(self, session_id):
        return self._sessions.get(session_id)

    def cancel(self, session_id):
        session = self._sessions.get(session_id)
        if session:
            asyncio.create_task(session.cancel())
            del self._sessions[session_id]

    @property
    def active(self):
        return bool(self._sessions)
