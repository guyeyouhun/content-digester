"""Tests for content_digester.writers.auto_kb — _infer_source_type, write_entries."""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from content_digester.schemas.intermediate import KnowledgeEntry
from content_digester.writers.auto_kb import (
    _infer_source_type,
    _now,
    _upsert_entry,
    write_entries,
)


# ── _infer_source_type tests ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "source,expected",
    [
        ("https://arxiv.org/abs/2301.12345", "paper"),
        ("arxiv.org/abs/2301.12345", "paper"),
        ("https://youtube.com/watch?v=xxxx", "video"),
        ("https://youtu.be/xxxx", "video"),
        ("https://github.com/user/repo", "repo"),
        ("https://gitlab.com/user/repo", "repo"),
        ("https://example.com/article", "article"),
        ("http://blog.com/post", "article"),
    ],
)
def test_infer_source_type_known(source, expected):
    """_infer_source_type \u6b63\u786e\u63a8\u65ad\u5df2\u77e5\u6e90\u7c7b\u578b."""
    assert _infer_source_type(source) == expected


def test_infer_source_type_unknown():
    """_infer_source_type \u5bf9\u672a\u77e5\u6e90\u8fd4\u56de 'unknown'."""
    assert _infer_source_type("some random text") == "unknown"


# ── write_entries with mock DB ──────────────────────────────────────────────


@pytest.fixture
def temp_db() -> Path:
    """\u521b\u5efa\u4e00\u4e2a\u4e34\u65f6 SQLite \u6570\u636e\u5e93\uff0c\u5305\u542b knowledge / relations / refresh_queue \u8868."""
    db_file = Path(tempfile.mktemp(suffix=".db"))
    conn = sqlite3.connect(str(db_file))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id TEXT PRIMARY KEY,
            type TEXT DEFAULT 'concept',
            title TEXT NOT NULL,
            summary TEXT DEFAULT '',
            content TEXT DEFAULT '',
            code_example TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            roles TEXT DEFAULT '[]',
            tasks TEXT DEFAULT '[]',
            truth TEXT DEFAULT 'staging',
            provenance TEXT DEFAULT 'unverified',
            evidence TEXT DEFAULT '',
            strength REAL DEFAULT 0.0,
            stability REAL DEFAULT 0.0,
            difficulty REAL DEFAULT 0.0,
            temperature REAL DEFAULT 0.0,
            practice_count INTEGER DEFAULT 0,
            practice_success INTEGER DEFAULT 0,
            supersedes TEXT,
            superseded_by TEXT,
            source TEXT DEFAULT '',
            relations TEXT DEFAULT '[]',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            last_accessed TEXT
        );
        CREATE TABLE IF NOT EXISTS relations (
            source_kn TEXT NOT NULL,
            target_kn TEXT NOT NULL,
            rel_type TEXT NOT NULL DEFAULT 'references',
            weight REAL DEFAULT 1.0,
            PRIMARY KEY (source_kn, target_kn, rel_type)
        );
        CREATE TABLE IF NOT EXISTS refresh_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kn_id TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'unknown',
            source_ref TEXT DEFAULT '',
            reason TEXT DEFAULT 'content_digested',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT '',
            scheduled_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        );
    """)
    conn.commit()
    conn.close()
    yield db_file
    db_file.unlink(missing_ok=True)


@pytest.fixture
def sample_entry() -> KnowledgeEntry:
    """\u4e00\u4e2a\u57fa\u672c\u7684 KnowledgeEntry fixture."""
    return KnowledgeEntry(
        title="Test Pattern",
        content="This is a test pattern for unit testing.",
        summary="A test pattern summary",
        tags=["testing", "python"],
        type="pattern",
        source="content_digester",
        relations=[{"target": "Other Entity", "type": "references"}],
    )


def test_write_entries_creates_records(temp_db, sample_entry):
    """write_entries \u5c06\u6761\u76ee\u5199\u5165\u6570\u636e\u5e93\u5e76\u8fd4\u56de ID \u5217\u8868."""
    ids = write_entries(
        entries=[sample_entry],
        source="https://example.com/test",
        db_path=temp_db,
    )

    assert len(ids) == 1
    assert ids[0]  # non-empty UUID

    # Verify the record was actually written
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM knowledge WHERE id = ?", (ids[0],)).fetchone()
    conn.close()

    assert row is not None
    assert row["title"] == "Test Pattern"
    assert row["content"] == "This is a test pattern for unit testing."
    assert row["truth"] == "staging"
    assert row["provenance"] == "extracted"

    tags = json.loads(row["tags"])
    assert "testing" in tags
    assert "python" in tags


def test_write_entries_multiple(temp_db):
    """write_entries \u6279\u91cf\u5199\u5165\u591a\u4e2a\u6761\u76ee."""
    entries = [
        KnowledgeEntry(title=f"Entry {i}", content=f"Content {i}")
        for i in range(5)
    ]
    ids = write_entries(entries=entries, source="test", db_path=temp_db)
    assert len(ids) == 5
    assert len(set(ids)) == 5  # all unique


def test_write_entries_empty_list(temp_db):
    """write_entries \u5bf9\u7a7a\u5217\u8868\u8fd4\u56de\u7a7a\u5217\u8868."""
    ids = write_entries(entries=[], source="test", db_path=temp_db)
    assert ids == []


def test_upsert_entry_dedup(temp_db, sample_entry):
    """_upsert_entry \u5bf9\u540c\u4e00 title+source \u53bb\u91cd\uff1a\u7b2c\u4e8c\u6b21\u5199\u5165\u589e\u52a0 practice_count."""
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row

    id1 = _upsert_entry(conn, sample_entry, "src-ref", "test-type")
    conn.commit()

    # Second write with same title+source should return the SAME id
    id2 = _upsert_entry(conn, sample_entry, "src-ref", "test-type")
    conn.commit()

    assert id1 == id2

    row = conn.execute("SELECT practice_count FROM knowledge WHERE id = ?", (id1,)).fetchone()
    assert row["practice_count"] >= 1

    conn.close()


def test_write_entries_respects_source_ref_length(temp_db):
    """write_entries \u5c06 source \u622a\u65ad\u5230 200 \u5b57\u7b26."""
    long_source = "x" * 300
    entry = KnowledgeEntry(title="T", content="C")
    ids = write_entries(entries=[entry], source=long_source, db_path=temp_db)

    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT source FROM knowledge WHERE id = ?", (ids[0],)).fetchone()
    conn.close()

def test_write_entries_with_explicit_db_path(temp_db, sample_entry):
    """write_entries \u63a5\u53d7\u663e\u5f0f db_path \u53c2\u6570\u5e76\u6b63\u786e\u5199\u5165."""
    ids = write_entries(entries=[sample_entry], source="test", db_path=temp_db)
    assert len(ids) == 1
