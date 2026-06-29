"""auto-kb 写入器——将知识条目写入 auto-kb 的 knowledge.db"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from content_digester.schemas.intermediate import KnowledgeEntry

DEFAULT_DB_PATH = (
    Path(os.environ.get("KNOWLEDGE_DB_PATH", ""))
    if os.environ.get("KNOWLEDGE_DB_PATH")
    else Path.home() / ".local" / "share" / "auto-kb" / "knowledge" / "knowledge.db"
)


def _get_db(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upsert_entry(
    conn: sqlite3.Connection,
    entry: KnowledgeEntry,
    source_ref: str,
    source_type: str,
) -> str:
    """写入或更新单条知识，返回 entry ID。按 title+source 去重。"""
    cursor = conn.execute(
        "SELECT id, practice_count FROM knowledge WHERE title = ? AND source = ?",
        (entry.title[:200], source_ref[:200]),
    )
    existing = cursor.fetchone()
    if existing:
        eid = existing["id"]
        conn.execute(
            "UPDATE knowledge SET practice_count = practice_count + 1, updated_at = ? WHERE id = ?",
            (_now(), eid),
        )
        return eid

    entry_id = str(uuid4())
    conn.execute(
        """INSERT INTO knowledge
        (id, type, title, summary, content, code_example, tags, roles, tasks,
         source, provenance, truth, evidence, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'staging', ?, ?, ?)""",
        (
            entry_id,
            entry.type,
            entry.title[:200],
            entry.summary[:500] if entry.summary else "",
            entry.content or "",
            getattr(entry, "code_example", "") or "",
            json.dumps(entry.tags, ensure_ascii=False),
            json.dumps(getattr(entry, "roles", []), ensure_ascii=False),
            json.dumps(getattr(entry, "tasks", []), ensure_ascii=False),
            source_ref[:200],                      # source = \u539f\u59cb\u6807\u8bc6
            "extracted",                           # provenance = content-digester \u63d0\u53d6
            getattr(entry, "evidence", "") or "",
            _now(),
            _now(),
        ),
    )
    return entry_id


def _map_relation_type(rel_type: str) -> str:
    """Map content-digester relation types to auto-kb RelationType.

    content-digester allows: references|implements|depends|contradicts|contains|derives_from
    auto-kb allows:    references|contradicts|supersedes|derives_from|extends|implements

    Mapping for incompatible types:
      - depends     \u2192 references  (dependency is a directional reference)
      - contains    \u2192 references  (composition flattened to reference)
    """
    valid = {"references", "contradicts", "supersedes", "derives_from", "extends", "implements"}
    if rel_type in valid:
        return rel_type
    # Explicit fallbacks for semantic correctness
    if rel_type == "depends":
        return "references"
    if rel_type == "contains":
        return "references"
    return "references"


def write_entries(
    entries: list[KnowledgeEntry],
    source: str = "",
    db_path: Optional[Path] = None,
) -> list[str]:
    """\u6279\u91cf\u5199\u5165\u77e5\u8bc6\u6761\u76ee\uff0c\u8fd4\u56de ID \u5217\u8868\u3002

    \u4e09\u904d\u5199\u5165\uff1a
    1. \u5148\u5199\u5165\u6240\u6709\u6761\u76ee\uff0c\u6536\u96c6 {title \u2192 id} \u6620\u5c04
    2. \u518d\u5199\u5165\u6240\u6709 relation\uff08\u786e\u4fdd\u76ee\u6807 ID \u5df2\u5b58\u5728\uff09
    3. \u5199\u5165 refresh_queue\uff08\u5185\u5bb9\u5237\u65b0\u53cd\u9988\u56de\u8def\uff09
    """
    conn = _get_db(db_path)
    title_to_id: dict[str, str] = {}
    ids: list[str] = []

    # \u4ece source \u63a8\u65ad source_type\uff08\u5199\u5165 refresh_queue \u65f6\u4f7f\u7528\uff09
    source_type = _infer_source_type(source)

    # Pass 1: \u5199\u5165\u6240\u6709\u6761\u76ee
    for entry in entries:
        eid = _upsert_entry(conn, entry, source, source_type)
        ids.append(eid)
        title_to_id[entry.title] = eid

    # Pass 2: \u5199\u5165 relations
    for entry, eid in zip(entries, ids):
        for rel in entry.relations:
            target_title = rel.get("target", "")
            target_id = title_to_id.get(target_title)
            if target_id is None:
                cursor = conn.execute(
                    "SELECT id FROM knowledge WHERE title = ? LIMIT 1",
                    (target_title,),
                )
                row = cursor.fetchone()
                if row:
                    target_id = row["id"]
            if target_id is None:
                continue

            rel_type = _map_relation_type(rel.get("type", "references"))

            conn.execute(
                """INSERT OR IGNORE INTO relations (source_kn, target_kn, rel_type, weight)
                VALUES (?, ?, ?, ?)""",
                (eid, target_id, rel_type, 1.0),
            )

    # Pass 3: \u5199\u5165 refresh_queue
    now = _now()
    for eid in ids:
        conn.execute(
            """INSERT OR IGNORE INTO refresh_queue
            (kn_id, source_ref, source_type, reason, status, created_at, scheduled_at, updated_at)
            VALUES (?, ?, ?, 'content_digested', 'pending', ?, ?, ?)""",
            (eid, source[:200], source_type, now, now, now),
        )

    conn.commit()
    conn.close()
    return ids


def _infer_source_type(source: str) -> str:
    """\u4ece source \u6807\u8bc6\u63a8\u65ad\u7d20\u6750\u7c7b\u578b"""
    sl = source.lower()
    if "arxiv" in sl:
        return "paper"
    if "youtube" in sl or "youtu.be" in sl:
        return "video"
    if "github" in sl or "gitlab" in sl:
        return "repo"
    if source.startswith("http"):
        return "article"
    return "unknown"
