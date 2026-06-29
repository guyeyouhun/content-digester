"""Tests for content_digester.schemas.intermediate — data classes and enums."""

import json
from dataclasses import asdict

import pytest

from content_digester.schemas.intermediate import (
    Confidence,
    Entity,
    EntityType,
    KnowledgeEntry,
    KnowledgeGraph,
    RawContent,
    Relation,
    Section,
    ParsedContent,
)


# ── Confidence enum ─────────────────────────────────────────────────────────

def test_confidence_values():
    """Confidence \u679a\u4e3e\u5b9a\u4e49\u4e86\u4e09\u4e2a\u6807\u51c6\u503c."""
    assert Confidence.EXTRACTED.value == "EXTRACTED"
    assert Confidence.INFERRED.value == "INFERRED"
    assert Confidence.AMBIGUOUS.value == "AMBIGUOUS"


def test_confidence_is_string_enum():
    """Confidence \u662f\u4e00\u4e2a str \u5b50\u7c7b\u679a\u4e3e."""
    assert isinstance(Confidence.EXTRACTED, str)
    assert Confidence.EXTRACTED == "EXTRACTED"


# ── EntityType enum ─────────────────────────────────────────────────────────

def test_entity_type_values():
    """EntityType \u5305\u542b\u6240\u6709\u5185\u5bb9\u7c7b\u578b."""
    types = [t.value for t in EntityType]
    assert "concept" in types
    assert "method" in types
    assert "tool" in types
    assert "product" in types
    assert "pattern" in types
    assert "architecture" in types
    assert "data_model" in types


# ── Entity ──────────────────────────────────────────────────────────────────

def test_entity_creation_defaults():
    """Entity \u4f7f\u7528\u9ed8\u8ba4\u503c\u521b\u5efa."""
    e = Entity(name="test_entity")
    assert e.name == "test_entity"
    assert e.type == "concept"
    assert e.summary == ""
    assert e.detail == ""
    assert e.tags == []
    assert e.confidence == "EXTRACTED"
    assert e.evidence == ""


def test_entity_full_creation():
    """Entity \u4f7f\u7528\u5168\u90e8\u5b57\u6bb5\u521b\u5efa."""
    e = Entity(
        name="Dependency Injection",
        type="pattern",
        summary="A design pattern for decoupling",
        detail="Dependency injection allows components to receive their dependencies from external sources.",
        tags=["design-pattern", "architecture"],
        confidence="INFERRED",
        evidence="See Martin Fowler's article on DI",
    )
    assert e.name == "Dependency Injection"
    assert e.tags == ["design-pattern", "architecture"]
    assert e.confidence == "INFERRED"


def test_entity_to_entry():
    """Entity.to_entry() \u751f\u6210\u6b63\u786e\u7684 KnowledgeEntry."""
    e = Entity(
        name="My Entity",
        type="pattern",
        summary="summary text",
        detail="detail text",
        tags=["tag1"],
    )
    entry = e.to_entry(source="test-src")
    assert isinstance(entry, KnowledgeEntry)
    assert entry.title == "My Entity"
    assert entry.content == "detail text"
    assert entry.summary == "summary text"
    assert "pattern" in entry.tags
    assert "tag1" in entry.tags
    assert entry.source == "test-src"


def test_entity_to_entry_relations():
    """Entity.to_entry() \u6b63\u786e\u4f20\u9012 relations."""
    e = Entity(name="X", detail="details")
    rel = {"target": "Y", "type": "references"}
    entry = e.to_entry(source="s", relations=[rel])
    assert entry.relations == [rel]


def test_entity_to_entry_falls_back_to_summary():
    """\u5f53 detail \u4e3a\u7a7a\u65f6\uff0cEntity.to_entry() \u4f7f\u7528 summary \u4f5c\u4e3a content."""
    e = Entity(name="X", summary="summary only")
    entry = e.to_entry(source="s")
    assert entry.content == "summary only"


# ── Relation ────────────────────────────────────────────────────────────────

def test_relation_creation():
    """Relation \u57fa\u672c\u521b\u5efa."""
    r = Relation(source="A", target="B", type="depends")
    assert r.source == "A"
    assert r.target == "B"
    assert r.type == "depends"
    assert r.confidence == "INFERRED"


