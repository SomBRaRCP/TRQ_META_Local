from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import settings
from app.vector import cosine


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PipelineStore:
    def __init__(self, db_path: Path | None = None, jsonl_path: Path | None = None) -> None:
        self.db_path = db_path or settings.db_path
        self.jsonl_path = jsonl_path or settings.jsonl_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        # WAL + busy_timeout permitem que dois processos (chat 7860 e pipeline
        # 8000) leiam/escrevam o mesmo arquivo SQLite sem "database is locked":
        # WAL libera leitores concorrentes durante a escrita; busy_timeout faz
        # uma escrita esperar em vez de falhar na hora se o banco estiver travado.
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Open a SQLite connection and always close it.

        sqlite3.Connection used as a context manager commits/rolls back, but it
        does not close the underlying file handle. On Windows that can keep the
        SQLite file locked after tests or temporary runs.
        """

        conn = self.connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    stim_type TEXT NOT NULL,
                    stimulus TEXT NOT NULL,
                    response TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    nqc_json TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    source TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    src_id TEXT NOT NULL,
                    dst_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    kind TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_created ON nodes(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_id)")

    def save_run(self, record: dict[str, Any]) -> str:
        node_id = record.get("id") or str(uuid.uuid4())
        record["id"] = node_id
        record.setdefault("created_at", utc_now())
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO nodes (
                    id, created_at, stim_type, stimulus, response, metrics_json,
                    nqc_json, decision_json, embedding_json, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node_id,
                    record["created_at"],
                    record["stim_type"],
                    record["stimulus"],
                    record["response"],
                    json.dumps(record["metrics"], ensure_ascii=False),
                    json.dumps(record["nqc"], ensure_ascii=False),
                    json.dumps(record["decision"], ensure_ascii=False),
                    json.dumps(record["embedding"], ensure_ascii=False),
                    record["source"],
                ),
            )
            for edge in record.get("edges", []):
                conn.execute(
                    """
                    INSERT INTO edges (id, created_at, src_id, dst_id, score, kind)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        record["created_at"],
                        node_id,
                        edge["dst_id"],
                        float(edge["score"]),
                        edge.get("kind", "coreg_similarity"),
                    ),
                )

        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return node_id

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM nodes ORDER BY created_at DESC LIMIT ?",
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [self._row_to_record(row, include_embedding=False) for row in rows]

    def get_run(self, node_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_record(row, include_embedding=True)

    def search_similar(self, embedding: list[float], limit: int = 5, exclude_id: str | None = None) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM nodes ORDER BY created_at DESC LIMIT 500").fetchall()
        scored: list[dict[str, Any]] = []
        for row in rows:
            if exclude_id and row["id"] == exclude_id:
                continue
            record = self._row_to_record(row, include_embedding=True)
            score = cosine(embedding, record.get("embedding") or [])
            if score > 0:
                record["score"] = round(score, 6)
                record.pop("embedding", None)
                scored.append(record)
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[: max(1, min(limit, 20))]

    @staticmethod
    def _row_to_record(row: sqlite3.Row, include_embedding: bool) -> dict[str, Any]:
        record = {
            "id": row["id"],
            "created_at": row["created_at"],
            "stim_type": row["stim_type"],
            "stimulus": row["stimulus"],
            "response": row["response"],
            "metrics": json.loads(row["metrics_json"]),
            "nqc": json.loads(row["nqc_json"]),
            "decision": json.loads(row["decision_json"]),
            "source": row["source"],
        }
        if include_embedding:
            record["embedding"] = json.loads(row["embedding_json"])
        return record
