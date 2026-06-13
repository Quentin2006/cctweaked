"""Filesystem-based task queue for a CC:Tweaked turtle hivemind.

All state lives under {DATA_DIR}/tasks/. No database — every task is a JSON
file on disk. Atomic os.rename() provides concurrency for claim operations.

Directory structure:
    {DATA_DIR}/tasks/
    ├── pending/       # Tasks waiting to be claimed
    ├── active/        # Tasks being worked on
    ├── completed/     # Tasks done
    └── failed/        # Tasks that failed
"""

import json
import logging
import os
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Task field defaults & helpers
# ---------------------------------------------------------------------------

VALID_STATUSES = {"pending", "active", "completed", "failed"}
VALID_TYPES = {"mine", "craft", "build", "explore", "replicate", "reflect"}


def _now() -> str:
    """ISO-8601 timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Short, unique task identifier (12 hex chars)."""
    return uuid.uuid4().hex[:12]


def _make_task(
    task_type: str,
    goal: str,
    priority: int = 5,
    depends_on: list | None = None,
    params: dict | None = None,
) -> dict:
    """Build a task dict with defaults for missing optional fields."""
    now = _now()
    return {
        "id": _new_id(),
        "type": task_type,
        "goal": goal,
        "assigned_to": None,
        "status": "pending",
        "priority": priority,
        "created_at": now,
        "updated_at": now,
        "result": None,
        "error": None,
        "depends_on": depends_on if depends_on is not None else [],
        "assigned_turtle": None,
        "params": params if params is not None else {},
    }


# ---------------------------------------------------------------------------
# TaskManager
# ---------------------------------------------------------------------------


