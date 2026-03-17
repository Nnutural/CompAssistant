from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from app.crawler.schemas import KnowledgeRecord

from .schemas import DocumentSearchFilters, DocumentSearchHit


class SQLiteIndexStore:
    name = "sqlite_index_store"

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else Path(__file__).resolve().parents[2] / "data" / "local_knowledge" / "knowledge_index.sqlite3"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.fts_enabled = False
        self._initialize()

    def upsert(self, record: KnowledgeRecord) -> KnowledgeRecord:
        payload_json = json.dumps(record.model_dump(mode="json"), ensure_ascii=False)
        tags_json = json.dumps(record.tags, ensure_ascii=False)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO knowledge_records (
                    record_id,
                    doc_id,
                    title,
                    summary,
                    content_text,
                    source_type,
                    source_channel,
                    source_name,
                    implementation_status,
                    tags_json,
                    publish_time,
                    url,
                    searchable_text,
                    indexed_at,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(record_id) DO UPDATE SET
                    doc_id=excluded.doc_id,
                    title=excluded.title,
                    summary=excluded.summary,
                    content_text=excluded.content_text,
                    source_type=excluded.source_type,
                    source_channel=excluded.source_channel,
                    source_name=excluded.source_name,
                    implementation_status=excluded.implementation_status,
                    tags_json=excluded.tags_json,
                    publish_time=excluded.publish_time,
                    url=excluded.url,
                    searchable_text=excluded.searchable_text,
                    indexed_at=excluded.indexed_at,
                    payload_json=excluded.payload_json
                """,
                (
                    record.record_id,
                    record.doc_id,
                    record.title,
                    record.summary,
                    record.content_text,
                    record.source_type,
                    record.source_channel,
                    record.source_name,
                    record.implementation_status,
                    tags_json,
                    record.publish_time.isoformat() if record.publish_time else None,
                    record.url,
                    record.searchable_text,
                    record.indexed_at.isoformat(),
                    payload_json,
                ),
            )
            if self.fts_enabled:
                connection.execute("DELETE FROM knowledge_records_fts WHERE record_id = ?", (record.record_id,))
                connection.execute(
                    "INSERT INTO knowledge_records_fts (record_id, searchable_text) VALUES (?, ?)",
                    (record.record_id, record.searchable_text),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO knowledge_records_fts_fallback (record_id, searchable_text)
                    VALUES (?, ?)
                    ON CONFLICT(record_id) DO UPDATE SET searchable_text=excluded.searchable_text
                    """,
                    (record.record_id, record.searchable_text),
                )
            connection.commit()
        return record

    def search_documents(
        self,
        query: str,
        filters: DocumentSearchFilters | dict | None = None,
        top_k: int = 5,
    ) -> list[DocumentSearchHit]:
        normalized_query = str(query or "").strip()
        if not normalized_query:
            return []
        normalized_filters = filters if isinstance(filters, DocumentSearchFilters) else DocumentSearchFilters.model_validate(filters or {})
        sql_filters, sql_parameters = _build_sql_filters(normalized_filters)
        limit = max(1, int(top_k))

        with closing(self._connect()) as connection:
            if self.fts_enabled:
                rows = connection.execute(
                    f"""
                    SELECT kr.payload_json, bm25(knowledge_records_fts) AS score
                    FROM knowledge_records_fts
                    JOIN knowledge_records kr ON kr.record_id = knowledge_records_fts.record_id
                    WHERE knowledge_records_fts MATCH ? {sql_filters}
                    ORDER BY score
                    LIMIT ?
                    """,
                    (_to_fts_query(normalized_query), *sql_parameters, limit * 4),
                ).fetchall()
            else:
                rows = connection.execute(
                    f"""
                    SELECT kr.payload_json, NULL AS score
                    FROM knowledge_records_fts_fallback fts
                    JOIN knowledge_records kr ON kr.record_id = fts.record_id
                    WHERE fts.searchable_text LIKE ? {sql_filters}
                    ORDER BY kr.indexed_at DESC
                    LIMIT ?
                    """,
                    (f"%{normalized_query}%", *sql_parameters, limit * 4),
                ).fetchall()

        hits: list[DocumentSearchHit] = []
        for row in rows:
            record = _safe_load_record(row["payload_json"])
            if record is None:
                continue
            if normalized_filters.tags and not set(normalized_filters.tags).issubset(set(record.tags)):
                continue
            hits.append(
                DocumentSearchHit(
                    record_id=record.record_id,
                    doc_id=record.doc_id,
                    title=record.title,
                    summary=record.summary,
                    source_type=record.source_type,
                    source_channel=record.source_channel,
                    source_name=record.source_name,
                    implementation_status=record.implementation_status,
                    tags=list(record.tags),
                    publish_time=record.publish_time,
                    url=record.url,
                    score=float(row["score"]) if row["score"] is not None else None,
                )
            )
            if len(hits) >= limit:
                break
        return hits

    def get_document(self, record_id: str) -> KnowledgeRecord | None:
        normalized_id = str(record_id or "").strip()
        if not normalized_id:
            return None
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM knowledge_records WHERE record_id = ?",
                (normalized_id,),
            ).fetchone()
        if row is None:
            return None
        return _safe_load_record(row["payload_json"])

    def get_compatibility_notes(self) -> list[str]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT note FROM knowledge_index_compatibility ORDER BY note ASC"
            ).fetchall()
        return [str(row["note"]) for row in rows]

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_records (
                    record_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    content_text TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_channel TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    implementation_status TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    publish_time TEXT,
                    url TEXT NOT NULL,
                    searchable_text TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            _ensure_column(connection, "knowledge_records", "source_channel", "TEXT NOT NULL DEFAULT 'public_web'")
            _ensure_column(connection, "knowledge_records", "implementation_status", "TEXT NOT NULL DEFAULT 'implemented'")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_index_compatibility (
                    note TEXT PRIMARY KEY
                )
                """
            )
            try:
                connection.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_records_fts
                    USING fts5(record_id UNINDEXED, searchable_text, tokenize='unicode61')
                    """
                )
                self.fts_enabled = True
            except sqlite3.OperationalError as exc:
                self.fts_enabled = False
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS knowledge_records_fts_fallback (
                        record_id TEXT PRIMARY KEY,
                        searchable_text TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "INSERT OR IGNORE INTO knowledge_index_compatibility (note) VALUES (?)",
                    (f"FTS5 unavailable, using LIKE fallback: {exc}",),
                )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection


