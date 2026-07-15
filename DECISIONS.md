# Aether OS — Architecture Decision Record (ADR) Log

> Aether OS is an open-source, model-agnostic AI agent **kernel**. This log records the
> architectural decisions behind v0.1. We are building in public: decisions here reflect
> what is **implemented and tested today** unless explicitly marked as a design goal.
> Where a decision anticipates future tiers (vector/graph memory, adapters, sandboxing),
> it is stated as intent, not as a shipped capability.

---

## ADR-0001 — Provider-agnostic kernel via injected agent callables

**Status:** Accepted

**Context:**
Most agent frameworks bind tightly to a single LLM provider or SDK. That couples your
orchestration logic to one vendor's client, auth, and message schema, and makes swapping
models (or running several side by side) a rewrite. We want the kernel to outlive any one
model generation and any one provider's API.

**Decision:**
The kernel never calls an LLM itself. Agents are supplied to the `Orchestrator` as plain
injected **callables** (`(task, context) -> result`). The kernel coordinates these
callables — sequentially, or in council/debate — but knows nothing about tokens, prompts,
HTTP, or provider auth. Whoever integrates Aether wraps their model of choice (any vendor,
local model, or even a non-LLM function) in a callable and hands it to the kernel.

**Consequences:**
- Model/provider choice is a caller concern, not a kernel concern — no vendor lock-in.
- Trivial to run heterogeneous agents (e.g. one model proposes, another verifies).
- Testing needs no network or API keys: inject deterministic stub callables.
- The kernel cannot offer provider-specific conveniences (token counting, native tool-call
  schemas). Those live in adapters/integration code above the kernel by design.

---

## ADR-0002 — Stdlib-only base tier, optional extras

**Status:** Accepted

**Context:**
Heavy dependency trees are a tax: install friction, supply-chain surface, version conflicts,
and slow cold starts. Yet some capabilities (vector search, graph stores) genuinely need
third-party libraries. We want a base that runs anywhere Python runs, without forcing those
costs on users who don't need them.

**Decision:**
The base kernel — memory (SQLite FTS), skill registry, orchestrator, governance, CLI — uses
the **Python standard library only**. Advanced tiers ship as optional extras
(`pip install aether[vectors]`, `aether[graph]`, etc.) that are activated only when installed.

**Consequences:**
- `pip install aether` yields a working, testable kernel with zero third-party deps.
- Minimal supply-chain surface for the trust-critical core (governance/audit).
- Optional tiers must degrade gracefully: the kernel checks for extras and falls back to the
  base behavior when they are absent.
- Some richer features are unavailable until a user opts into an extra — an accepted trade.

---

## ADR-0003 — Council / debate with a verifier for reliability

**Status:** Accepted

**Context:**
A single agent pass is a single point of failure: hallucination, a missed constraint, or a
low-quality answer goes straight to the output. We want a structural way to raise reliability
that does not depend on any one model being "smart enough."

**Decision:**
The `Orchestrator` supports a **council/debate** mode over multiple injected agent callables,
plus a **verifier** step that checks or reconciles candidate answers before a result is
returned. Because agents are just callables (ADR-0001), the council can mix models, prompts,
or roles (proposer, critic, verifier) freely.

**Consequences:**
- Reliability becomes an orchestration property, not a per-model gamble.
- Naturally supports proposer/critic and best-of-N patterns without special-casing providers.
- Higher cost/latency: N agent calls plus verification per task. Callers choose sequential vs.
  council per workload.
- Quantified reliability gains are a **design goal**, not a measured claim in v0.1 — the
  eval harness to measure them is on the roadmap.

---

## ADR-0004 — Deny-by-default governance and audit log ("no blind execution")

**Status:** Accepted

**Context:**
Agents that can act (run tools, touch files, spend money) are dangerous precisely when they
are autonomous. Allow-by-default is unsafe: any new or unexpected action would execute. We
also need an after-the-fact record of what was attempted and what was decided.

**Decision:**
Governance is **deny-by-default**. An `AllowlistPolicy` must explicitly permit an action or
it is refused. A `Governor` mediates execution and routes high-risk actions to human approval.
Every decision — allowed, denied, escalated, approved — is appended to an immutable-style
JSONL `AuditLog`. Nothing executes without passing the policy first: no blind execution.

**Consequences:**
- Safe failure mode: unknown actions are refused, not run.
- Full, greppable audit trail (JSONL) for review, debugging, and accountability.
- Slightly more setup: operators must declare what the agent may do. This is intentional
  friction that keeps authority explicit.
