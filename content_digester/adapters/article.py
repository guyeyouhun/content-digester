"""article adapter——网页文章分析拆解"""
from __future__ import annotations

from content_digester.core.registry import Adapter, register_adapter
from content_digester.lib.llm import LLMClient
from content_digester.schemas.intermediate import (
    Entity,
    KnowledgeGraph,
    ParsedContent,
    RawContent,
    Section,
)


@register_adapter("article")
class ArticleAdapter(Adapter):
    """网页文章 adapter"""

    @property
    def source_type(self) -> str:
        return "article"

    def fetch(self, identifier: str) -> RawContent:
        downloaded = self._fetch_url(identifier)
        if not downloaded:
            raise ValueError(f"Failed to fetch URL: {identifier}")

        return RawContent(
            source_type="article",
            identifier=identifier,
            title=identifier.rstrip("/").split("/")[-1][:80] or "article",
            raw_data=downloaded,
            metadata={"url": identifier},
        )

    def _fetch_url(self, url: str) -> str | None:
        """尝试多种方式获取 URL 内容"""
        # Try trafilatura first
        import trafilatura
        result = trafilatura.fetch_url(url)
        if result:
            return result

        # Fallback: requests
        import requests
        try:
            resp = requests.get(
                url,
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0 (compatible; content-digester/1.0)"},
            )
            if resp.ok:
                return resp.text
        except Exception:
            pass  # trafilatura 和 requests 都失败时，无可回退方案

        return None

    def parse(self, raw: RawContent) -> ParsedContent:
        import trafilatura

        text = trafilatura.extract(
            raw.raw_data,
            output_format="txt",
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
        title = raw.title
        metadata = raw.metadata.copy()

        # Try structured extraction for better title
        result = trafilatura.extract(
            raw.raw_data,
            output_format="json",
            with_metadata=True,
        )
        if result:
            import json
            try:
                data = json.loads(result)
                if data.get("title"):
                    title = data["title"]
                metadata["author"] = data.get("author", "")
                metadata["date"] = data.get("date", "")
                metadata["description"] = data.get("description", "")
                text = data.get("text", text or "")
            except (json.JSONDecodeError, KeyError):
                pass

        sections = []
        if text:
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for i, para in enumerate(paragraphs):
                sections.append(Section(
                    heading=f"section-{i}",
                    content=para[:2000],
                    level=1,
                    type="text",
                ))

        return ParsedContent(
            title=title,
            sections=sections[:30],
            metadata=metadata,
        )

    def decompose(self, parsed: ParsedContent) -> KnowledgeGraph:
        llm = LLMClient()

        combined = "\n\n".join(
            f"## {s.heading}\n{s.content}" for s in parsed.sections
        )
        if not combined.strip():
            return KnowledgeGraph(entities=[
                Entity(
                    name=parsed.title[:80],
                    type="concept",
                    summary=parsed.metadata.get("description", parsed.title)[:200],
                    detail=parsed.title,
                    tags=["article"],
                )
            ])

        kg = llm.decompose(combined, title=parsed.title)
        if not kg.entities:
            kg.entities.append(Entity(
                name=parsed.title[:80],
                type="concept",
                summary=combined[:200],
                detail=combined[:2000],
                tags=["article"],
            ))

        return kg
