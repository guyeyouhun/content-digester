# auto-kb \u2194 content-digester \u6570\u636e\u6a21\u578b\u5bf9\u9f50\u62a5\u544a

**\u65e5\u671f**: 2026-06-26  
**\u5206\u6790\u8005**: ModelAligner  

---

## 1. \u77e5\u8bc6 Entry \u5b57\u6bb5\u6620\u5c04

### 1.1 \u5b57\u6bb5\u5bf9\u7167\u8868

| auto-kb `knowledge` \u5217 | auto-kb `types.ts` | content-digester `KnowledgeEntry` | \u5bf9\u9f50\u72b6\u6001 |
|---|---|---|---|
| `id` | `id: string` | _(\u7531 `_upsert_entry` \u751f\u6210 UUID)_ | \u2705 Auto |
| `type` | `type: KnowledgeType` | `type: str` | \u2705 \u5df2\u5bf9\u9f50 |
| `title` | `title: string` | `title: str` | \u2705 \u76f4\u63a5\u4f20\u9012 |
| `summary` | `summary: string` | `summary: str` | \u2705 \u76f4\u63a5\u4f20\u9012 |
| `content` | `content: string` | `content: str` | \u2705 \u76f4\u63a5\u4f20\u9012 |
| `code_example` | `code_example?: string` | `code_example: str` | \ud83d\udfe2 **\u672c\u6b21\u65b0\u589e** |
| `tags` | `tags: string[]` | `tags: list[str]` | \u2705 JSON \u5e8f\u5217\u5316 |
| `roles` | `roles: string[]` | `roles: list[str]` | \ud83d\udfe2 **\u672c\u6b21\u65b0\u589e** |
| `tasks` | `tasks: string[]` | `tasks: list[str]` | \ud83d\udfe2 **\u672c\u6b21\u65b0\u589e** |
| `truth` | `truth: Truth` | _(\u786c\u7f16\u7801 `'staging'`)_ | \u2705 \u5408\u7406\u9ed8\u8ba4 |
| `provenance` | `provenance: Provenance` | _(\u786c\u7f16\u7801 `'extracted'`)_ | \u2705 \u5408\u7406\u9ed8\u8ba4 |
| `evidence` | `evidence?: string` | `evidence: str` | \ud83d\udfe2 **\u672c\u6b21\u65b0\u589e** |
| `strength` | `strength: number` | \u2014 | \ud83d\udfe2 DB \u9ed8\u8ba4 0.8 |
| `stability` | `stability: number` | \u2014 | \ud83d\udfe2 DB \u9ed8\u8ba4 0.8 |
| `difficulty` | `difficulty: number` | \u2014 | \ud83d\udfe2 DB \u9ed8\u8ba4 0.3 |
| `temperature` | `temperature` | \u2014 | \ud83d\udfe2 DB \u9ed8\u8ba4 'warm' |
| `practice_count` | `practice_count: number` | \u2014 | \ud83d\udfe2 DB \u9ed8\u8ba4 0; \u91cd\u590d\u5199\u5165 +1 |
| `practice_success` | `practice_success: number` | \u2014 | \ud83d\udfe2 DB \u9ed8\u8ba4 0 |
| `supersedes` | `supersedes?: string` | \u2014 | \ud83d\udfe2 \u6682\u4e0d\u586b\u5145 |
| `superseded_by` | `superseded_by?: string` | \u2014 | \ud83d\udfe2 \u6682\u4e0d\u586b\u5145 |
| `source` | `source?: string` | `source: str` | \u2705 \u4f20\u9012\u4e3a `source_ref` |
| `relations` | `relations: Relation[]` | `relations: list[dict]` | \u2705 \u72ec\u7acb\u8868\u5199\u5165 |
| `created_at` | `created_at: string` | _(`_now()`)_ | \u2705 |
| `updated_at` | `updated_at: string` | _(`_now()`)_ | \u2705 |
| `last_accessed` | `last_accessed?: string` | \u2014 | \ud83d\udfe2 DB \u9ed8\u8ba4 NULL |

### 1.2 \u4fee\u590d\u524d\u7f3a\u5931\u7684\u5b57\u6bb5\uff08\u5df2\u4fee\u590d\uff09

\u4fee\u590d\u524d `_upsert_entry` INSERT \u53ea\u5305\u542b 11 \u4e2a\u5b57\u6bb5\uff1a
```
id, type, title, summary, content, tags, source, provenance, truth, created_at, updated_at
```

**\u7f3a\u5931**: `code_example`, `roles`, `tasks`, `evidence`

