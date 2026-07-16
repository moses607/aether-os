# Aether OS — Roadmap

> **Aether OS** is an open-source, model-agnostic AI agent **kernel**: a small,
> provider-agnostic core that pairs **memory + governance** with an **evolved skills system**.
> The kernel coordinates *injected* agent callables — it never calls an LLM itself — so you
> bring any model, any provider.
>
> **Building in public.** This roadmap separates what is **built and tested today** from what
> is **planned**. Everything under *Next* and *Later* is a **design goal**, not a shipped or
> measured result. We will not describe roadmap items as done.

## Where Aether sits

The agent ecosystem today skews toward one of three shapes: **SDK-heavy frameworks** that
couple your logic to one vendor, **provider-locked runtimes** tied to a single model's API, or
**skill/prompt collections** with no governed execution core. Aether's bet is different and
deliberately small: a **provider-agnostic kernel** with first-class **memory** and
**deny-by-default governance**, extended through a transparent **`SKILL.md`** system. We aim to
complement — not clone — projects in the broader space (e.g. Superpowers, VoltAgent /
awesome-agent-skills, AIOS, Microsoft Agent Framework); we position at the **architectural**
level (kernel + governance + memory), not on any specific feature claim.

---

## Now — MVP (v0.1, shipped & tested)

The current release is a working, stdlib-only kernel:

- **Provider-agnostic Orchestrator** — coordinates injected agent callables. Sequential mode
  and **council/debate + verifier** mode. The kernel never calls an LLM itself.
- **Memory — L1 tier** — `MemoryStore` on **SQLite with full-text search (FTS)**. Durable,
  embedded, no server, no third-party deps.
- **Skills** — `SkillRegistry` discovers and indexes **`SKILL.md`** files as the unit of
  extensibility. Human-readable, git-friendly, reviewable.
- **Governance** — `AllowlistPolicy` (**deny-by-default**), `Governor` with **human approval**
  for high-risk actions, and an append-only **`AuditLog` (JSONL)**. No blind execution.
- **CLI** — terminal-first reference surface exercising the kernel API.
- **Zero third-party dependencies** in the base tier; runs anywhere Python runs.

---

## Next — v0.5 (planned)

Design goals for the next milestone. None of these are built yet.

- **Memory tiers: vector + graph** — optional L2 (semantic/vector) and L3 (graph/relationship)
  tiers behind the existing store interface, shipped as extras. Enables semantic recall and
  relationship traversal beyond keyword FTS.
- **MCP adapter** — expose the kernel over the Model Context Protocol as the first adapter atop
  the single kernel API (per ADR-0007), so MCP-speaking clients can drive Aether.
- **Self-improving Researcher agent** — a reference agent that gathers information and proposes
  new/updated skills, always subject to governance (deny-by-default + approval).
- ~~**Cost tracking**~~ — **shipped v0.2** (`aether/kernel/tracking.py`): per-agent/model tokens + spend. Prices are user-supplied (a stale hardcoded table lies about spend)
  trail, so governance can reason about budget as a risk dimension.
- ~~**Evaluation harness**~~ — **shipped v0.2** (`aether/kernel/evals.py`): cases + scorers + pass-rate report. Still to do: measure council/debate
  gains claimed in ADR-0003). Until this lands, reliability improvements remain **design
  goals**, not measured results.

---

## Later — v1.0 (planned)

Larger surface and trust features. Not built yet.

- **Web dashboard** — a browser surface (another adapter over the kernel API) for runs, memory
  inspection, audit review, and approvals.
- **Sandboxing** — isolated execution for agent/tool actions to contain side effects, layered
  under the existing governance gate.
- **Cryptographic skill verification** — signing and provenance for `SKILL.md` skills, moving
  trust from source-review-only (v0.1) toward verifiable authorship/integrity.
- **Skill marketplace** — discovery and sharing of skills in open formats, with verification
  (above) as the trust backbone.

---

## Enterprise (planned, further out)

For organizations that need Aether governed across teams. Not built yet.

- **Multi-tenant** — isolated memory, skills, and audit per tenant on shared infrastructure.
- **RBAC** — role-based access control layered on the governance core (extends ADR-0004/0009).
- **SSO** — enterprise identity integration for operators and approvers.
- **Audit export** — stream/export the JSONL audit log to external SIEM / compliance systems.
- **On-prem** — fully self-hosted deployment, consistent with the stdlib-first, open-format base.

---

## Roadmap at a glance

| Horizon | Milestone | Focus |
|--------|-----------|-------|
| **Now**   | v0.1 MVP   | Provider-agnostic kernel, SQLite/FTS memory, `SKILL.md`, deny-by-default governance + audit, CLI — **shipped & tested** |
| **Next**  | v0.5       | Vector + graph memory, MCP adapter, Researcher agent — *planned*  ·  cost tracking + eval harness — **shipped in v0.2** |
| **Later** | v1.0       | Web dashboard, sandboxing, crypto skill verification, marketplace — *planned* |
| **Later** | Enterprise | Multi-tenant, RBAC, SSO, audit export, on-prem — *planned* |

---

## Help wanted

Aether is built in public and contributions are welcome. Good places to start:

- **Memory tiers** — prototype the optional vector/graph tiers behind the `MemoryStore`
  interface (keeping the base stdlib-only).
- **Adapters** — help design the MCP adapter (and later VS Code / web) over the single kernel
  API, keeping surfaces thin.
- **Reliability benchmark** — use the shipped eval harness to actually **measure** council/debate gains
  rather than asserted.
- **Skills** — contribute well-scoped `SKILL.md` skills and sharpen the registry conventions.
- **Governance** — stress-test deny-by-default, risk classification, and the approval flow;
  propose the RBAC path toward Enterprise.
- **Docs & examples** — end-to-end samples wiring different providers' models in as injected
  agent callables.

Open an issue to discuss a direction before large changes. Please keep the **base tier
dependency-free** and preserve **open, inspectable formats** (Markdown skills, JSONL audit,
SQLite memory).
