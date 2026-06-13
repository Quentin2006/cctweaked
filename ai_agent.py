"""AI session manager — spawns opencode CLI, parses output, manages lifecycle."""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = os.getenv("DATA_DIR", "data")
SKILL_FILE = os.path.join(DATA_DIR, "skills", "turtle-control.skill.md")
MAX_STEPS = 100
IDLE_TIMEOUT = 300
SESSION_TIMEOUT = 1800

logger = logging.getLogger(__name__)

_opencode_available = None


class AISession:
    def __init__(self, session_id, goal):
        self.id = session_id
        self.goal = goal
        self.proc = None
        self.step = 0
        self.events = asyncio.Queue()
        self._cancelled = False
        self.status = "idle"
        self.created_at = datetime.now(timezone.utc).isoformat()

    async def start(self):
        """Spawn opencode CLI subprocess."""
        if not os.path.exists(SKILL_FILE):
            await self.events.put(
                {"type": "error", "content": f"Skill file not found at {SKILL_FILE}"}
            )
            self.status = "failed"
            return

        global _opencode_available
        if _opencode_available is None:
            proc = await asyncio.create_subprocess_exec(
                "which", "opencode",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()
            _opencode_available = proc.returncode == 0

        if not _opencode_available:
            await self.events.put(
                {
                    "type": "error",
                    "content": "opencode CLI not found. Install: curl -fsSL https://opencode.ai/install | bash",
                }
            )
            self.status = "failed"
            return

        opencode_home = os.path.join(DATA_DIR, "opencode")
        self.proc = await asyncio.create_subprocess_exec(
            "opencode", "run",
            f"goal: {self.goal}",
            "--format", "json",
            "--dangerously-skip-permissions",
            "--file", SKILL_FILE,
            stdout=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={
                **os.environ,
                "OPENCODE_HOME": opencode_home,
            },
        )

        self.status = "running"

        asyncio.create_task(self._read_stdout())
        asyncio.create_task(self._read_stderr())

    async def _read_stderr(self):
        try:
            while self.proc and self.proc.stderr and not self._cancelled:
                line = await self.proc.stderr.readline()
                if not line:
                    break
                text = line.decode().strip()
                if text:
                    logger.warning("Session %s stderr: %s", self.id, text)
                    await self.events.put({
                        "type": "error",
                        "content": text,
                        "session_id": self.id,
                    })
        except Exception:
            logger.exception("Session %s stderr reader error", self.id)

    async def _read_stdout(self):
        """Read JSON lines from opencode stdout."""
        try:
            while self.proc and self.proc.stdout and not self._cancelled:
                line = await self.proc.stdout.readline()
                if not line:
                    if self.proc.returncode is None:
                        try:
                            await asyncio.wait_for(self.proc.wait(), timeout=2.0)
                        except asyncio.TimeoutError:
                            pass
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

        except Exception:
            logger.exception("Session %s stdout reader error", self.id)
        finally:
            if self.status == "running":
                if self.proc and self.proc.returncode is not None and self.proc.returncode != 0:
                    self.status = "failed"
                    await self.events.put({
                        "type": "error",
                        "content": f"Session exited with code {self.proc.returncode}",
                        "session_id": self.id,
                    })
                else:
                    self.status = "completed"
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
        if self.status not in ("completed", "failed"):
            self.status = "failed"

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
    def __init__(self, max_concurrent=5):
        self._sessions = {}
        self._max_concurrent = max_concurrent

    def create(self, goal):
        if len(self._sessions) >= self._max_concurrent:
            raise RuntimeError(
                f"Max concurrent sessions ({self._max_concurrent}) reached"
            )
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

    def cancel_all(self):
        for sid in list(self._sessions.keys()):
            self.cancel(sid)

    @property
    def active(self):
        return bool(self._sessions)

    def get_active_count(self):
        return sum(
            1 for s in self._sessions.values()
            if s.status in ("running", "idle")
        )

    def _cleanup_zombies(self):
        for sid in list(self._sessions.keys()):
            session = self._sessions[sid]
            if session.status in ("completed", "failed") or (
                session.proc
                and session.proc.returncode is not None
                and session.status not in ("completed", "failed")
            ):
                del self._sessions[sid]

    def list_sessions(self, status=None):
        """Return all sessions with metadata, optionally filtered by status.

        Args:
            status: Optional status string to filter by (e.g. "running", "completed").

        Returns:
            List of dicts with session metadata.
        """
        result = []
        for sid, session in self._sessions.items():
            if status and session.status != status:
                continue
            result.append({
                "id": sid,
                "goal": session.goal,
                "status": session.status,
                "step": session.step,
                "created_at": session.created_at,
            })
        return result

    def get_stats(self):
        counts = {}
        for session in self._sessions.values():
            counts[session.status] = counts.get(session.status, 0) + 1
        return {
            "total": len(self._sessions),
            "by_status": counts,
        }
