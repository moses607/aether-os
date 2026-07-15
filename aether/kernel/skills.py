"""
Aether OS — Kernel: Skill Registry
==================================

Auto-discovers skills in the evolved SKILL.md format (YAML-ish frontmatter +
markdown body) and exposes them to the orchestrator. Kept dependency-free: the
frontmatter parser only needs `name` and `description` to route, so we avoid a
hard PyYAML dependency in the base tier (a full YAML parser can be swapped in
via the optional extras — see pyproject).

Skill file shape (see docs/skill-format.md):

    ---
    name: my-skill
    description: What it does + when to trigger it.
    version: 1.0.0        # optional
    tags: [research, io]  # optional
    ---
    # My Skill
    ...markdown body (the actual playbook)...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Skill:
    name: str
    description: str
    body: str
    path: Path
    version: str = ""
    tags: list[str] = field(default_factory=list)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a SKILL.md into (frontmatter dict, body). Minimal, forgiving."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    fm: dict[str, str] = {}
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        line = lines[i]
        if ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
        i += 1
    body = "\n".join(lines[i + 1 :]) if i < len(lines) else ""
    return fm, body


def load_skill(path: str | Path) -> Skill:
    """Load and validate a single SKILL.md."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)
    name = fm.get("name") or path.parent.name
    description = fm.get("description", "")
    if not description:
        raise ValueError(f"skill {name} missing 'description' (required for routing)")
    tags_raw = fm.get("tags", "").strip("[] ")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
    return Skill(
        name=name,
        description=description,
        body=body,
        path=path,
        version=fm.get("version", ""),
        tags=tags,
    )


class SkillRegistry:
    """Discovers and holds skills from one or more directories."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def discover(self, root: str | Path) -> "SkillRegistry":
        """Recursively load every `*/SKILL.md` under `root`."""
        root = Path(root)
        for skill_md in sorted(root.rglob("SKILL.md")):
            try:
                skill = load_skill(skill_md)
                self._skills[skill.name] = skill
            except Exception as exc:  # a bad skill must not crash discovery
                print(f"[aether] skipped {skill_md}: {exc}")
        return self

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def names(self) -> list[str]:
        return sorted(self._skills)

    def match(self, query: str) -> list[Skill]:
        """Naive keyword routing over name+description.

        The real orchestrator uses the model to route (descriptions are written
        for that); this is a deterministic fallback for CLI/tests.
        """
        q = query.lower()
        scored = [
            (s, (s.name.lower().count(q) * 2) + s.description.lower().count(q))
            for s in self._skills.values()
        ]
        return [s for s, score in sorted(scored, key=lambda p: -p[1]) if score]

    def __len__(self) -> int:
        return len(self._skills)
