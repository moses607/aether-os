"""
Aether OS — Kernel: Eval Harness
================================

You cannot improve what you do not score. This is the reliability pillar: a
tiny, dependency-free harness that runs a callable against a fixed set of cases
and reports a pass rate — so a prompt/skill/agent change is a *measured* change,
not a vibe.

Deliberately model-agnostic: you pass in any `fn(input) -> output`. Bind it to
whatever backend you like.

    harness = EvalHarness(scorer=contains)
    report = harness.run(my_agent, [Case("2+2?", expect="4")])
    print(report.pass_rate)   # 1.0

Scorers return a float in [0, 1]. Ship your own for domain logic (e.g. JSON
schema validity, unit-test pass, rubric score from a judge model).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field


@dataclass
class Case:
    """One eval case. `expect` is optional when the scorer doesn't need it."""
    input: str
    expect: str | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    case: Case
    output: str
    score: float
    error: str | None = None


@dataclass
class EvalReport:
    results: list[EvalResult]
    threshold: float

    @property
    def mean_score(self) -> float:
        return sum(r.score for r in self.results) / len(self.results) if self.results else 0.0

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.score >= self.threshold) / len(self.results)

    @property
    def failures(self) -> list[EvalResult]:
        return [r for r in self.results if r.score < self.threshold]

    def summary(self) -> str:
        return (
            f"cases={len(self.results)} pass_rate={self.pass_rate:.0%} "
            f"mean_score={self.mean_score:.2f} failures={len(self.failures)}"
        )


Scorer = Callable[[str, Case], float]


def contains(output: str, case: Case) -> float:
    """1.0 if the expected substring appears (case-insensitive)."""
    if case.expect is None:
        return 0.0
    return 1.0 if case.expect.lower() in (output or "").lower() else 0.0


def exact(output: str, case: Case) -> float:
    if case.expect is None:
        return 0.0
    return 1.0 if (output or "").strip() == case.expect.strip() else 0.0


class EvalHarness:
    """Runs a callable over cases and scores it. Failures never crash the run."""

    def __init__(self, *, scorer: Scorer = contains, threshold: float = 1.0) -> None:
        self.scorer = scorer
        self.threshold = threshold

    def run(self, fn: Callable[[str], str], cases: Sequence[Case]) -> EvalReport:
        results: list[EvalResult] = []
        for case in cases:
            try:
                output = fn(case.input)
                results.append(EvalResult(case, output, self.scorer(output, case)))
            except Exception as exc:  # an exception is a failed case, not a crash
                results.append(EvalResult(case, "", 0.0, error=f"{type(exc).__name__}: {exc}"))
        return EvalReport(results, self.threshold)
