"""paper adapter——论文/PDF 分析拆解"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from content_digester.core.registry import Adapter, register_adapter
from content_digester.lib.llm import LLMClient
from content_digester.schemas.intermediate import (
    Entity,
    KnowledgeGraph,
    ParsedContent,
    RawContent,
    Section,
)


ARXIV_ID_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5})(?:v\d+)?")


def _is_arxiv_id(identifier: str) -> bool:
    return bool(ARXIV_ID_RE.search(identifier))


def _fetch_arxiv_abstract(arxiv_id: str) -> str:
    import requests

    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    # Simple XML parsing for title + abstract
    text = resp.text
    title = ""
    abstract = ""

    m = re.search(r"<title>(.*?)</title>", text, re.DOTALL)
    if m:
        title = m.group(1).strip()

    m = re.search(r"<summary>(.*?)</summary>", text, re.DOTALL)
    if m:
        abstract = m.group(1).strip()

    # Remove XML tags
    abstract = re.sub(r"<[^>]+>", "", abstract)
    title = re.sub(r"<[^>]+>", "", title)

    return f"Title: {title}\n\nAbstract: {abstract}"


@register_adapter("paper")
class PaperAdapter(Adapter):
    """论文 adapter — 支持 ArXiv URL/ID 和本地 PDF"""

    @property
    def source_type(self) -> str:
        return "paper"

    def fetch(self, identifier: str) -> RawContent:
        path = Path(identifier)

        # 本地 PDF
        if path.exists() and path.suffix.lower() == ".pdf":
            content = path.read_bytes()
            return RawContent(
                source_type="paper",
                identifier=identifier,
                title=path.stem,
                raw_data=content,
                metadata={"local_path": str(path.resolve()), "format": "pdf"},
            )

        # ArXiv URL/ID
        m = ARXIV_ID_RE.search(identifier)
        if m:
            arxiv_id = m.group(1)
            # Try to get abstract from ArXiv API
            text = _fetch_arxiv_abstract(arxiv_id)

            # Also try to download PDF for fuller text
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            try:
                import requests
                resp = requests.get(pdf_url, timeout=30, stream=True)
                if resp.ok:
                    pdf_content = resp.content
                    return RawContent(
                        source_type="paper",
                        identifier=identifier,
                        title=f"arxiv-{arxiv_id}",
                        raw_data=pdf_content,
                        metadata={
                            "arxiv_id": arxiv_id,
                            "format": "pdf",
                            "abstract": text,
                            "url": pdf_url,
                        },
                    )
            except Exception:
                pass  # PDF 下载失败（网络或被封锁），回退到仅使用 ArXiv 摘要

            # Fallback: abstract only
            return RawContent(
                source_type="paper",
                identifier=identifier,
                title=f"arxiv-{arxiv_id}",
                raw_data=text,
                metadata={"arxiv_id": arxiv_id, "format": "abstract"},
            )

        # Plain URL — try to fetch as web page
        import requests
        resp = requests.get(identifier, timeout=30)
        resp.raise_for_status()
        return RawContent(
            source_type="paper",
            identifier=identifier,
            title=identifier.rstrip("/").split("/")[-1][:80],
            raw_data=resp.text,
            metadata={"url": identifier, "format": "html"},
        )

    def parse(self, raw: RawContent) -> ParsedContent:
        sections = []
        metadata = raw.metadata.copy()

        # Try markitdown for PDF (if available)
        if raw.metadata.get("format") == "pdf" and isinstance(raw.raw_data, bytes):
            try:
                from markitdown import MarkItDown
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(raw.raw_data)
                    tmp_path = f.name
                try:
                    md = MarkItDown()
                    result = md.convert(tmp_path)
                    text = result.text_content
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
                metadata["parser"] = "markitdown"

                # Split into sections by headings
                for block in re.split(r"\n#{1,3}\s+", text):
                    block = block.strip()
                    if not block:
                        continue
                    lines = block.split("\n", 1)
                    heading = lines[0].strip()[:80]
                    content = lines[1].strip()[:2000] if len(lines) > 1 else ""
                    sections.append(Section(
                        heading=heading,
                        content=content,
                        type="text",
                    ))
                return ParsedContent(
                    title=raw.title,
                    sections=sections[:30],
                    metadata=metadata,
                )
            except ImportError:
                pass  # markitdown 未安装，回退到 PyMuPDF 文本提取

            # Fallback: try PyMuPDF
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=raw.raw_data, filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                metadata["parser"] = "pymupdf"

                paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                for i, para in enumerate(paragraphs[:30]):
                    sections.append(Section(
                        heading=f"section-{i}",
                        content=para[:2000],
                        type="text",
                    ))
                return ParsedContent(
                    title=raw.title,
                    sections=sections,
                    metadata=metadata,
                )
            except ImportError:
                pass

        # Abstract-only or HTML fallback
        text = raw.raw_data if isinstance(raw.raw_data, str) else raw.raw_data.decode("utf-8", errors="ignore")

        # Include abstract text if available
        if "abstract" in metadata:
            text = metadata["abstract"] + "\n\n" + text

        sections.append(Section(
            heading="abstract",
            content=text[:5000],
            type="text",
        ))

        return ParsedContent(
            title=raw.title,
            sections=sections,
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
                    summary=parsed.title,
                    tags=["paper"],
                )
            ])

        kg = llm.decompose(combined, title=parsed.title)

        if not kg.entities:
            kg.entities.append(Entity(
                name=parsed.title[:80],
                type="concept",
                summary=combined[:300],
                detail=combined[:3000],
                tags=["paper"],
            ))

        return kg