def test_relation_default_type():
    """Relation \u9ed8\u8ba4 type \u4e3a 'references'."""
    r = Relation(source="A", target="B")
    assert r.type == "references"


# ── KnowledgeGraph ──────────────────────────────────────────────────────────

def test_kg_creation_empty():
    """KnowledgeGraph \u9ed8\u8ba4\u542b\u7a7a\u5217\u8868."""
    kg = KnowledgeGraph()
    assert kg.entities == []
    assert kg.relations == []


def test_kg_with_data():
    """KnowledgeGraph \u53ef\u4ee5\u5305\u542b\u5b9e\u4f53\u548c\u5173\u7cfb."""
    entities = [Entity(name="E1")]
    relations = [Relation(source="E1", target="E2")]
    kg = KnowledgeGraph(entities=entities, relations=relations)
    assert len(kg.entities) == 1
    assert len(kg.relations) == 1
    assert kg.entities[0].name == "E1"


# ── KnowledgeEntry ──────────────────────────────────────────────────────────

def test_entry_creation():
    """KnowledgeEntry \u57fa\u672c\u521b\u5efa — title \u548c content \u662f\u5fc5\u9700\u5b57\u6bb5."""
    entry = KnowledgeEntry(
        title="Test",
        content="Some content",
    )
    assert entry.title == "Test"
    assert entry.content == "Some content"
    assert entry.summary == ""
    assert entry.tags == []
    assert entry.type == "concept"
    assert entry.source == "content_digester"
    assert entry.relations == []
    assert entry.roles == []
    assert entry.tasks == []
    assert entry.evidence == ""
    assert entry.code_example == ""


def test_entry_all_fields():
    """KnowledgeEntry \u5168\u90e8\u5b57\u6bb5\u586b\u5145."""
    entry = KnowledgeEntry(
        title="Full Entry",
        content="Detailed content",
        summary="Quick summary",
        tags=["python", "testing"],
        type="pattern",
        source="arxiv",
        relations=[{"target": "X", "type": "references"}],
        roles=["developer"],
        tasks=["apply"],
        evidence="page 42",
        code_example="print('hello')",
    )
    assert entry.title == "Full Entry"
    assert entry.roles == ["developer"]
    assert entry.tasks == ["apply"]
    assert entry.evidence == "page 42"
    assert entry.code_example == "print('hello')"


def test_entry_with_relations():
    """KnowledgeEntry \u53ef\u4ee5\u5305\u542b relations."""
    entry = KnowledgeEntry(
        title="X",
        content="content",
        relations=[{"target": "Y", "type": "references"}],
    )
    assert len(entry.relations) == 1
    assert entry.relations[0]["target"] == "Y"



# ── RawContent and ParsedContent ────────────────────────────────────────────
def test_raw_content_creation():
    """RawContent \u57fa\u672c\u521b\u5efa — source_type, identifier, title, raw_data \u662f\u5fc5\u9700\u5b57\u6bb5."""
    rc = RawContent(
        source_type="article",
        identifier="https://example.com",
        title="Example Page",
        raw_data="<html>...</html>",
        metadata={"url": "https://example.com"},
    )
    assert rc.source_type == "article"
    assert rc.identifier == "https://example.com"
    assert rc.title == "Example Page"
    assert rc.raw_data == "<html>...</html>"
    assert rc.metadata["url"] == "https://example.com"

def test_section_creation():
    """Section \u57fa\u672c\u521b\u5efa."""
    s = Section(heading="Intro", content="Welcome", type="text")
    assert s.heading == "Intro"
    assert s.content == "Welcome"
    assert s.type == "text"


def test_parsed_content_creation():
    """ParsedContent \u57fa\u672c\u521b\u5efa."""
    sections = [Section(heading="H1", content="body")]
    pc = ParsedContent(
        title="Doc Title",
        sections=sections,
        metadata={"language": "zh"},
    )
    assert pc.title == "Doc Title"
    assert len(pc.sections) == 1
    assert pc.sections[0].heading == "H1"
