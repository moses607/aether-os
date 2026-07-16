"""
Aether OS — Kernel: Usage & Cost Tracking
=========================================

Agents burn money quietly. This tracks tokens and cost per agent and per model
so a run has a price tag you can see.

**Prices are supplied by you, not hardcoded.** Model pricing changes often and a
stale table silently lies about your spend, so the default price table is empty
(cost 0.0) until you provide current rates from your provider's pricing page:

    tracker = UsageTracker(prices={"my-model": Price(input_per_mtok=3.0, output_per_mtok=15.0)})
    tracker.record("researcher", "my-model", prompt_tokens=1200, completion_tokens=300)
    print(tracker.total_cost(), tracker.report())
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Price:
    """USD per 1,000,000 tokens. Get current values from your provider."""
    input_per_mtok: float = 0.0
    output_per_mtok: float = 0.0


@dataclass
class Usage:
    agent: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: float

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class UsageTracker:
    """Accumulates per-call usage; reports totals by agent and by model."""

    def __init__(self, prices: dict[str, Price] | None = None) -> None:
        self.prices = prices or {}
        self.records: list[Usage] = []

    def record(
        self, agent: str, model: str, *, prompt_tokens: int, completion_tokens: int
    ) -> Usage:
        if prompt_tokens < 0 or completion_tokens < 0:
            raise ValueError("token counts must be non-negative")
        price = self.prices.get(model, Price())
        cost = (
            prompt_tokens / 1_000_000 * price.input_per_mtok
            + completion_tokens / 1_000_000 * price.output_per_mtok
        )
        usage = Usage(agent, model, prompt_tokens, completion_tokens, cost)
        self.records.append(usage)
        return usage

    def total_cost(self) -> float:
        return sum(r.cost for r in self.records)

    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.records)

    def by_agent(self) -> dict[str, float]:
        out: dict[str, float] = defaultdict(float)
        for r in self.records:
            out[r.agent] += r.cost
        return dict(out)

    def by_model(self) -> dict[str, float]:
        out: dict[str, float] = defaultdict(float)
        for r in self.records:
            out[r.model] += r.cost
        return dict(out)

    def report(self) -> str:
        if not self.records:
            return "no usage recorded"
        lines = [
            f"calls={len(self.records)} tokens={self.total_tokens():,} "
            f"cost=${self.total_cost():.4f}"
        ]
        for agent, cost in sorted(self.by_agent().items(), key=lambda kv: -kv[1]):
            lines.append(f"  {agent:<24} ${cost:.4f}")
        if not self.prices:
            lines.append("  (no price table set -> costs are 0.00; supply current prices)")
        return "\n".join(lines)