def _build_sql_filters(filters: DocumentSearchFilters) -> tuple[str, list[str]]:
    clauses: list[str] = []
    parameters: list[str] = []
    if filters.source_type:
        clauses.append("AND kr.source_type = ?")
        parameters.append(filters.source_type)
    if filters.source_types:
        clauses.append(f"AND kr.source_type IN ({','.join('?' for _ in filters.source_types)})")
        parameters.extend(filters.source_types)
    if filters.source_channel:
        clauses.append("AND kr.source_channel = ?")
        parameters.append(filters.source_channel)
    if filters.source_channels:
        clauses.append(f"AND kr.source_channel IN ({','.join('?' for _ in filters.source_channels)})")
        parameters.extend(filters.source_channels)
    if filters.source_name:
        clauses.append("AND kr.source_name = ?")
        parameters.append(filters.source_name)
    if filters.implementation_status:
        clauses.append("AND kr.implementation_status = ?")
        parameters.append(filters.implementation_status)
    if filters.implementation_statuses:
        clauses.append(
            f"AND kr.implementation_status IN ({','.join('?' for _ in filters.implementation_statuses)})"
        )
        parameters.extend(filters.implementation_statuses)
    return f" {' '.join(clauses)}" if clauses else "", parameters


def _to_fts_query(query: str) -> str:
    terms = [term.strip() for term in query.split() if term.strip()]
    if not terms:
        return query
    return " OR ".join(f'"{term.replace("\"", "")}"' for term in terms)


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {str(row["name"]) for row in rows}
    if column_name not in existing_columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _safe_load_record(payload_json: str) -> KnowledgeRecord | None:
    try:
        payload = json.loads(payload_json)
        return KnowledgeRecord.model_validate(payload)
    except (json.JSONDecodeError, ValidationError):
        return None
