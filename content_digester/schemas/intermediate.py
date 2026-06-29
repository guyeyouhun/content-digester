"""统一中间格式定义——Adapter 和 Writer 之间的通信协议。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Confidence(str, Enum):
    """置信度标签（参考 graphify 的置信度系统）"""
    EXTRACTED = "EXTRACTED"   # 来源中显式存在
    INFERRED = "INFERRED"     # 合理推断
    AMBIGUOUS = "AMBIGUOUS"   # 不确定


class EntityType(str, Enum):
    CONCEPT = "concept"
    METHOD = "method"
    TOOL = "tool"
    PRODUCT = "product"
    PATTERN = "pattern"
    ARCHITECTURE = "architecture"
    DATA_MODEL = "data_model"


# ── 原始内容（fetch 输出） ─────────────────────────────────

@dataclass
class RawContent:
    """从素材获取的原始内容"""
    source_type: str          # repo | paper | article | video
    identifier: str            # URL / 路径 / ArXiv ID
    title: str
    raw_data: bytes | str     # 原始数据
    metadata: dict = field(default_factory=dict)


# ── 解析后内容（parse 输出） ───────────────────────────────

@dataclass
class Section:
    heading: str
    content: str
    level: int = 1
    type: str = "text"         # text | code | table | formula


@dataclass
class ParsedContent:
    """结构化解析结果"""
    title: str
    sections: list[Section] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ── 知识图谱（decompose 输出） ─────────────────────────────

@dataclass
class Entity:
    """核心实体——一个可独立学习的知识单元"""
    name: str
    type: str = "concept"      # concept | method | tool | product | ...
    summary: str = ""
    detail: str = ""
    tags: list[str] = field(default_factory=list)
    confidence: str = Confidence.EXTRACTED.value
    evidence: str = ""         # 原文证据

    def to_entry(self, source: str, relations: list[dict] | None = None) -> "KnowledgeEntry":
        return KnowledgeEntry(
            title=self.name,
            content=self.detail or self.summary,
            summary=self.summary,
            tags=[self.type] + self.tags,
            type=self._map_type_to_knowledge_type(),
            source=source,
            relations=relations or [],
            roles=self._derive_roles(),
            tasks=self._derive_tasks(),
            evidence=self.evidence,
        )

    def _map_type_to_knowledge_type(self) -> str:
        """Map content-digester entity type → auto-kb KnowledgeType."""
        mapping = {
            "pattern": "pattern",
            "architecture": "pattern",
            "data_model": "concept",
            "product": "project",
        }
        return mapping.get(self.type, "concept")

    def _derive_roles(self) -> list[str]:
        """Infer roles from entity type and tags.

        auto-kb uses roles for role-based knowledge routing.
        """
        type_role_map = {
            "method": ["developer"],
            "tool": ["developer", "devops"],
            "product": ["product_manager", "developer"],
            "pattern": ["developer", "architect"],
            "architecture": ["architect"],
            "data_model": ["data_engineer", "developer"],
            "concept": ["researcher"],
        }
        roles = list(type_role_map.get(self.type, ["general"]))
        # Boost with tag-based hints
        role_hint_tags = {"testing": "qa_engineer", "security": "security_engineer",
                          "deployment": "devops", "monitoring": "devops",
                          "frontend": "frontend_developer", "api": "backend_developer"}
        for tag in self.tags:
            for hint, role in role_hint_tags.items():
                if hint in tag.lower() and role not in roles:
                    roles.append(role)
        return roles

    def _derive_tasks(self) -> list[str]:
        """Infer tasks from entity type.

        auto-kb uses tasks for task-based knowledge retrieval.
        """
        type_task_map = {
            "method": ["implement", "apply"],
            "tool": ["use", "configure", "integrate"],
            "product": ["evaluate", "compare", "select"],
            "pattern": ["apply", "recognize", "refactor"],
            "architecture": ["design", "evaluate", "review"],
            "data_model": ["design", "query", "migrate"],
            "concept": ["understand", "explain", "research"],
        }
        return type_task_map.get(self.type, ["understand"])


@dataclass
class Relation:
    """实体间的关系"""
    source: str
    target: str
    type: str = "references"   # implements | depends | contradicts | references
    confidence: str = Confidence.INFERRED.value


@dataclass
class KnowledgeGraph:
    """分解后的完整知识图谱"""
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)


# ── 最终输出条目（auto-kb learn 参数） ────────────────────

@dataclass
class KnowledgeEntry:
    """写入 auto-kb 的单条知识"""
    title: str
    content: str
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    type: str = "concept"
    source: str = "content_digester"
    relations: list[dict] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    evidence: str = ""
    code_example: str = ""
