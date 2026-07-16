"""
Aether OS — Session (the high-level API)
========================================

One object that wires the kernel together: memory + skills + a governed
orchestrator + usage tracking. This is the ergonomic entrypoint — the kernel
primitives stay available underneath if you want to compose them yourself.

    from aether.session import Session

    s = Session(db="aether.db", skills_path="skills")
    s.remember("User prefers concise answers", kind="fact")

    # Assemble the context you feed your model: relevant memories + matching skills.
    ctx = s.context_for("write me a hook for a video")
    #  -> {"task": ..., "memories": [...], "skills": [{"name":..., "body":...}]}

    # Nothing side-effecting runs without passing policy + (if high risk) a human.
    if s.authorize(Action("tool", "memory.write", risk="high")):
        ...

The Session never calls a model. You bring agent callables — that's what keeps
Aether provider-agnostic (see DECISIONS.md).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from aether.kernel.governance import (
    Action,
    AllowlistPolicy,
    Approver,
    AuditLog,
    Governor,
    Policy,
)
from aether.kernel.memory import Memory, MemoryStore
from aether.kernel.orchestrator import Agent, Orchestrator, RunResult, Step
from aether.kernel.skills import SkillRegistry
from aether.kernel.tracking import Price, UsageTracker


class Session:
    """A live Aether session: memory, skills, orchestration, governance, cost."""

    def __init__(
        self,
        *,
        db: str | Path = "aether.db",
        skills_path: str | Path | None = "skills",
        namespace: str = "default",
        policy: Policy | None = None,
        approver: Approver | None = None,
        audit_path: str | Path = "aether-audit.jsonl",
        prices: dict[str, Price] | None = None,
        verifier: Agent | None = None,
    ) -> None:
        self.namespace = namespace
        self.memory = MemoryStore(db)
        self.skills = SkillRegistry()
        if skills_path and Path(skills_path).exists():
            self.skills.discover(skills_path)
        # Deny-by-default: an empty allowlist permits nothing until you opt in.
        self.governor = Governor(policy or AllowlistPolicy(), AuditLog(audit_path), approver)
        self.usage = UsageTracker(prices)
        self.orchestrator = Orchestrator(verifier=verifier)

    # -- memory --------------------------------------------------------------

    def remember(self, content: str, *, kind: str = "fact", meta: dict | None = None) -> int:
        return self.memory.remember(content, namespace=self.namespace, kind=kind, meta=meta)

    def recall(self, query: str, *, limit: int = 5) -> list[Memory]:
        return self.memory.recall(query, namespace=self.namespace, limit=limit)

    # -- context assembly ----------------------------------------------------

    def context_for(self, task: str, *, memory_limit: int = 5, skill_limit: int = 3) -> dict[str, Any]:
        """Build the context bundle for a task: relevant memories + matching skills.

        This is the kernel's core value: instead of dumping everything into the
        window, you get only what this task needs.
        """
        memories = [m.content for m in self.recall(task, limit=memory_limit)]
        matched = self.skills.match(task)[:skill_limit]
        return {
            "task": task,
            "memories": memories,
            "skills": [{"name": s.name, "description": s.description, "body": s.body} for s in matched],
        }

    # -- governance ----------------------------------------------------------

    def authorize(self, action: Action) -> bool:
        """Policy check + audit + (if required) human approval. Returns True to proceed."""
        return self.governor.authorize(action)

    # -- orchestration -------------------------------------------------------

    def run_sequential(self, steps: Sequence[Step], task: str) -> RunResult:
        return self.orchestrator.run_sequential(steps, task, self.context_for(task))

    def run_council(self, agents: Sequence[Agent], task: str, *, judge: Agent) -> RunResult:
        return self.orchestrator.run_council(agents, task, judge=judge, context=self.context_for(task))

    # -- lifecycle -----------------------------------------------------------

    def close(self) -> None:
        self.memory.close()

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
