"""Smoke + unit tests for the Aether kernel memory store and skill loader."""

from __future__ import annotations

from pathlib import Path

from aether.kernel.memory import MemoryStore
from aether.kernel.skills import SkillRegistry, load_skill


def test_remember_and_recall() -> None:
    store = MemoryStore(":memory:")
    mid = store.remember("The launch is on Friday", kind="decision")
    assert mid > 0
    hits = store.recall("launch")
    assert any("Friday" in m.content for m in hits)
    assert store.count() == 1


def test_namespaces_isolate() -> None:
    store = MemoryStore(":memory:")
    store.remember("alpha secret", namespace="a")
    store.remember("beta secret", namespace="b")
    assert len(store.recall("secret", namespace="a")) == 1
    assert len(store.recall("secret")) == 2


def test_empty_content_rejected() -> None:
    store = MemoryStore(":memory:")
    try:
        store.remember("   ")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("empty content should raise")


def test_skill_discovery(tmp_path: Path) -> None:
    d = tmp_path / "skills" / "demo"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: demo\ndescription: A demo skill for tests.\n---\n# Demo\nbody\n",
        encoding="utf-8",
    )
    reg = SkillRegistry().discover(tmp_path / "skills")
    assert reg.names() == ["demo"]
    skill = load_skill(d / "SKILL.md")
    assert skill.description.startswith("A demo skill")
