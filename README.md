# content-digester \u2014 \u901a\u7528\u5185\u5bb9\u5206\u89e3\u5c42

\u5c06\u5404\u7c7b\u7d20\u6750\u81ea\u52a8\u83b7\u53d6\u3001\u5206\u6790\u3001\u5206\u89e3\u4e3a\u7ed3\u6784\u5316\u77e5\u8bc6\uff0c\u7edf\u4e00\u5199\u5165 auto-kb\u3002

## \u67b6\u6784

```
\u7d20\u6750\u6807\u8bc6 (Git URL / ArXiv ID / \u7f51\u9875\u94fe\u63a5 / \u672c\u5730\u8def\u5f84)
  \u2192 [fetch]   \u83b7\u53d6\u539f\u59cb\u5185\u5bb9
  \u2192 [parse]   \u63d0\u53d6\u7ed3\u6784\u5316\u4fe1\u606f
  \u2192 [decompose] LLM \u62c6\u89e3\u4e3a entities + concepts + relations
  \u2192 auto-kb learn \u00d7 N
```

\u6bcf\u4e2a adapter \u662f\u81ea\u5305\u542b\u7684\uff1a\u7ed9\u4e00\u4e2a\u6807\u8bc6\uff0c\u5b83\u81ea\u5df1\u5b8c\u6210\u83b7\u53d6\u2192\u89e3\u6790\u2192\u62c6\u89e3\u2192\u5199\u5165\u5168\u6d41\u7a0b\u3002

## Adapters

| Adapter | \u7d20\u6750\u6807\u8bc6 | fetch | parse |
|---------|---------|-------|-------|
| repo | Git URL | git clone | tree-sitter / AST |
| paper | ArXiv ID / PDF \u8def\u5f84 | \u4e0b\u8f7d PDF | PDF \u89e3\u6790 + \u7ae0\u8282\u63d0\u53d6 |
| article | \u7f51\u9875 URL | HTTP fetch | HTML \u2192 markdown |
| video | YouTube URL | \u4e0b\u8f7d\u5b57\u5e55 | \u5b57\u5e55\u5206\u6bb5 |

## \u5165\u53e3

### CLI \u6a21\u5f0f

```bash
# \u5904\u7406\u5355\u4e2a\u7d20\u6750
content-digester run article https://example.com
content-digester run repo https://github.com/user/project
content-digester run paper 2401.12345
content-digester run video https://youtube.com/watch?v=xxx

# \u6279\u91cf\u5904\u7406
content-digester batch article urls.txt

# \u5904\u7406 auto-kb \u7684 refresh_queue\uff08\u8fc7\u65f6\u77e5\u8bc6\u91cd\u65b0\u6d88\u5316\uff09
content-digester refresh --db-path=knowledge.db
```

### MCP Server \u6a21\u5f0f

```bash
content-digester-mcp
# \u63d0\u4f9b 3 \u4e2a MCP \u5de5\u5177: digest, digest_batch, refresh
```

## \u8f93\u51fa

\u6bcf\u4e2a adapter \u6700\u540e\u8c03\u7528 auto-kb \u7684 `write_entries` \u76f4\u63a5\u5199\u5165 SQLite\uff0c\u6216\u901a\u8fc7 `KNOWLEDGE_DB_PATH` \u73af\u5883\u53d8\u91cf\u6307\u5b9a\u76ee\u6807\u6570\u636e\u5e93\u3002entry \u81ea\u52a8\u8fdb\u5165 staging \u72b6\u6001\uff0c\u9700 `knowledge_confirm` \u540e\u624d\u53ef\u68c0\u7d22\u3002

## \u914d\u7f6e

```bash
KNOWLEDGE_DB_PATH=/path/to/knowledge.db
LLM_API_KEY=...
LLM_MODEL=...
```

## \u53cd\u9988\u56de\u8def

content-digester \u4e0e auto-kb \u901a\u8fc7 `refresh_queue` \u5f62\u6210\u95ed\u73af\uff1a

```
auto-kb FSRS \u8870\u51cf \u2192 \u51b7\u51bb\u77e5\u8bc6 \u2192 \u63a8\u5165 refresh_queue
  \u2192 content-digester refresh \u2192 \u91cd\u65b0\u83b7\u53d6/\u89e3\u6790/\u5206\u89e3
  \u2192 \u65b0\u7248\u672c\u5199\u5165 auto-kb \u2192 \u65e7\u7248\u672c superseded
```

## \u6d4b\u8bd5

```bash
pip install -e ".[pdf]"
pytest -v      # 86 tests, 5 files, \u5168 mock \u96f6\u7f51\u7edc
```

## \u6570\u636e\u6a21\u578b\u5bf9\u9f50

\u5b57\u6bb5\u6620\u5c04\u8be6\u89c1 [MODEL_ALIGN.md](MODEL_ALIGN.md)\u3002