\u4fee\u590d\u540e INSERT \u5305\u542b 15 \u4e2a\u5b57\u6bb5\uff0c\u8986\u76d6\u6240\u6709\u6709\u610f\u4e49\u7684\u6570\u636e\u5217\u3002

### 1.3 roles / tasks \u63a8\u5bfc\u903b\u8f91

content-digester \u7684 `Entity` \u4e0d\u76f4\u63a5\u643a\u5e26 `roles`/`tasks`\uff0c\u901a\u8fc7 `Entity.to_entry()` \u81ea\u52a8\u63a8\u5bfc\uff1a

**roles \u63a8\u5bfc** (`Entity._derive_roles()`):
```
type \u2192 roles \u6620\u5c04:
  method       \u2192 [developer]
  tool         \u2192 [developer, devops]
  product      \u2192 [product_manager, developer]
  pattern      \u2192 [developer, architect]
  architecture \u2192 [architect]
  data_model   \u2192 [data_engineer, developer]
  concept      \u2192 [researcher]

tag hint \u589e\u5f3a (\u5b89\u5168\u68c0\u67e5):
  testing    \u2192 +qa_engineer
  security   \u2192 +security_engineer
  deployment \u2192 +devops
  monitoring \u2192 +devops
  frontend   \u2192 +frontend_developer
  api        \u2192 +backend_developer
```

**tasks \u63a8\u5bfc** (`Entity._derive_tasks()`):
```
type \u2192 tasks \u6620\u5c04:
  method       \u2192 [implement, apply]
  tool         \u2192 [use, configure, integrate]
  product      \u2192 [evaluate, compare, select]
  pattern      \u2192 [apply, recognize, refactor]
  architecture \u2192 [design, evaluate, review]
  data_model   \u2192 [design, query, migrate]
  concept      \u2192 [understand, explain, research]
```

**KnowledgeType \u6620\u5c04** (`Entity._map_type_to_knowledge_type()`):
```
  pattern      \u2192 pattern
  architecture \u2192 pattern
  data_model   \u2192 concept
  product      \u2192 project
  (\u5176\u4ed6)        \u2192 concept (default)
```

---

## 2. \u5173\u7cfb\u7c7b\u578b\u5bf9\u9f50

### 2.1 \u7c7b\u578b\u7a7a\u95f4\u5bf9\u6bd4

| content-digester `Relation.type` | auto-kb `RelationType` | \u517c\u5bb9\u6027 |
|---|---|---|
| `references` | `references` | \u2705 \u76f4\u63a5 |
| `implements` | `implements` | \u2705 \u76f4\u63a5 |
| `contradicts` | `contradicts` | \u2705 \u76f4\u63a5 |
| `derives_from` | `derives_from` | \u2705 \u76f4\u63a5 |
| `depends` | \u2014 | \u274c **\u6620\u5c04 \u2192 `references`** |
| `contains` | \u2014 | \u274c **\u6620\u5c04 \u2192 `references`** |
| \u2014 | `supersedes` | (content-digester \u4e0d\u4f7f\u7528) |
| \u2014 | `extends` | (content-digester \u4e0d\u4f7f\u7528) |

### 2.2 \u6620\u5c04\u51fd\u6570

\u65b0\u589e `_map_relation_type()`:
- \u76f4\u63a5\u5339\u914d 6 \u79cd\u5df2\u77e5\u7c7b\u578b \u2192 \u539f\u6837\u8fd4\u56de
- `depends` \u2192 `references` (\u4f9d\u8d56\u5173\u7cfb\u964d\u7ea7\u4e3a\u65b9\u5411\u5f15\u7528)
- `contains` \u2192 `references` (\u5305\u542b\u5173\u7cfb\u6241\u5e73\u5316\u4e3a\u5f15\u7528)
- \u5176\u4ed6\u672a\u77e5 \u2192 `references` (\u5b89\u5168\u56de\u9000)

### 2.3 \u8bed\u4e49\u8bf4\u660e

- **`depends`**: content-digester \u4e2d\u8868\u793a \"\u5b9e\u4f53 A \u4f9d\u8d56\u5b9e\u4f53 B\"\u3002auto-kb \u6ca1\u6709\u7b49\u4ef7\u7c7b\u578b\uff0c\u4f7f\u7528 `references` \u6355\u83b7\u65b9\u5411\u6027\u3002\u672a\u6765\u53ef\u8003\u8651\u6dfb\u52a0 `depends_on` \u5230 auto-kb RelationType\u3002
- **`contains`**: content-digester \u4e2d\u8868\u793a \"\u5b9e\u4f53 A \u5305\u542b\u5b9e\u4f53 B\"\uff08\u7ec4\u5408\u5173\u7cfb\uff09\u3002\u4f7f\u7528 `references` \u4f5c\u4e3a\u8fd1\u4f3c\u3002\u7cbe\u786e\u5efa\u6a21\u9700\u8981 auto-kb \u652f\u6301\u5c42\u7ea7\u5173\u7cfb\u3002

