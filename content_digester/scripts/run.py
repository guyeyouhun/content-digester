"""CLI 入口——运行 adapter 管线"""
from __future__ import annotations

import argparse
import sys

import content_digester  # noqa: F401 — 触发 adapter 注册


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="content-digester: 素材→结构化知识→auto-kb")
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    run_p = sub.add_parser("run", help="处理单个素材")
    run_p.add_argument("source_type", nargs="?", default=None,
                       choices=["repo", "paper", "article", "video"],
                       help="素材类型（缺省自动检测）")
    run_p.add_argument("identifier", help="素材标识（URL/路径/ID）")
    run_p.add_argument("--dry-run", action="store_true", help="仅打印，不写入 auto-kb")

    # batch
    batch_p = sub.add_parser("batch", help="批量处理素材（需指定类型）")
    batch_p.add_argument("source_type", choices=["repo", "paper", "article", "video"])
    batch_p.add_argument("file", help="每行一个标识的文本文件")
    batch_p.add_argument("--dry-run", action="store_true")

    # serve — MCP Server
    serve_p = sub.add_parser("serve", help="启动 MCP Server（stdio 模式）")
    serve_p.add_argument("--db-path", help="auto-kb 数据库路径")

    # refresh
    refresh_p = sub.add_parser("refresh", help="处理 refresh_queue 刷新请求")
    refresh_p.add_argument("--limit", type=int, default=10, help="一次处理上限")
    refresh_p.add_argument("--db-path", help="auto-kb 数据库路径")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "serve":
        _handle_serve(args.db_path)
    elif args.command == "refresh":
        _handle_refresh(args.limit, args.db_path)
    elif args.command == "run":
        _handle_run(args.source_type, args.identifier, args.dry_run)
    elif args.command == "batch":
        _handle_batch(args.source_type, args.file, args.dry_run)


def _handle_serve(db_path: str | None = None):
    """以 MCP Server 模式启动"""
    from content_digester.scripts.mcp_server import main as mcp_main

    if db_path:
        import os
        os.environ["KNOWLEDGE_DB_PATH"] = db_path

    print("[content-digester] Starting MCP server (stdio)...", file=sys.stderr)
    mcp_main()


def _handle_refresh(limit: int = 10, db_path: str | None = None):
    """处理 refresh_queue"""
    import json
    from content_digester.scripts.mcp_server import refresh as refresh_tool

    import os
    if db_path:
        os.environ["KNOWLEDGE_DB_PATH"] = db_path

    result = json.loads(refresh_tool(db_path=db_path, limit=limit))
    if result["refreshed"] == 0:
        print(result.get("message", "No pending requests"))
        return

    for r in result["results"]:
        status_icon = "\u2713" if r["status"] == "done" else "\u2717"
        src = r.get("source_ref") or r.get("kn_id", "?")
        print(f"  {status_icon} {src} \u2192 {r['status']}")
        if r.get("new_entry_count"):
            print(f"      {r['new_entry_count']} entries written")
        if r.get("error"):
            print(f"      error: {r['error']}")


def _resolve_source_type(source_type: str | None, identifier: str) -> str:
    if source_type:
        return source_type
    from content_digester.core.registry import detect

    detected = detect(identifier)
    if not detected:
        print(f"Could not auto-detect source type for: {identifier}")
        print("Available types: repo, paper, article, video")
        sys.exit(1)
    print(f"  [auto-detect] \u2192 {detected}")
    return detected


def _handle_run(source_type: str | None, identifier: str, dry_run: bool = False):
    st = _resolve_source_type(source_type, identifier)
    from content_digester.core.registry import get_adapter
    from content_digester.writers.auto_kb import write_entries

    adapter = get_adapter(st)
    print(f"[{st}] Fetching: {identifier}")
    entries = adapter.run(identifier)

    print(f"  \u2192 {len(entries)} knowledge entries extracted")
    for e in entries:
        print(f"    - {e.type}: {e.title}")

    if dry_run:
        print("  [dry-run] skipping auto-kb write")
        return

    ids = write_entries(entries, source=identifier)
    print(f"  \u2192 Written to auto-kb: {len(ids)} entries")
    for eid, entry in zip(ids, entries):
        print(f"    - {entry.title} \u2192 id={eid}")


def _handle_batch(source_type: str, filepath: str, dry_run: bool = False):
    with open(filepath) as f:
        identifiers = [line.strip() for line in f if line.strip()]

    print(f"[batch] Processing {len(identifiers)} {source_type} sources")
    for i, ident in enumerate(identifiers, 1):
        print(f"\n[{i}/{len(identifiers)}] {ident}")
        _handle_run(source_type, ident, dry_run)


if __name__ == "__main__":
    main()
