"""Persistent logging of AI session events to disk.

Creates per-session log directories under {DATA_DIR}/sessions/ with:
  - meta.json         # Session metadata (created_at, events_count, summary, etc.)
  - events.jsonl      # Every event, one JSON object per line
  - transcript.md     # Human-readable formatted log with emoji prefixes

All file operations catch OSError and log via logging.warning() to avoid
disrupting the event stream.
"""
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_TRANSCRIPT_PREFIX = {
    "thought":  "> [{}] 🤔 {}\n",
    "action":   "`[{}] 🔧 {}\n`",
    "result":   "`[{}] ✅ {}\n`",
    "question": "`[{}] ❓ {}\n`",
    "done":     "`[{}] 🏁 {}\n`",
    "error":    "`[{}] ❌ {}\n`",
    "progress": "`[{}] 📊 {}\n`",
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(time_val) -> str:
    if time_val is None:
        return "--:--:--"
    if isinstance(time_val, str) and len(time_val) >= 19:
        try:
            return time_val[11:19]
        except IndexError:
            return time_val
    if isinstance(time_val, str) and len(time_val) == 8 and ":" in time_val:
        return time_val
    return str(time_val)


def _format_transcript_line(event: dict) -> str | None:
    etype = event.get("type", "")
    content = event.get("content", event.get("data", ""))
    time_str = _parse_time(event.get("timestamp", event.get("time", None)))
    template = _TRANSCRIPT_PREFIX.get(etype)
    if template is None:
        return None
    return template.format(time_str, content)


class SessionLogger:
    """Persist AI session events to disk.

    Each session gets its own directory under ``{data_dir}/sessions/``::

        {data_dir}/sessions/
        └── {timestamp}_{agent_type}_{session_id[:8]}/
            ├── meta.json
            ├── events.jsonl
            └── transcript.md

    All public methods are safe to call from asyncio code — they log warnings
    on ``OSError`` instead of raising.  No locking is needed because all
    access originates from the same event loop thread.
    """

    def __init__(self, data_dir: str | None = None):
        self._data_dir = data_dir or os.getenv("DATA_DIR", "data")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_session_log(
        self,
        session_id: str,
        agent_type: str,
        goal: str,
    ) -> str:
        """Create a new session log directory on disk.

        Parameters
        ----------
        session_id:
            Unique session identifier (e.g. from ``AISession.id``).
        agent_type:
            Short label for the agent (e.g. ``"opencode"``, ``"reflector"``).
        goal:
            The high-level goal of the session.

        Returns
        -------
        str
            The ``session_log_id`` — a short directory name that must be
            passed to subsequent calls like :meth:`write_event`.
            Format: ``{timestamp}_{agent_type}_{session_id[:8]}``.
        """
        timestamp = _iso_now()
        safe_id = session_id[:8]
        session_log_id = f"{timestamp}_{agent_type}_{safe_id}"
        safe_log_id = session_log_id.replace(":", "-")
        session_dir = os.path.join(
            self._data_dir, "sessions", safe_log_id
        )

        meta = {
            "session_log_id": safe_log_id,
            "session_id": session_id,
            "agent_type": agent_type,
            "goal": goal,
            "created_at": timestamp,
            "last_event_at": None,
            "end_time": None,
            "duration_seconds": None,
            "events_count": 0,
            "summary": None,
        }

        try:
            os.makedirs(session_dir, exist_ok=True)
            self._write_json(os.path.join(session_dir, "meta.json"), meta)
            header_lines = [
                f"# Session: {agent_type} — {goal}",
                f"**Started:** {timestamp}  |  **ID:** {session_id}",
                "",
                "---",
                "",
            ]
            transcript_path = os.path.join(session_dir, "transcript.md")
            with open(transcript_path, "w", encoding="utf-8") as fh:
                fh.writelines(line + "\n" for line in header_lines)
        except OSError:
            logger.warning(
                "Failed to create session log directory: %s", session_dir,
                exc_info=True,
            )
            return safe_log_id

        return safe_log_id

    def write_event(self, session_log_id: str, event: dict) -> None:
        """Append a single event to *events.jsonl* and *transcript.md*.

        Also updates ``meta.json`` — increments ``events_count`` and sets
        ``last_event_at``.
        """
        session_dir = self._resolve_dir(session_log_id)
        if session_dir is None:
            return

        timestamp = _iso_now()
        event_with_ts = {**event, "timestamp": timestamp}

        events_path = os.path.join(session_dir, "events.jsonl")
        try:
            with open(events_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event_with_ts, default=str) + "\n")
        except OSError:
            logger.warning(
                "Failed to write event to %s", events_path, exc_info=True,
            )

        line = _format_transcript_line(event_with_ts)
        if line is not None:
            self.write_transcript_line(session_log_id, line)

        self._update_meta(
            session_dir,
            {
                "last_event_at": timestamp,
                "events_count": ("inc", "events_count"),
            },
        )

    def write_transcript_line(self, session_log_id: str, line: str) -> None:
        """Append a single (pre-formatted) line to *transcript.md*."""
        session_dir = self._resolve_dir(session_log_id)
        if session_dir is None:
            return

        transcript_path = os.path.join(session_dir, "transcript.md")
        try:
            with open(transcript_path, "a", encoding="utf-8") as fh:
                fh.write(line)
                if not line.endswith("\n"):
                    fh.write("\n")
        except OSError:
            logger.warning(
                "Failed to write transcript line to %s",
                transcript_path,
                exc_info=True,
            )

    def finalize_session(
        self,
        session_log_id: str,
        summary: dict | None = None,
    ) -> None:
        """Mark a session as complete.

        Updates ``meta.json`` with ``end_time``, ``duration_seconds``, and
        a *summary* dict (e.g. steps taken, errors encountered, outcome).
        """
        session_dir = self._resolve_dir(session_log_id)
        if session_dir is None:
            return

        end_time = _iso_now()
        meta_path = os.path.join(session_dir, "meta.json")
        meta = self._read_json(meta_path)
        if meta is None:
            return

        created_str = meta.get("created_at")
        duration = None
        if created_str:
            try:
                created_dt = datetime.fromisoformat(created_str)
                end_dt = datetime.fromisoformat(end_time)
                duration = round((end_dt - created_dt).total_seconds(), 2)
            except (ValueError, TypeError):
                pass

        duration_str = (
            f"{duration}s" if duration is not None else "unknown"
        )
        self.write_transcript_line(
            session_log_id,
            f"\n---\n**Session ended:** {end_time}  |  "
            f"**Duration:** {duration_str}\n",
        )

        updates = {
            "end_time": end_time,
            "duration_seconds": duration,
        }
        if summary is not None:
            updates["summary"] = summary

        self._update_meta(session_dir, updates)

    def get_session_log(self, session_log_id: str) -> dict | None:
        """Read and return the metadata for a session log.

        Returns ``None`` if the directory or *meta.json* does not exist.
        """
        session_dir = self._resolve_dir(session_log_id)
        if session_dir is None:
            return None
        return self._read_json(os.path.join(session_dir, "meta.json"))

    def get_recent_sessions(self, limit: int = 10) -> list[dict]:
        """Return the *limit* most recent session logs (newest first).

        Each entry is the parsed contents of that session's ``meta.json``.
        """
        sessions_dir = os.path.join(self._data_dir, "sessions")
        try:
            entries = sorted(
                os.listdir(sessions_dir),
                reverse=True,
            )
        except FileNotFoundError:
            return []
        except OSError:
            logger.warning(
                "Failed to list sessions directory: %s",
                sessions_dir,
                exc_info=True,
            )
            return []

        result = []
        for entry in entries:
            if len(result) >= limit:
                break
            meta_path = os.path.join(sessions_dir, entry, "meta.json")
            meta = self._read_json(meta_path)
            if meta is not None:
                result.append(meta)
        return result

    def get_session_events(self, session_log_id: str) -> list[dict]:
        """Return all events from *events.jsonl* as a list of dicts.

        Reads the entire file into memory; for very large sessions consider
        reading the file incrementally instead.
        """
        session_dir = self._resolve_dir(session_log_id)
        if session_dir is None:
            return []

        events_path = os.path.join(session_dir, "events.jsonl")
        return self._read_jsonl(events_path)

    def get_session_transcript(self, session_log_id: str) -> str:
        """Return the full human-readable transcript as a single string."""
        session_dir = self._resolve_dir(session_log_id)
        if session_dir is None:
            return ""

        transcript_path = os.path.join(session_dir, "transcript.md")
        try:
            with open(transcript_path, "r", encoding="utf-8") as fh:
                return fh.read()
        except FileNotFoundError:
            return ""
        except OSError:
            logger.warning(
                "Failed to read transcript: %s",
                transcript_path,
                exc_info=True,
            )
            return ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_dir(self, session_log_id: str) -> str | None:
        candidates = [
            os.path.join(self._data_dir, "sessions", session_log_id),
        ]
        if ":" in session_log_id:
            candidates.append(
                os.path.join(
                    self._data_dir,
                    "sessions",
                    session_log_id.replace(":", "-"),
                )
            )

        for path in candidates:
            if os.path.isdir(path):
                return path

        logger.warning(
            "Session log directory not found: %s (tried: %s)",
            session_log_id,
            ", ".join(candidates),
        )
        return None

    def _write_json(self, path: str, data: dict) -> None:
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, default=str)
                fh.write("\n")
        except OSError:
            logger.warning(
                "Failed to write JSON: %s", path, exc_info=True,
            )

    def _read_json(self, path: str) -> dict | None:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError):
            logger.warning(
                "Failed to read JSON: %s", path, exc_info=True,
            )
            return None

    def _read_jsonl(self, path: str) -> list[dict]:
        results: list[dict] = []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        results.append(json.loads(stripped))
                    except json.JSONDecodeError:
                        logger.warning(
                            "Skipping invalid JSONL line in %s: %s",
                            path,
                            stripped[:120],
                        )
        except FileNotFoundError:
            pass
        except OSError:
            logger.warning(
                "Failed to read JSONL: %s", path, exc_info=True,
            )
        return results

    def _update_meta(self, session_dir: str, updates: dict) -> None:
        meta_path = os.path.join(session_dir, "meta.json")
        meta = self._read_json(meta_path)
        if meta is None:
            return

        changed = False
        for key, value in updates.items():
            if isinstance(value, tuple) and len(value) == 2 and value[0] == "inc":
                field = value[1]
                meta[field] = meta.get(field, 0) + 1
                changed = True
            else:
                if meta.get(key) != value:
                    meta[key] = value
                    changed = True

        if changed:
            self._write_json(meta_path, meta)