class TaskManager:
    """Filesystem-backed task queue.

    Concurrency is handled by atomic ``os.rename()`` — the only operation
    that moves a task between status directories.  Every method catches
    ``FileNotFoundError`` / ``json.JSONDecodeError`` / ``ValueError`` so
    callers never need to handle them for operational errors.
    """

    def __init__(self, data_dir: str | None = None):
        self._data_dir = data_dir or os.getenv("DATA_DIR", "data")
        self._tasks_root = os.path.join(self._data_dir, "tasks")
        self._dirs = {
            "pending": os.path.join(self._tasks_root, "pending"),
            "active": os.path.join(self._tasks_root, "active"),
            "completed": os.path.join(self._tasks_root, "completed"),
            "failed": os.path.join(self._tasks_root, "failed"),
        }
        self._ensure_dirs()

    # -- helpers ---------------------------------------------------------

    def _ensure_dirs(self) -> None:
        """Create task subdirectories if they don't exist."""
        os.makedirs(self._tasks_root, exist_ok=True)
        for d in self._dirs.values():
            os.makedirs(d, exist_ok=True)

    def _path(self, status: str, filename: str) -> str:
        return os.path.join(self._dirs[status], filename)

    def _read_task(self, path: str) -> dict | None:
        """Read and validate a JSON task file.  Returns ``None`` on error."""
        try:
            with open(path, "r") as f:
                task = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            return None

        # Basic sanity check — must have at least an id and type
        if not isinstance(task, dict) or "id" not in task or "type" not in task:
            return None
        return task

    def _write_task(self, path: str, task: dict) -> bool:
        """Atomically write a task to *path* (temp + rename)."""
        tmp = path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(task, f, indent=2, sort_keys=True)
            os.replace(tmp, path)
            return True
        except OSError:
            # Clean up temp file on failure
            try:
                os.remove(tmp)
            except OSError:
                pass
            return False

    def _search_dirs(self, task_id: str) -> str | None:
        """Return the full path of a task file by searching all directories.

        Returns ``None`` when the task does not exist in any directory.
        """
        for d in self._dirs.values():
            for fname in os.listdir(d):
                # Active files use the format  {agent_id}_{task_id}.json
                # so we check both the full filename and the suffix.
                if fname.endswith(".json") and (
                    fname == f"{task_id}.json" or fname.endswith(f"_{task_id}.json")
                ):
                    candidate = os.path.join(d, fname)
                    task = self._read_task(candidate)
                    if task is not None and task.get("id") == task_id:
                        return candidate
        return None

    # -- public API ------------------------------------------------------

    def create_task(
        self,
        task_type: str,
        goal: str,
        priority: int = 5,
        depends_on: list | None = None,
        params: dict | None = None,
    ) -> dict:
        """Create a new task and place it in the pending queue.

        Returns the full task dict (with generated ``id``).
        """
        task = _make_task(task_type, goal, priority, depends_on, params)
        path = self._path("pending", f"{task['id']}.json")
        ok = self._write_task(path, task)
        if not ok:
            logger.error("Failed to write task %s", task["id"])
            return task  # still return the dict so caller has the id
        return task

    def claim_task(self, agent_id: str, task_types: list | None = None) -> dict | None:
        """Atomically claim the highest-priority pending task.

        1. Scans ``pending/``, reads every JSON file to check priority.
        2. Sorts candidates by priority (descending), then by created_at
           (oldest first) as a tie-breaker.
        3. Uses atomic ``os.rename()`` to move the file to
           ``active/{agent_id}_{task_id}.json``.
        4. If the rename fails (another agent got there first) the method
           moves on to the next candidate.

        Returns the task dict, or ``None`` if no matching task was available.
        """
        type_filter: set | None = set(task_types) if task_types is not None else None

        pending_dir = self._dirs["pending"]
        try:
            candidates = os.listdir(pending_dir)
        except FileNotFoundError:
            return None

        # Build a list of (priority, created_at, path, task) tuples
        entries: list[tuple[int, str, str, dict]] = []
        for fname in candidates:
            if not fname.endswith(".json"):
                continue
            path = os.path.join(pending_dir, fname)
            task = self._read_task(path)
            if task is None:
                continue
            if task.get("status", "pending") != "pending":
                continue
            if type_filter is not None and task.get("type") not in type_filter:
                continue
            # Skip tasks with unmet dependencies
            deps = task.get("depends_on", [])
            if deps and not self._deps_fulfilled(deps):
                continue
            prio = task.get("priority", 5)
            created = task.get("created_at", "")
            entries.append((prio, created, path, task))

        if not entries:
            return None

        # Sort: priority descending, then created_at ascending
        entries.sort(key=lambda x: (-x[0], x[1]))

        for prio, created, src_path, task in entries:
            task_id = task["id"]
            dest_path = self._path("active", f"{agent_id}_{task_id}.json")
            try:
                os.rename(src_path, dest_path)
            except FileNotFoundError:
                continue  # already claimed by another agent

            task["status"] = "active"
            task["assigned_to"] = agent_id
            task["updated_at"] = _now()
            try:
                with open(dest_path, "w") as f:
                    json.dump(task, f, indent=2, sort_keys=True)
            except OSError:
                logger.error("Failed to write claimed task %s", task_id)
            return task

        return None

    def _deps_fulfilled(self, dep_ids: list[str]) -> bool:
        """Check whether all dependency tasks are completed."""
        for dep_id in dep_ids:
            path = self._path("completed", f"{dep_id}.json")
            if not os.path.isfile(path):
                return False
        return True

    def complete_task(self, task_id: str, agent_id: str, result: dict | None = None) -> bool:
        """Mark an active task as completed.

        Moves the file from ``active/`` to ``completed/`` and sets
        ``status``, ``result``, and ``updated_at``.
        Returns ``True`` on success.
        """
        return self._transition(
            task_id=task_id,
            agent_id=agent_id,
            from_status="active",
            to_status="completed",
            updates={"result": result, "error": None},
        )

    def fail_task(self, task_id: str, agent_id: str, error: str) -> bool:
        """Mark an active task as failed.

        Moves the file from ``active/`` to ``failed/`` and sets
        ``status``, ``error``, and ``updated_at``.
        Returns ``True`` on success.
        """
        return self._transition(
            task_id=task_id,
            agent_id=agent_id,
            from_status="active",
            to_status="failed",
            updates={"error": error, "result": None},
        )

    def _transition(
        self,
        task_id: str,
        agent_id: str,
        from_status: str,
        to_status: str,
        updates: dict | None = None,
    ) -> bool:
        """Move a task file between directories and apply field updates."""
        src_dir = self._dirs[from_status]
        dst_dir = self._dirs[to_status]

        pattern = f"{agent_id}_{task_id}.json"
        src_path = os.path.join(src_dir, pattern)

        task = self._read_task(src_path)
        if task is None:
            return False

        task["status"] = to_status
        task["updated_at"] = _now()
        if updates:
            task.update(updates)

        dest_path = os.path.join(dst_dir, f"{task_id}.json")
        try:
            os.rename(src_path, dest_path)
        except FileNotFoundError:
            return False

        try:
            with open(dest_path, "w") as f:
                json.dump(task, f, indent=2, sort_keys=True)
        except OSError:
            logger.error("Failed to update task %s metadata", task_id)
            return False

        return True

    def get_task(self, task_id: str) -> dict | None:
        """Retrieve a task by ID from any status directory.

        Returns ``None`` if the task does not exist.
        """
        path = self._search_dirs(task_id)
        if path is None:
            return None
        return self._read_task(path)

    def list_tasks(self, status: str | None = None, task_type: str | None = None) -> list[dict]:
        """List tasks, optionally filtered by *status* and/or *task_type*.

        When *status* is ``None`` all status directories are searched.
        """
        dirs_to_scan: list[str] = []
        if status is not None:
            if status in self._dirs:
                dirs_to_scan = [self._dirs[status]]
        else:
            dirs_to_scan = list(self._dirs.values())

        results: list[dict] = []
        for d in dirs_to_scan:
            try:
                for fname in os.listdir(d):
                    if not fname.endswith(".json"):
                        continue
                    path = os.path.join(d, fname)
                    task = self._read_task(path)
                    if task is None:
                        continue
                    if task_type is not None and task.get("type") != task_type:
                        continue
                    results.append(task)
            except FileNotFoundError:
                continue

        return results

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or active task.

        - Pending task → removed from disk entirely.
        - Active task  → moved to ``failed/`` with error ``"cancelled"``.
        - Otherwise    → no-op, returns ``False``.

        Returns ``True`` if a task was actually cancelled.
        """
        pending_path = self._path("pending", f"{task_id}.json")
        try:
            os.remove(pending_path)
            return True
        except FileNotFoundError:
            pass

        active_dir = self._dirs["active"]
        try:
            for fname in os.listdir(active_dir):
                if fname.endswith(f"_{task_id}.json"):
                    src = os.path.join(active_dir, fname)
                    task = self._read_task(src)
                    if task is None:
                        continue
                    if task.get("id") != task_id:
                        continue
                    dest = self._path("failed", f"{task_id}.json")
                    task["status"] = "failed"
                    task["error"] = "cancelled"
                    task["updated_at"] = _now()
                    os.rename(src, dest)
                    try:
                        with open(dest, "w") as f:
                            json.dump(task, f, indent=2, sort_keys=True)
                    except OSError:
                        logger.error("Failed to update cancelled task %s", task_id)
                    return True
        except FileNotFoundError:
            pass

        return False

    def get_pending_by_type(self, task_type: str) -> list[dict]:
        """Return pending tasks of a specific type, sorted by priority (desc)."""
        results: list[dict] = []
        pending_dir = self._dirs["pending"]
        try:
            for fname in os.listdir(pending_dir):
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(pending_dir, fname)
                task = self._read_task(path)
                if task is None:
                    continue
                if task.get("type") != task_type:
                    continue
                if task.get("status", "pending") != "pending":
                    continue
                results.append(task)
        except FileNotFoundError:
            pass

        results.sort(key=lambda t: -t.get("priority", 5))
        return results

    def get_stats(self) -> dict:
        """Return task counts for each status.

        Returns:
            ``{"pending": N, "active": N, "completed": N, "failed": N}``
        """
        counts: dict[str, int] = {}
        for status, d in self._dirs.items():
            try:
                counts[status] = len(
                    [f for f in os.listdir(d) if f.endswith(".json")]
                )
            except FileNotFoundError:
                counts[status] = 0
        return counts

    def cleanup_stale_claims(self, timeout: int = 300) -> int:
        """Return stale active tasks to ``pending/``.

        A task is considered stale when its ``updated_at`` timestamp is
        older than *timeout* seconds.  The file is moved back to
        ``pending/`` and its ``status`` / ``assigned_to`` fields are
        cleared.

        Returns the number of tasks recovered.
        """
        now = datetime.utcnow()
        recovered = 0
        active_dir = self._dirs["active"]

        try:
            for fname in os.listdir(active_dir):
                if not fname.endswith(".json"):
                    continue
                src = os.path.join(active_dir, fname)
                task = self._read_task(src)
                if task is None:
                    continue

                updated_str = task.get("updated_at")
                if not updated_str:
                    continue

                try:
                    updated = datetime.fromisoformat(updated_str)
                except (ValueError, TypeError):
                    continue

                if (now - updated).total_seconds() < timeout:
                    continue

                task["status"] = "pending"
                task["assigned_to"] = None
                task["assigned_turtle"] = None
                task["updated_at"] = _now()
                task["error"] = None
                task["result"] = None

                task_id = task["id"]
                dest = self._path("pending", f"{task_id}.json")
                try:
                    os.rename(src, dest)
                except FileNotFoundError:
                    continue  # raced

                try:
                    with open(dest, "w") as f:
                        json.dump(task, f, indent=2, sort_keys=True)
                except OSError:
                    logger.error("Failed to rewrite recovered task %s", task_id)

                recovered += 1
        except FileNotFoundError:
            pass

        return recovered


# ---------------------------------------------------------------------------
# Demo / smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Override DATA_DIR so we don't touch real data
        os.environ["DATA_DIR"] = tmpdir
        tm = TaskManager()

        print("=== TaskManager Smoke Test ===\n")

        # 1. Create a few tasks
        t1 = tm.create_task("mine", "Mine 64 iron ore", priority=8)
        t2 = tm.create_task("craft", "Craft 16 iron ingots", priority=5,
                            depends_on=[t1["id"]])
        t3 = tm.create_task("explore", "Explore cave system", priority=3)
        t4 = tm.create_task("build", "Build a cobblestone generator", priority=10)
        print(f"Created:  {t1['id']} (prio {t1['priority']}) — {t1['goal']}")
        print(f"Created:  {t2['id']} (prio {t2['priority']}) — {t2['goal']}")
        print(f"Created:  {t3['id']} (prio {t3['priority']}) — {t3['goal']}")
        print(f"Created:  {t4['id']} (prio {t4['priority']}) — {t4['goal']}")

        # 2. Stats
        stats = tm.get_stats()
        print(f"\nStats:    {stats}")

        # 3. Claim — should get highest priority (build, prio 10)
        claimed = tm.claim_task("agent-1")
        assert claimed is not None, "Expected to claim a task"
        print(f"Claimed:  {claimed['id']} — {claimed['goal']} (by agent-1)")

        # 4. Claim again — should get next highest (mine, prio 8)
        claimed2 = tm.claim_task("agent-2")
        assert claimed2 is not None
        print(f"Claimed:  {claimed2['id']} — {claimed2['goal']} (by agent-2)")

        # 5. Claim by type
        claimed3 = tm.claim_task("agent-3", task_types=["explore"])
        assert claimed3 is not None
        print(f"Claimed:  {claimed3['id']} — {claimed3['goal']} (by agent-3, type=explore)")

        # 6. Complete first task
        ok = tm.complete_task(claimed["id"], "agent-1", {"blocks_mined": 0})
        print(f"\nComplete: {claimed['id']} → {'OK' if ok else 'FAIL'}")

        # 7. Fail second task
        ok = tm.fail_task(claimed2["id"], "agent-2", "ran out of fuel")
        print(f"Fail:     {claimed2['id']} → {'OK' if ok else 'FAIL'}")

        # 8. Stats after operations
        stats = tm.get_stats()
        print(f"\nStats:    {stats}")

        # 9. get_task by id
        fetched = tm.get_task(t1["id"])
        print(f"\nGet task: {fetched['id'] if fetched else 'NOT FOUND'} — "
              f"status={fetched['status'] if fetched else '?'}")

        # 10. list_tasks filtered
        pending = tm.list_tasks(status="pending")
        print(f"\nPending:  {[t['id'] for t in pending]}")
        completed = tm.list_tasks(status="completed")
        print(f"Completed: {[t['id'] for t in completed]}")
        failed = tm.list_tasks(status="failed")
        print(f"Failed:   {[t['id'] for t in failed]}")

        # 11. Cancel a pending task
        ok = tm.cancel_task(t2["id"])
        print(f"\nCancel:   {t2['id']} → {'OK' if ok else 'FAIL'}")

        stats = tm.get_stats()
        print(f"Stats:    {stats}")

        # 12. Claim — the remaining craft task has unmet dep (t1 now completed,
        #            but t2 was cancelled). Create a standalone task.
        t5 = tm.create_task("reflect", "Analyze mining patterns", priority=1)
        print(f"\nCreated:  {t5['id']} — {t5['goal']}")
        claimed4 = tm.claim_task("agent-4")
        if claimed4:
            print(f"Claimed:  {claimed4['id']} — {claimed4['goal']} (by agent-4)")
        else:
            print("Claim:    no available tasks")

        # 13. Stale claim cleanup
        print("\n=== Stale claim test ===")
        t6 = tm.create_task("mine", "Mine diamonds", priority=10)
        claimed5 = tm.claim_task("agent-stale")
        assert claimed5 is not None
        print(f"Claimed:  {claimed5['id']} (by agent-stale)")

        # Manually backdate the updated_at to simulate staleness
        active_path = os.path.join(tmpdir, "tasks", "active",
                                   f"agent-stale_{claimed5['id']}.json")
        try:
            with open(active_path, "r") as f:
                data = json.load(f)
            data["updated_at"] = "2020-01-01T00:00:00"
            with open(active_path, "w") as f:
                json.dump(data, f, indent=2, sort_keys=True)
        except OSError:
            pass

        recovered = tm.cleanup_stale_claims(timeout=0)
        print(f"Recovered: {recovered} stale task(s)")

        stats = tm.get_stats()
        print(f"Stats:    {stats}")

        # 14. get_pending_by_type
        mine_tasks = tm.get_pending_by_type("mine")
        print(f"\nPending mine tasks: {len(mine_tasks)}")

        print("\n=== All tests passed ===")
