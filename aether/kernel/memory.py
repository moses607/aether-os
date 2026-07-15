"""
Aether OS — Kernel: Memory Store
================================

A dependency-free, SQLite-backed memory hierarchy for agents.

Design goals:
- **Zero external dependencies** for the base tier (stdlib `sqlite3` only), so the
  kernel runs anywhere Python runs. Vector/graph tiers are optional add-ons
  (see ROADMAP) that plug in behind the same interface.
- **Namespaced** memories so multiple agents/projects share one store safely.
- **Typed** records (`kind`): `fact`, `episodic`, `decision`, `skill_result`, ...
- **Full-text recall** via SQLite FTS5 when available, with a LIKE fallback so it
  works even on minimal SQLite builds.

This is the L1 tier of the memory hierarchy described in ARCHITECTURE.md
(L1 relational/FTS here → L2 vector recall → L3 graph relations).
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass
class Memory:
    """A single memory record."""
    id: int
    namespace: str
    kind: str
    content: str
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0


class MemoryStore:
    """SQLite-backed L1 memory store with full-text recall.

    Example
    -------
    >>> store = MemoryStore(":memory:")
    >>> mid = store.remember("The launch is on Friday", kind="decision")
    >>> [m.content for m in store.recall("launch")]
    ['The launch is on Friday']
    """

    def __init__(self, path: str | Path = "aether.db") -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._fts = self._detect_fts()
        self._migrate()

    # -- setup ---------------------------------------------------------------

    def _detect_fts(self) -> bool:
        try:
            self._conn.execute("CREATE VIRTUAL TABLE _fts_probe USING fts5(x)")
            self._conn.execute("DROP TABLE _fts_probe")
            return True
        except sqlite3.OperationalError:
            return False

    def _migrate(self) -> None:
        cur = self._conn
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                namespace TEXT NOT NULL DEFAULT 'default',
                kind TEXT NOT NULL DEFAULT 'fact',
                content TEXT NOT NULL,
                meta TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ns ON memories(namespace)")
        if self._fts:
            cur.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts "
                "USING fts5(content, content='memories', content_rowid='id')"
            )
        self._conn.commit()

    # -- write ---------------------------------------------------------------

    def remember(
        self,
        content: str,
        *,
        namespace: str = "default",
        kind: str = "fact",
        meta: dict[str, Any] | None = None,
    ) -> int:
        """Store a memory and return its id."""
        if not content or not content.strip():
            raise ValueError("cannot remember empty content")
        ts = time.time()
        cur = self._conn.execute(
            "INSERT INTO memories(namespace, kind, content, meta, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (namespace, kind, content, json.dumps(meta or {}), ts),
        )
        mid = int(cur.lastrowid)
        if self._fts:
            self._conn.execute(
                "INSERT INTO memories_fts(rowid, content) VALUES (?, ?)", (mid, content)
            )
        self._conn.commit()
        return mid

    def forget(self, memory_id: int) -> None:
        self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        if self._fts:
            self._conn.execute("DELETE FROM memories_fts WHERE rowid = ?", (memory_id,))
        self._conn.commit()

    # -- read ----------------------------------------------------------------

    def recall(
        self, query: str, *, namespace: str | None = None, limit: int = 10
    ) -> list[Memory]:
        """Full-text recall (FTS5 when available, LIKE fallback otherwise)."""
        query = (query or "").strip()
        if not query:
            return []
        if self._fts:
            rows = self._conn.execute(
                "SELECT m.* FROM memories_fts f JOIN memories m ON m.id = f.rowid "
                "WHERE memories_fts MATCH ? "
                + ("AND m.namespace = ? " if namespace else "")
                + "ORDER BY rank LIMIT ?",
                (query, namespace, limit) if namespace else (query, limit),
            ).fetchall()
        else:
            like = f"%{query}%"
            rows = self._conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? "
                + ("AND namespace = ? " if namespace else "")
                + "ORDER BY created_at DESC LIMIT ?",
                (like, namespace, limit) if namespace else (like, limit),
            ).fetchall()
        return [self._row(r) for r in rows]

    def get(self, memory_id: int) -> Memory | None:
        r = self._conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        return self._row(r) if r else None

    def all(self, *, namespace: str | None = None, limit: int = 100) -> list[Memory]:
        if namespace:
            rows = self._conn.execute(
                "SELECT * FROM memories WHERE namespace = ? ORDER BY created_at DESC LIMIT ?",
                (namespace, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row(r) for r in rows]

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0])

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _row(r: sqlite3.Row) -> Memory:
        return Memory(
            id=int(r["id"]),
            namespace=r["namespace"],
            kind=r["kind"],
            content=r["content"],
            meta=json.loads(r["meta"]),
            created_at=float(r["created_at"]),
        )

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
