"""content-digester MCP Server — 素材消化工具"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

import content_digester  # noqa: F401 — 注册 adapter

mcp = FastMCP("content-digester", instructions="素材消化工具：将网页/论文/代码仓库/视频内容分解为结构化知识，存入 auto-kb。")


@mcp.tool()
def digest(
    identifier: str,
    source_type: Optional[str] = None,
    dry_run: bool = False,
    db_path: Optional[str] = None,
) -> str:
    """消化单个素材——获取→解析→分解→写入 auto-kb

    Args:
        identifier: 素材标识（URL / 本地路径 / ArXiv ID / YouTube ID）
        source_type: 素材类型。不传则自动检测（repo/paper/article/video）
        dry_run: 仅预览，不写入数据库
        db_path: auto-kb 数据库路径（缺省用 KNOWLEDGE_DB_PATH 或 ~/.local/share/auto-kb/knowledge/knowledge.db）
    """
    from content_digester.core.registry import get_adapter, detect
    from content_digester.writers.auto_kb import write_entries

    st = source_type or detect(identifier)
    if not st:
        return json.dumps({"error": f"Cannot detect source type for: {identifier}"}, ensure_ascii=False)

    try:
        adapter = get_adapter(st)
        entries = adapter.run(identifier)
    except Exception as e:
        return json.dumps({"error": f"Digestion failed: {e}"}, ensure_ascii=False)

    result = {
        "source_type": st,
        "identifier": identifier,
        "entry_count": len(entries),
        "entries": [
            {"type": e.type, "title": e.title, "summary": e.summary[:100]}
            for e in entries
        ],
    }

    if dry_run:
        result["status"] = "dry-run (not written)"
        return json.dumps(result, ensure_ascii=False)

    _db = Path(db_path) if db_path else None
    try:
        ids = write_entries(entries, source=identifier, db_path=_db)
        result["status"] = "written"
        result["entry_ids"] = ids
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def digest_batch(
    source_type: str,
    identifiers: list[str],
    dry_run: bool = False,
) -> str:
    """批量消化多个同类型素材

    Args:
        source_type: 素材类型（repo/paper/article/video）
        identifiers: 素材标识列表
        dry_run: 仅预览，不写入数据库
    """
    from content_digester.core.registry import get_adapter
    from content_digester.writers.auto_kb import write_entries

    adapter = get_adapter(source_type)
    results = []

    for ident in identifiers:
        try:
            entries = adapter.run(ident)
            results.append({
                "identifier": ident,
                "entry_count": len(entries),
                "entries": [{"type": e.type, "title": e.title} for e in entries],
                "status": "dry-run" if dry_run else "pending",
            })
            if not dry_run:
                ids = write_entries(entries, source=ident)
                results[-1]["status"] = "written"
                results[-1]["entry_ids"] = ids
        except Exception as e:
            results.append({
                "identifier": ident,
                "status": "error",
                "error": str(e),
            })

    return json.dumps({"processed": len(results), "results": results}, ensure_ascii=False)


@mcp.tool()
def refresh(
    db_path: Optional[str] = None,
    limit: int = 10,
) -> str:
    """处理 auto-kb 的 refresh_queue，重新消化需要刷新的知识

    Args:
        db_path: auto-kb 数据库路径
        limit: 一次最多处理多少条
    """
    import sqlite3
    from datetime import datetime, timezone

    _db = Path(db_path) if db_path else None
    from content_digester.writers.auto_kb import _get_db

    conn = _get_db(_db)
    conn.row_factory = sqlite3.Row

    # 取 pending 的刷新请求
    rows = conn.execute(
        "SELECT * FROM refresh_queue WHERE status = 'pending' ORDER BY scheduled_at ASC LIMIT ?",
        (limit,),
    ).fetchall()

    if not rows:
        conn.close()
        return json.dumps({"refreshed": 0, "message": "No pending refresh requests"}, ensure_ascii=False)

    from content_digester.writers.auto_kb import write_entries
    from content_digester.core.registry import get_adapter

    results = []
    for row in rows:
        kn_id = row["kn_id"]
        source_ref = row["source_ref"]
        source_type = row["source_type"]
        rq_id = row["id"]

        # 标记 processing
        conn.execute(
            "UPDATE refresh_queue SET status = 'processing', updated_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), rq_id),
        )
        conn.commit()

        try:
            adapter = get_adapter(source_type)
            entries = adapter.run(source_ref)
            ids = write_entries(entries, source=source_ref, db_path=_db)

            # 标记完成
            conn.execute(
                "UPDATE refresh_queue SET status = 'done', kn_id_new = ?, updated_at = ? WHERE id = ?",
                (ids[0] if ids else kn_id, datetime.now(timezone.utc).isoformat(), rq_id),
            )
            results.append({
                "refresh_queue_id": rq_id,
                "kn_id": kn_id,
                "source_ref": source_ref,
                "status": "done",
                "new_entry_count": len(ids),
            })
        except Exception as e:
            conn.execute(
                "UPDATE refresh_queue SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
                (str(e), datetime.now(timezone.utc).isoformat(), rq_id),
            )
            results.append({
                "refresh_queue_id": rq_id,
                "kn_id": kn_id,
                "source_ref": source_ref,
                "status": "failed",
                "error": str(e),
            })
        conn.commit()

    conn.close()
    return json.dumps({"refreshed": len(results), "results": results}, ensure_ascii=False)


def main():
    """作为独立 MCP Server 启动"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
