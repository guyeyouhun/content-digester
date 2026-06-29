"""repo adapter——代码仓库分析拆解"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from content_digester.core.registry import Adapter, register_adapter
from content_digester.lib.llm import LLMClient
from content_digester.schemas.intermediate import (
    Confidence,
    Entity,
    KnowledgeGraph,
    ParsedContent,
    RawContent,
    Relation,
    Section,
)


@register_adapter("repo")
class RepoAdapter(Adapter):
    """代码仓库 adapter"""

    @property
    def source_type(self) -> str:
        return "repo"

    def fetch(self, identifier: str) -> RawContent:
        path = Path(identifier)

        # 本地路径
        if path.exists():
            return RawContent(
                source_type="repo",
                identifier=str(path.resolve()),
                title=path.name,
                raw_data=str(path.resolve()),
                metadata={"local_path": str(path.resolve())},
            )

        # GitHub URL → git clone 到临时目录
        tmpdir = tempfile.mkdtemp(prefix="content-digester-")
        dest = os.path.join(tmpdir, "repo")
        subprocess.run(
            ["git", "clone", "--depth", "1", identifier, dest],
            capture_output=True, text=True, timeout=120,
        )
        return RawContent(
            source_type="repo",
            identifier=identifier,
            title=identifier.rstrip("/").split("/")[-1].replace(".git", ""),
            raw_data=dest,
            metadata={"url": identifier, "local_path": dest},
        )

    def parse(self, raw: RawContent) -> ParsedContent:
        """扫描仓库结构，产出结构化描述"""
        root = Path(raw.raw_data)
        sections = []
        metadata = raw.metadata.copy()

        # 检测语言和技术栈
        stack = self._detect_stack(root)
        metadata["stack"] = stack

        # 收集关键文件
        readme = self._find_readme(root)
        if readme:
            sections.append(Section(
                heading="README",
                content=readme[:3000],
                type="text",
            ))

        # 收集目录结构
        tree = self._get_tree(root, max_depth=3)
        sections.append(Section(
            heading="Directory Structure",
            content=tree,
            type="text",
        ))

        # 收集关键配置文件
        configs = self._find_configs(root)
        for name, content in configs:
            sections.append(Section(
                heading=f"Config: {name}",
                content=content[:1000],
                type="code",
            ))

        return ParsedContent(
            title=metadata.get("url", root.name),
            sections=sections,
            metadata=metadata,
        )

    def decompose(self, parsed: ParsedContent) -> KnowledgeGraph:
        """确定性模块提取 + LLM 语义增强"""
        entities = []
        relations = []

        stack = parsed.metadata.get("stack", {})
        repo_name = parsed.metadata.get("url", parsed.title).rstrip("/").split("/")[-1]
        lang_summary = ", ".join(stack.get("languages", []))

        # ── Pass 1: 确定性提取（模块 + 配置） ──

        # Entity: 项目总览
        entities.append(Entity(
            name=f"{repo_name}-overview",
            type="architecture",
            summary=f"{repo_name} 项目概览",
            detail=f"技术栈: {lang_summary}\n框架: {', '.join(stack.get('frameworks', []))}",
            tags=["architecture", *stack.get("languages", [])],
            confidence=Confidence.EXTRACTED.value,
        ))

        # Entity: 关键模块（目录结构推断）
        modules = self._detect_modules(parsed)
        for mod_name, mod_desc in modules:
            entities.append(Entity(
                name=f"{repo_name}-{mod_name}",
                type="architecture",
                summary=mod_desc,
                detail=mod_desc,
                tags=["module", *stack.get("languages", [])],
                confidence=Confidence.INFERRED.value,
            ))
            relations.append(Relation(
                source=f"{repo_name}-overview",
                target=f"{repo_name}-{mod_name}",
                type="contains",
                confidence=Confidence.EXTRACTED.value,
            ))

        # ── Pass 2: LLM 语义增强 ──

        llm = LLMClient()
        if llm.configured:
            # Build a summary of the repo for LLM analysis
            repo_text = (
                f"Repository: {repo_name}\n"
                f"Language: {lang_summary}\n"
                f"Frameworks: {', '.join(stack.get('frameworks', []))}\n\n"
            )
            for s in parsed.sections:
                repo_text += f"## {s.heading}\n{s.content}\n\n"

            kg = llm.decompose(repo_text[:8000], title=repo_name)
            if kg.entities:
                # Merge: add LLM entities that don't overlap with deterministic ones
                det_names = {e.name for e in entities}
                for e in kg.entities:
                    if e.name not in det_names:
                        entities.append(e)
                for r in kg.relations:
                    relations.append(r)

        return KnowledgeGraph(entities=entities, relations=relations)

    # ── 辅助方法 ──────────────────────────────────────────

    def _detect_stack(self, root: Path) -> dict:
        """检测项目技术栈"""
        languages = set()
        frameworks = []

        for f in root.rglob("*"):
            if f.is_dir() and f.name.startswith("."):
                continue
            if f.suffix:
                lang = {
                    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                    ".go": "Go", ".rs": "Rust", ".java": "Java",
                    ".rb": "Ruby", ".php": "PHP", ".cs": "C#",
                    ".swift": "Swift", ".kt": "Kotlin",
                }.get(f.suffix)
                if lang:
                    languages.add(lang)

        # 检测框架
        pkg_files = list(root.rglob("package.json")) + list(root.rglob("pyproject.toml")) + list(root.rglob("Cargo.toml")) + list(root.rglob("go.mod"))
        for pf in pkg_files:
            try:
                text = pf.read_text(encoding="utf-8", errors="ignore")
                if "react" in text.lower(): frameworks.append("React")
                if "next" in text.lower(): frameworks.append("Next.js")
                if "django" in text.lower(): frameworks.append("Django")
                if "fastapi" in text.lower(): frameworks.append("FastAPI")
                if "axum" in text.lower() or "tokio" in text.lower(): frameworks.append("Tokio/Axum")
            except Exception:
                pass  # 读取包配置文件失败（编码/权限），跳过该文件继续检测

        return {"languages": sorted(languages), "frameworks": list(set(frameworks))}

    def _find_readme(self, root: Path) -> str | None:
        for name in ("README.md", "readme.md", "Readme.md"):
            p = root / name
            if p.exists():
                try:
                    return p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    return None
        return None

    def _get_tree(self, root: Path, max_depth: int = 2) -> str:
        lines = []
        for i, p in enumerate(sorted(root.iterdir())):
            if i > 30:
                lines.append("  ...")
                break
            if p.name.startswith("."):
                continue
            if p.is_dir():
                lines.append(f"  {p.name}/")
                if max_depth > 1:
                    for j, sub in enumerate(sorted(p.iterdir())):
                        if j > 10:
                            lines.append(f"    ...")
                            break
                        if not sub.name.startswith("."):
                            lines.append(f"    {sub.name}")
        return "\n".join(lines)

    def _find_configs(self, root: Path) -> list[tuple[str, str]]:
        configs = []
        for name in ("pyproject.toml", "package.json", "Cargo.toml", "go.mod", "Makefile"):
            p = root / name
            if p.exists():
                try:
                    configs.append((name, p.read_text(encoding="utf-8", errors="ignore")))
                except Exception:
                    pass  # 读取配置文件失败（编码/权限），跳过该文件继续
        return configs

    def _detect_modules(self, parsed: ParsedContent) -> list[tuple[str, str]]:
        """从目录结构推断核心模块"""
        modules = []
        all_text = "\n".join(s.content for s in parsed.sections)
        lines = all_text.split("\n")

        for line in lines:
            line = line.strip()
            if line.endswith("/") and not line.startswith("."):
                name = line.rstrip("/").strip()
                if name and name not in ("node_modules", "__pycache__", ".git", "target", "dist", "build"):
                    modules.append((name, f"{name} 模块"))
        return modules[:10]