---

## 3. refresh_queue \u4fee\u590d

### 3.1 \u4fee\u590d\u524d

`write_entries()` \u4e0d\u5199\u5165 `refresh_queue`\u3002source_type \u901a\u8fc7 `_infer_source_type()` \u63a8\u65ad\u4f46\u672a\u88ab\u5229\u7528\u3002

### 3.2 \u4fee\u590d\u540e

\u65b0\u589e Pass 3\uff1a\u6bcf\u4e2a\u6761\u76ee\u5199\u5165\u540e\u81ea\u52a8\u63d2\u5165 `refresh_queue`\uff1a
```sql
INSERT INTO refresh_queue (kn_id, source_ref, source_type, reason, status, ...)
VALUES (?, ?, ?, 'content_digested', 'pending', ...)
```

source_type \u6b63\u786e\u4f20\u9012\uff1a`paper` / `video` / `repo` / `article` / `unknown`\u3002

---

## 4. \u4fee\u6539\u7684\u6587\u4ef6

### 4.1 `content-digester/content_digester/schemas/intermediate.py`
- `KnowledgeEntry`: \u6dfb\u52a0 `@dataclass`, \u65b0\u589e `roles`, `tasks`, `evidence`, `code_example` \u5b57\u6bb5
- `Entity.to_entry()`: \u8c03\u7528\u65b0\u63a8\u5bfc\u65b9\u6cd5\uff0c\u4f20\u9012\u6240\u6709\u5b57\u6bb5
- `Entity._map_type_to_knowledge_type()`: \u65b0\u589e \u2014 entity type \u2192 KnowledgeType \u6620\u5c04
- `Entity._derive_roles()`: \u65b0\u589e \u2014 \u4ece type + tags \u63a8\u5bfc\u89d2\u8272
- `Entity._derive_tasks()`: \u65b0\u589e \u2014 \u4ece type \u63a8\u5bfc\u4efb\u52a1

### 4.2 `content-digester/content_digester/writers/auto_kb.py`
- `_upsert_entry()`: INSERT \u65b0\u589e `code_example`, `roles`, `tasks`, `evidence` \u5217
- `_map_relation_type()`: \u65b0\u589e \u2014 \u663e\u5f0f\u5173\u7cfb\u7c7b\u578b\u6620\u5c04
- `write_entries()`: 
  - \u4f7f\u7528 `_map_relation_type()` \u66ff\u4ee3\u5185\u8054 fallback
  - \u65b0\u589e Pass 3: \u5199\u5165 `refresh_queue`
  - \u660e\u786e source_type \u4f20\u9012

### 4.3 \u4e0d\u53d8\u7684\u6587\u4ef6
- `auto-knowledge-base/src/types.ts`: **\u672a\u4fee\u6539** \u2014 \u6ee1\u8db3 \"\u4e0d\u66f4\u6539\u5df2\u6709\u5b57\u6bb5\u540d\" \u7ea6\u675f
- `auto-knowledge-base/src/storage/schema.sql`: **\u672a\u4fee\u6539** \u2014 \u6240\u6709\u65b0\u589e\u5b57\u6bb5\u5df2\u5728 schema \u4e2d\u5b58\u5728

---

## 5. \u9a8c\u8bc1\u7ed3\u679c

\u2705 Entity.to_entry() \u751f\u6210\u5b8c\u6574\u5b57\u6bb5 KnowledgeEntry  
\u2705 \u6240\u6709 entity type \u63a8\u5bfc\u51fa\u975e\u7a7a roles/tasks  
\u2705 Depends/contains \u5173\u7cfb\u6b63\u786e\u6620\u5c04\u4e3a references  
\u2705 refresh_queue \u6b63\u786e\u5199\u5165 source_type \u548c reason  
\u2705 \u76f4\u63a5\u5339\u914d\u7684\u5173\u7cfb\u7c7b\u578b (references/implements/contradicts/derives_from) \u4e0d\u5931\u771f  
\u2705 \u9ed8\u8ba4 KnowledgeEntry \u521b\u5efa\u65f6 roles/tasks/evidence \u4e3a\u7a7a\u5217\u8868/\u5b57\u7b26\u4e32 (\u5b89\u5168\u9ed8\u8ba4\u503c)  
