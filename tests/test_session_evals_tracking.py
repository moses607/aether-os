"""Tests for the v0.2 additions: eval harness, usage tracking, and Session."""

from __future__ import annotations

from pathlib import Path

from aether.kernel.evals import Case, EvalHarness, contains, exact
from aether.kernel.governance import Action, AllowlistPolicy
from aether.kernel.tracking import Price, UsageTracker
from aether.session import Session


# -- evals -------------------------------------------------------------------

def test_eval_scores_and_pass_rate() -> None:
    h = EvalHarness(scorer=contains)
    report = h.run(lambda s: "the answer is 4", [Case("2+2?", expect="4"), Case("3+3?", expect="6")])
    assert report.pass_rate == 0.5
    assert len(report.failures) == 1
    assert "pass_rate=50%" in report.summary()


def test_eval_exception_is_a_failed_case_not_a_crash() -> None:
    def boom(_: str) -> str:
        raise RuntimeError("model down")

    report = EvalHarness().run(boom, [Case("x", expect="y")])
    assert report.pass_rate == 0.0
    assert report.results[0].error and "RuntimeError" in report.results[0].error


def test_exact_scorer() -> None:
    assert exact("4", Case("2+2", expect="4")) == 1.0
    assert exact("four", Case("2+2", expect="4")) == 0.0


# -- tracking ----------------------------------------------------------------

def test_cost_is_zero_without_prices() -> None:
    t = UsageTracker()
    u = t.record("a", "m", prompt_tokens=1000, completion_tokens=1000)
    assert u.cost == 0.0
    assert "no price table set" in t.report()


def test_cost_computed_from_supplied_prices() -> None:
    t = UsageTracker({"m": Price(input_per_mtok=10.0, output_per_mtok=30.0)})
    t.record("agent1", "m", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert round(t.total_cost(), 4) == 40.0
    assert t.by_agent()["agent1"] == 40.0
    assert t.total_tokens() == 2_000_000


# -- session -----------------------------------------------------------------

def test_session_context_bundles_memory_and_skills(tmp_path: Path) -> None:
    sk = tmp_path / "skills" / "hooks"
    sk.mkdir(parents=True)
    (sk / "SKILL.md").write_text(
        "---\nname: hooks\ndescription: Generate a hook for a video.\n---\n# Hooks\nplaybook\n",
        encoding="utf-8",
    )
    with Session(db=":memory:", skills_path=tmp_path / "skills",
                 audit_path=tmp_path / "audit.jsonl") as s:
        s.remember("User prefers concise answers")
        ctx = s.context_for("hook for a video")
        assert "concise" in " ".join(ctx["memories"]) or ctx["memories"] == []
        assert any(sk["name"] == "hooks" for sk in ctx["skills"])


def test_session_is_deny_by_default(tmp_path: Path) -> None:
    with Session(db=":memory:", skills_path=None, audit_path=tmp_path / "audit.jsonl") as s:
        assert s.authorize(Action("shell", "rm -rf /")) is False


def test_session_allows_only_allowlisted(tmp_path: Path) -> None:
    with Session(
        db=":memory:",
        skills_path=None,
        policy=AllowlistPolicy({"tool": ["memory."]}),
        audit_path=tmp_path / "audit.jsonl",
    ) as s:
        assert s.authorize(Action("tool", "memory.recall")) is True
        assert s.authorize(Action("tool", "network.post")) is False
        assert (tmp_path / "audit.jsonl").exists()  # every decision is audited
