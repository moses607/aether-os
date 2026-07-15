"""
Aether OS — Kernel: Agent Orchestrator
======================================

Model-agnostic coordination primitives. Agents are just callables:

    Agent = Callable[[str, dict], str]   # (task, context) -> result

The kernel never calls an LLM directly — you inject agent functions bound to
whatever backend you want (Claude, GPT-class, local). That keeps the core
provider-agnostic and testable. Two topologies ship in v0.1:

- **sequential**: pipe a task through an ordered list of agents (each sees the
  previous result). Deterministic, cheapest.
- **council**: run N agents on the same task, then aggregate (vote / debate).
  A judge agent picks or synthesizes the answer. This is where reliability comes
  from — independent perspectives catch what one pass misses.

Roadmap (see ARCHITECTURE.md): parallel fan-out/fan-in, loop-until-done with
stop conditions, and verification gates wired to the governance layer.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

Agent = Callable[[str, dict], str]


@dataclass
class Step:
    name: str
    agent: Agent


@dataclass
class RunResult:
    output: str
    trace: list[dict] = field(default_factory=list)


class Orchestrator:
    """Coordinates agents. Verification/approval hooks come from governance."""

    def __init__(self, *, verifier: Agent | None = None) -> None:
        # Optional verifier runs after each step; return "" to accept, or a
        # reason string to reject (triggers a single retry in v0.1).
        self._verifier = verifier

    def run_sequential(self, steps: Sequence[Step], task: str, context: dict | None = None) -> RunResult:
        ctx = dict(context or {})
        result = task
        trace: list[dict] = []
        for step in steps:
            result = step.agent(result, ctx)
            ctx[step.name] = result
            entry = {"step": step.name, "output": result}
            if self._verifier:
                verdict = self._verifier(result, ctx)
                entry["verdict"] = verdict or "accepted"
                if verdict:  # rejected -> one retry with the feedback in context
                    ctx["_verification_feedback"] = verdict
                    result = step.agent(result, ctx)
                    entry["retry_output"] = result
            trace.append(entry)
        return RunResult(output=result, trace=trace)

    def run_council(
        self,
        agents: Sequence[Agent],
        task: str,
        *,
        judge: Agent,
        context: dict | None = None,
    ) -> RunResult:
        """Independent agents answer, a judge synthesizes/selects. Diversity of
        perspective is the reliability mechanism — see DECISIONS.md ADR-0003."""
        ctx = dict(context or {})
        opinions = [a(task, ctx) for a in agents]
        ctx["opinions"] = opinions
        verdict = judge(task, ctx)
        trace = [{"agent": i, "opinion": o} for i, o in enumerate(opinions)]
        trace.append({"judge": verdict})
        return RunResult(output=verdict, trace=trace)
