from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from content_digester.schemas.intermediate import (
        KnowledgeEntry, KnowledgeGraph, ParsedContent, RawContent,
    )

ADAPTER_REGISTRY: dict[str, type["Adapter"]] = {}


def detect(source: str) -> str | None:
    """从标识符自动推断 source type"""
    source_lower = source.lower().strip()

    # GitHub / GitLab / Bitbucket URLs
    if any(host in source_lower for host in ("github.com", "gitlab.com", "bitbucket.org")):
        return "repo"
    if source_lower.endswith(".git"):
        return "repo"

    # ArXiv
    if "arxiv.org" in source_lower:
        return "paper"

    # YouTube
    if any(host in source_lower for host in ("youtube.com", "youtu.be")):
        return "video"

    # Local directory (repo-like)
    if source.startswith("/") or source.startswith("~") or source.startswith("."):
        from pathlib import Path
        p = Path(source).expanduser()
        if p.is_dir():
            return "repo"
        if p.is_file() and p.suffix.lower() in (".pdf", ".epub"):
            return "paper"

    # URL → default to article
    if source_lower.startswith("http"):
        return "article"

    # YouTube video ID (11 alphanumeric chars)
    if len(source) == 11 and source.isalnum():
        return "video"

    # ArXiv ID pattern
    import re
    if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", source):
        return "paper"

    return None


def register_adapter(source_type: str):
    """装饰器：注册 adapter 到全局注册表"""
    def wrapper(cls):
        ADAPTER_REGISTRY[source_type] = cls
        return cls
    return wrapper


def get_adapter(source_type: str) -> "Adapter":
    """Factory：从注册表获取 adapter 实例"""
    cls = ADAPTER_REGISTRY.get(source_type)
    if not cls:
        raise ValueError(
            f"Unknown source type: {source_type!r}. "
            f"Available: {list(ADAPTER_REGISTRY)}"
        )
    return cls()


class Adapter(ABC):
    """素材 adapter 基类——模板方法模式

    子类需实现：
      - source_type     (类属性)
      - fetch()
      - parse()
      - decompose()
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        ...

    @abstractmethod
    def fetch(self, identifier: str) -> RawContent:
        """获取原始素材"""
        ...

    @abstractmethod
    def parse(self, raw: RawContent) -> ParsedContent:
        """解析为结构化内容"""
        ...

    @abstractmethod
    def decompose(
        self, parsed: ParsedContent,
    ) -> KnowledgeGraph:
        """分解为知识图谱"""
        ...

    # ── 模板方法 ──────────────────────────────────────────

    def run(self, identifier: str) -> list[KnowledgeEntry]:
        """完整的 fetch → parse → decompose → to_entries 流水线"""
        raw = self.fetch(identifier)
        parsed = self.parse(raw)
        kg = self.decompose(parsed)
        return self._kg_to_entries(kg)

    def _kg_to_entries(self, kg: KnowledgeGraph) -> list[KnowledgeEntry]:
        """将知识图谱拆为 auto-kb 可消费的条目列表"""
        if not kg.entities:
            return []

        # 构建 entity name → KnowledgeEntry 的映射
        entity_map = {}
        entity_entries = []
        for entity in kg.entities:
            entry = entity.to_entry(source=self.source_type)
            entity_map[entity.name] = entry
            entity_entries.append(entry)

        # 补充 relation 信息
        for rel in kg.relations:
            src_entry = entity_map.get(rel.source)
            if src_entry is None:
                continue
            tgt_entry = entity_map.get(rel.target)
            if tgt_entry is None:
                continue
            src_entry.relations.append({
                "target": rel.target,
                "type": rel.type,
            })
            tgt_entry.relations.append({
                "target": rel.source,
                "type": rel.type,
            })

        return entity_entries
