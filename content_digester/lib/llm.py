"""LLM 客户端——用于 decompose 阶段的实体/关系提取。"""
from __future__ import annotations

import json
import os
from typing import Optional

import requests

from content_digester.schemas.intermediate import (
    Confidence,
    Entity,
    KnowledgeGraph,
    Relation,
)

# ── 提取 prompt ──

DECOMPOSE_SYSTEM = """You are a knowledge extraction engine. Analyze the given content and extract structured knowledge.

Return JSON:
{
  "entities": [
    {
      "name": "unique entity name",
      "type": "concept|method|tool|product|pattern|architecture",
      "summary": "one-sentence summary",
      "detail": "detailed description (2-3 sentences)",
      "tags": ["tag1", "tag2"],
      "evidence": "exact quote or reference from the content"
    }
  ],
  "relations": [
    {
      "source": "entity name (must match exactly)",
      "target": "entity name (must match exactly)",
      "type": "references|implements|depends|contradicts|contains|derives_from"
    }
  ]
}

Rules:
- Extract 3-8 entities per content piece
- entity names must be unique and concise
- tags lowercase, 2-4 per entity
- relations only between extracted entities
- "type" can also be any short descriptive term not in the enum
- If content is too short or empty, return empty entities list"""


class LLMClient:
    """OpenAI 兼容 API 客户端"""

    def __init__(self):
        self.base_url = (
            os.environ.get("LLM_BASE_URL", "").rstrip("/") or ""
        )
        self.api_key = os.environ.get("LLM_API_KEY", "") or ""
        self.model = os.environ.get("LLM_MODEL", "gpt-4o")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> Optional[str]:
        if not self.configured:
            return None

        url = f"{self.base_url}/chat/completions"
        try:
            resp = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=60,
            )
            if not resp.ok:
                return None
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None

    def decompose(self, content: str, title: str = "") -> KnowledgeGraph:
        """将结构化内容分解为知识图谱"""
        if not content.strip():
            return KnowledgeGraph()

        user_prompt = f"Title: {title or '(untitled)'}\n\nContent:\n{content[:8000]}"
        raw = self.chat(DECOMPOSE_SYSTEM, user_prompt)
        if not raw:
            return KnowledgeGraph()

        try:
            # Strip markdown code fences if present
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
        except (json.JSONDecodeError, IndexError):
            return KnowledgeGraph()

        entities = []
        for e in data.get("entities", []):
            entities.append(Entity(
                name=e.get("name", ""),
                type=e.get("type", "concept"),
                summary=e.get("summary", ""),
                detail=e.get("detail", ""),
                tags=e.get("tags", []),
                confidence=Confidence.EXTRACTED.value if e.get("evidence") else Confidence.INFERRED.value,
                evidence=e.get("evidence", ""),
            ))

        relations = []
        for r in data.get("relations", []):
            relations.append(Relation(
                source=r.get("source", ""),
                target=r.get("target", ""),
                type=r.get("type", "references"),
                confidence=Confidence.INFERRED.value,
            ))

        return KnowledgeGraph(entities=entities, relations=relations)
