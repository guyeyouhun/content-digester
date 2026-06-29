"""video adapter——视频/音频内容分析拆解"""
from __future__ import annotations

import re

from content_digester.core.registry import Adapter, register_adapter
from content_digester.lib.llm import LLMClient
from content_digester.schemas.intermediate import (
    Entity,
    KnowledgeGraph,
    ParsedContent,
    RawContent,
    Section,
)

# YouTube URL patterns
YT_RE = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)"
    r"([a-zA-Z0-9_-]{11})"
)


@register_adapter("video")
class VideoAdapter(Adapter):
    """视频 adapter — 当前支持 YouTube 字幕"""

    @property
    def source_type(self) -> str:
        return "video"

    def fetch(self, identifier: str) -> RawContent:
        yt_id = None
        m = YT_RE.search(identifier)
        if m:
            yt_id = m.group(1)
        elif len(identifier) == 11 and identifier.isalnum():
            yt_id = identifier

        if yt_id:
            return self._fetch_youtube(yt_id)

        # Plain URL or path — store as-is for potential future video types
        return RawContent(
            source_type="video",
            identifier=identifier,
            title=identifier.rstrip("/").split("/")[-1][:80],
            raw_data="",
            metadata={"url": identifier, "format": "unknown"},
        )

    def _fetch_youtube(self, video_id: str) -> RawContent:
        from youtube_transcript_api import YouTubeTranscriptApi

        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            text = "\n".join(entry["text"] for entry in transcript_list)
            languages = [video_id]  # Will be updated if API provides lang info
        except Exception:
            # Try manual languages
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["zh-Hans", "zh-Hant", "en"])
                text = "\n".join(entry["text"] for entry in transcript_list)
            except Exception:
                text = ""

        # Get video metadata (title via simple fetch)
        title = f"youtube-{video_id}"
        try:
            import requests
            resp = requests.get(
                f"https://www.youtube.com/watch?v={video_id}",
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.ok:
                m = re.search(r"<title>(.*?)</title>", resp.text, re.DOTALL)
                if m:
                    title = m.group(1).replace(" - YouTube", "").strip()
        except Exception:
            pass  # 获取 YouTube 标题失败（网络/HTML 解析），使用默认标题

        return RawContent(
            source_type="video",
            identifier=video_id,
            title=title,
            raw_data=text,
            metadata={
                "video_id": video_id,
                "platform": "youtube",
                "format": "transcript",
            },
        )

    def parse(self, raw: RawContent) -> ParsedContent:
        text = raw.raw_data if isinstance(raw.raw_data, str) else raw.raw_data.decode("utf-8", errors="ignore")
        sections = []

        if not text.strip():
            return ParsedContent(
                title=raw.title,
                sections=[],
                metadata=raw.metadata,
            )

        # Split transcript into logical segments
        max_chars = 3000
        segments = []
        current = ""
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if len(current) + len(line) > max_chars:
                segments.append(current)
                current = line
            else:
                current += " " + line
        if current:
            segments.append(current)

        for i, seg in enumerate(segments):
            sections.append(Section(
                heading=f"part-{i + 1}",
                content=seg[:2000],
                type="text",
            ))

        return ParsedContent(
            title=raw.title,
            sections=sections[:20],
            metadata=raw.metadata,
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
                    summary=f"Video: {parsed.title}",
                    tags=["video"],
                )
            ])

        kg = llm.decompose(combined, title=parsed.title)

        if not kg.entities:
            kg.entities.append(Entity(
                name=parsed.title[:80],
                type="concept",
                summary=f"Video transcription summary: {parsed.title}",
                detail=combined[:2000],
                tags=["video"],
            ))

        return kg