- Provides the substrate for later RBAC/multi-tenant governance (see ROADMAP).

---

## ADR-0005 — SKILL.md as the extensibility unit

**Status:** Accepted

**Context:**
Capabilities need to be shareable, reviewable, and version-controllable without shipping
opaque code blobs or requiring a plugin SDK. Humans and agents alike should be able to read a
capability and understand what it does before it runs.

**Decision:**
The unit of extensibility is a **`SKILL.md`** file — a human-readable, Markdown-based
descriptor discovered and indexed by the `SkillRegistry`. Skills are plain files: easy to
diff, review in a PR, and store in git.

**Consequences:**
- Capabilities are transparent and reviewable by design; no hidden behavior in a binary.
- Skills compose with governance (ADR-0004): what a skill may do is still gated by policy.
- A Markdown contract needs discipline to stay unambiguous; conventions in the registry keep
  parsing predictable.
- Cryptographic skill verification (signing/provenance) is a **roadmap item**, not present in
  v0.1. Today's trust model is source review, not signatures.

---

## ADR-0006 — SQLite as L1 memory with FTS; vector/graph as optional tiers

**Status:** Accepted

**Context:**
Memory is core to a useful agent, but "memory" spans exact recall, semantic similarity, and
relationship traversal. Forcing a vector database or graph engine on every user for the
common case (store and retrieve text) is overkill and adds heavy dependencies.

**Decision:**
The L1 (base) memory tier is **SQLite with full-text search (FTS)**, exposed via `MemoryStore`
— stdlib-only, embedded, no server. Vector similarity and graph relationships are defined as
**optional higher tiers** activated via extras (ADR-0002), behind the same store interface.

**Consequences:**
- Durable, queryable, dependency-free memory out of the box; one file, no daemon.
- FTS covers keyword recall well; semantic and relational retrieval await the optional tiers.
- A single interface lets callers add vector/graph tiers later without rewriting call sites.
- Vector + graph tiers are a **roadmap deliverable**, currently unbuilt — not yet available.

---

## ADR-0007 — Terminal-first, adapters behind one kernel API

**Status:** Accepted

**Context:**
Chasing many surfaces at once (IDE plugins, web UIs, chat integrations) before the core is
stable spreads effort thin and lets surface concerns leak into the kernel. But we also don't
want the kernel married to the terminal forever.

**Decision:**
v0.1 is **terminal-first**: the CLI is the primary and reference surface. All other surfaces
(MCP, VS Code, web) are planned as **adapters** that sit above **one stable kernel API** —
the kernel exposes a single programmatic contract, and every surface is a thin translation
layer onto it.

**Consequences:**
- The CLI validates the kernel API as a real client, keeping that contract honest.
- Future adapters add reach without changing kernel internals.
- Surfaces stay thin: no orchestration or governance logic in adapter code.
- MCP/VS Code/web adapters do not exist yet — they are **roadmap**, not shipped.

---

## ADR-0008 — Open, human-readable formats over proprietary lock-in

**Status:** Accepted

**Context:**
State that agents produce (memory, skills, audit trails) has long-term value only if users can
read, migrate, and own it. Proprietary or binary formats trap that value inside our tooling and
make external inspection or migration painful.

**Decision:**
Prefer **open, inspectable formats** end to end: skills are Markdown (`SKILL.md`), the audit
log is JSONL, memory lives in a standard SQLite database file. No proprietary container is
required to read or move Aether's state.

**Consequences:**
- Users own and can inspect their data with ubiquitous tools (`sqlite3`, `grep`, any editor).
- Interoperability and migration are straightforward; no export step to escape a walled format.
- We accept the constraints of general formats (e.g. JSONL append semantics, Markdown parsing
  conventions) rather than optimizing a bespoke binary layout.

---

## ADR-0009 — Human-in-the-loop for high-risk actions

**Status:** Accepted

**Context:**
Some actions are irreversible or costly (deleting data, spending money, changing permissions).
Deny-by-default (ADR-0004) prevents the unknown, but for known-but-dangerous actions the right
answer is often "ask a person," not a static allow/deny.

**Decision:**
The `Governor` classifies actions by risk and routes **high-risk** ones to an explicit
**human approval** gate before execution. Approvals and denials are recorded in the audit log
alongside the action they concern.

**Consequences:**
- Dangerous actions require a deliberate human decision, on the record.
- Keeps a human accountable for consequential steps while routine actions stay automated.
- Adds latency and requires an approval channel; acceptable for the class of actions involved.
- Risk classification is policy-driven and will evolve as more action types are governed.
