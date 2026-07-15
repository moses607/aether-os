"""
Aether OS — Kernel: Governance & Policy
=======================================

Nothing an agent proposes executes without passing the policy layer. This is the
"no blind execution" guarantee from SECURITY.md. Every side-effecting action is
described as an `Action`, checked against the active `Policy`, and — when the
policy says so — routed to a human approver before it runs. Every decision is
appended to an append-only `AuditLog`.

This module ships runnable defaults (allowlist + human-approval gate + audit
log). Sandboxing and cryptographic skill verification are layered on top (see
ROADMAP / SECURITY.md).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Verdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    NEEDS_APPROVAL = "needs_approval"


@dataclass
class Action:
    """A proposed side effect (tool call, shell command, file write, network)."""
    kind: str                      # e.g. "shell", "http", "file_write", "tool"
    target: str                    # command / url / path / tool name
    payload: dict = field(default_factory=dict)
    risk: str = "unknown"          # "low" | "medium" | "high"


@dataclass
class Decision:
    verdict: Verdict
    reason: str


class Policy:
    """Base policy. Subclass and override `check`."""

    def check(self, action: Action) -> Decision:  # pragma: no cover - interface
        raise NotImplementedError


class AllowlistPolicy(Policy):
    """Deny by default. Allow only explicitly listed (kind, target-prefix) pairs;
    send `high` risk to human approval even if allowlisted."""

    def __init__(self, allow: dict[str, list[str]] | None = None) -> None:
        # e.g. {"tool": ["memory.*", "search"], "http": ["https://api.github.com"]}
        self.allow = allow or {}

    def check(self, action: Action) -> Decision:
        prefixes = self.allow.get(action.kind, [])
        permitted = any(
            action.target == p or action.target.startswith(p.rstrip("*"))
            for p in prefixes
        )
        if not permitted:
            return Decision(Verdict.DENY, f"{action.kind}:{action.target} not on allowlist")
        if action.risk == "high":
            return Decision(Verdict.NEEDS_APPROVAL, "high-risk action requires human approval")
        return Decision(Verdict.ALLOW, "allowlisted")


class AuditLog:
    """Append-only JSONL audit trail."""

    def __init__(self, path: str | Path = "aether-audit.jsonl") -> None:
        self.path = Path(path)

    def record(self, action: Action, decision: Decision, *, approved_by: str | None = None) -> None:
        entry = {
            "ts": time.time(),
            "action": {"kind": action.kind, "target": action.target, "risk": action.risk},
            "verdict": decision.verdict.value,
            "reason": decision.reason,
            "approved_by": approved_by,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


# An approver returns True to permit a NEEDS_APPROVAL action. In the CLI this is a
# yes/no prompt; a web dashboard or Slack approval implements the same signature.
Approver = Callable[[Action], bool]


class Governor:
    """Ties policy + audit + human approval into one gate."""

    def __init__(self, policy: Policy, audit: AuditLog, approver: Approver | None = None) -> None:
        self.policy = policy
        self.audit = audit
        self.approver = approver

    def authorize(self, action: Action) -> bool:
        decision = self.policy.check(action)
        approved_by = None
        allowed = decision.verdict == Verdict.ALLOW
        if decision.verdict == Verdict.NEEDS_APPROVAL and self.approver:
            allowed = self.approver(action)
            approved_by = "human" if allowed else None
        self.audit.record(action, decision, approved_by=approved_by)
        return allowed
