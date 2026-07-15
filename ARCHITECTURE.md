# Aether OS — Architecture

> **Aether OS** is an open-source, model-agnostic AI agent *kernel*. It is the
> small, testable core that sits *underneath* whatever agents, models, and tools
> you plug into it: durable memory, skill discovery, multi-agent orchestration,
> and a governance gate that decides what an agent is actually allowed to do.
>
> **Status: v0.1 — building in public.** The kernel is deliberately minimal and
> stdlib-only in its base tier. This document describes the design as a whole and
> is explicit about **what exists and is tested today** versus **what is on the
> roadmap**. Roadmap items are labeled as such everywhere they appear.

---

## 1. Design goals

Aether OS is built around a few opinions:

1. **Provider-agnostic core.** The kernel never calls an LLM. Agents are plain
   callables injected by the host application. Swap Claude for a local model, a
   remote API, or a deterministic mock — the kernel does not change.
2. **Deny-by-default governance.** Every consequential action passes through an
   allowlist policy and an append-only audit log. High-risk actions require a
   human approver.
3. **Durable, queryable memory.** Agents that forget are toys. The base memory
   tier is a real SQLite store with full-text recall.
4. **Skills as files, not code.** Capabilities are described in `SKILL.md`
   documents that are discovered from disk, not registered in Python.
5. **Small enough to read.** The base tier depends only on the Python standard
   library. You can read the whole kernel in an afternoon.

These goals imply *design targets* — e.g. "roughly 2x the reliability of a
single-shot agent" via council + verifier + governance. **Those are design
goals, not measured benchmarks.** No performance or reliability numbers in this
repository are claimed as tested results.

---

## 2. Layered architecture

Aether OS is organized in three horizontal bands. Requests enter from the top
(adapters), are coordinated in the middle (kernel), and are grounded at the
bottom (memory). Control flows down; knowledge flows up.

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │                            ADAPTERS                                   │
  │   CLI (built)   ·   MCP server (roadmap)   ·   VS Code (roadmap)      │
  │                     ·   Web dashboard (roadmap)                       │
  │  Translate an external request into a kernel task; render results.    │
  └───────────────────────────────┬─────────────────────────────────────┘
                                   │  task: str + context: dict
  ┌───────────────────────────────▼─────────────────────────────────────┐
  │                             KERNEL                                    │
  │                                                                       │
  │   ┌──────────────┐   ┌───────────────────┐   ┌──────────────────┐    │
  │   │  SkillRegistry│   │   Orchestrator    │   │    Governance    │    │
  │   │  (skills.py) │   │ (orchestrator.py) │   │ (governance.py)  │    │
  │   │              │   │                   │   │                  │    │
  │   │ discover     │   │ run_sequential    │   │ AllowlistPolicy  │    │
  │   │ */SKILL.md   │   │ run_council       │   │ Governor         │    │
  │   │ route on     │   │ + verifier hook   │   │ AuditLog (JSONL) │    │
  │   │ description  │   │ injected agents   │   │ Approver (human) │    │
  │   └──────────────┘   └───────────────────┘   └──────────────────┘    │
  └───────────────────────────────┬─────────────────────────────────────┘
                                   │  read / write records
  ┌───────────────────────────────▼─────────────────────────────────────┐
  │                        MEMORY HIERARCHY                               │
  │                                                                       │
  │   L1  Relational / FTS   (memory.py — MemoryStore)     ✅ BUILT       │
  │       SQLite, FTS5 full-text (LIKE fallback), namespaces, kinds       │
  │                                                                       │
  │   L2  Vector / semantic recall                         ⏳ ROADMAP     │
  │   L3  Graph / entity + relation memory                 ⏳ ROADMAP     │
  └─────────────────────────────────────────────────────────────────────┘
```

### 2.1 Adapters (top band)

Adapters are the *only* part of the system that knows about the outside world.
Their job is to translate an inbound request into a kernel task (`str` +
`dict` context) and to render the kernel's output back out.

- **CLI — built.** `python -m aether.cli remember | recall | memories | skills`.
  A thin, tested entry point over `MemoryStore` and `SkillRegistry`.
- **MCP server, VS Code extension, web dashboard — roadmap.** Not built.

Because adapters are kept thin, the kernel has no transport, framework, or UI
dependency. A new adapter is "translate in, render out" and nothing else.

### 2.2 Kernel (middle band)

Three cooperating modules, each independently testable:

| Module            | Type / entry points                          | Responsibility                                          |
| ----------------- | -------------------------------------------- | ------------------------------------------------------- |
| `skills.py`       | `SkillRegistry`                              | Discover `*/SKILL.md`, parse frontmatter, expose skills |
| `orchestrator.py` | `Orchestrator.run_sequential`, `run_council` | Coordinate injected agent callables                     |
| `governance.py`   | `Governor`, `AllowlistPolicy`, `AuditLog`    | Decide + record what actions are permitted              |

The kernel is **provider-agnostic**: it coordinates agents but never *is* one.
See §4.

### 2.3 Memory hierarchy (bottom band)

Memory is tiered so that cheap, exact recall (L1) can be layered with semantic
(L2) and relational (L3) recall over time.

- **L1 — Relational / FTS. Built and tested.** `MemoryStore` in `memory.py`:
  a SQLite-backed store with FTS5 full-text search (and a `LIKE`-based fallback
  when FTS5 is unavailable), record **namespaces**, and typed **`kind`**
  records. This is the memory the kernel and CLI use today.
- **L2 — Vector / semantic. Roadmap.** Embedding-based similarity recall.
- **L3 — Graph. Roadmap.** Entities and relations for structured recall.

The tiers share one interface idea — write a record, recall relevant records —
so higher tiers can be added behind the same call sites without rewrites.

---

## 3. Data & control flow

A single task flows through the kernel like this:

```
      ┌──────────┐   context/recall    ┌──────────────────┐
      │  MEMORY  │────────────────────▶│   ORCHESTRATOR   │
      │   (L1)   │                     │  run_sequential  │
      │          │◀────────────────────│   / run_council  │
      └──────────┘   new records       └────────┬─────────┘
            ▲                                    │ task + context
            │                                    ▼
            │                          ┌───────────────────┐
            │                          │   AGENT(S)        │
            │                          │  injected callable│
            │                          │ Callable[[str,    │
            │                          │   dict], str]     │
            │                          └────────┬──────────┘
            │                                   │ proposed action / output
            │                                   ▼
            │                          ┌───────────────────┐
            │                          │  GOVERNANCE GATE  │
            │                          │  AllowlistPolicy  │
            │                          │  → Verdict        │
            │                          │  ALLOW / DENY /   │
            │                          │  NEEDS_APPROVAL   │
            │                          └────────┬──────────┘
            │                                   │
            │              ┌────────────────────┼───────────────────┐
            │              ▼                    ▼                   ▼
            │        NEEDS_APPROVAL           ALLOW              DENY
            │              │                    │                   │
            │        ┌───────────┐              │                   │
            │        │  Approver │              │                   │
            │        │  (human)  │              │                   │
            │        └─────┬─────┘              │                   │
            │              │ yes/no             │                   │
            │              ▼                    ▼                   ▼
            │        ┌─────────────────────────────────────────────────┐
            │        │              AUDIT LOG (append-only JSONL)       │
            │        └───────────────────────┬─────────────────────────┘
            │                                 │ permitted result
            │                                 ▼
            │                          ┌───────────────┐
            │                          │    OUTPUT     │
            │                          └───────────────┘
            │                                 │
            └─────────────────────────────────┘
              self-improvement loop (ROADMAP):
              distilled results / new skills feed back
              into MEMORY (L1) and SkillRegistry
```

**Reading the diagram:**

1. **Memory → Orchestrator.** The orchestrator can seed the task with recalled
   context from L1 memory, and write results back as new records.
2. **Orchestrator → Agents.** The orchestrator invokes one or more injected
   agent callables. In `run_sequential` the output of each step feeds the next;
   in `run_council` several agents answer the same task and a `judge` selects or
   synthesizes a final answer. An optional **verifier hook** can check a result
   before it is accepted.
3. **Agents → Governance gate.** Consequential actions are not executed by the
   agent directly. They are proposed to the `Governor`, which consults the
   `AllowlistPolicy` and returns a `Verdict`.
4. **Governance gate → Output.** `ALLOW` proceeds; `DENY` is blocked;
   `NEEDS_APPROVAL` pauses for a human `Approver`. Every decision is appended to
   the JSONL `AuditLog`.
5. **Self-improvement loop — roadmap.** A future self-improving "Researcher"
   agent would distill successful runs into new memory records and new skills,
   closing the loop back to Memory and the SkillRegistry. **Not built.**

---

## 4. Why the core is provider-agnostic

The single most important design decision: **the kernel never calls a model.**

An agent is just:

```python
Agent = Callable[[str, dict], str]
#                 task  context  result
```

The host application supplies these callables to the orchestrator. The kernel
sequences them, runs councils of them, verifies their output, and gates their
actions — but it has no idea whether a given callable is:

- a hosted LLM API call,
- a local open-weights model,
- a rules engine or retrieval function, or
- a deterministic stub used in a unit test.

**Consequences of this choice:**

- **No vendor lock-in.** Swapping providers is swapping a callable, not editing
  the kernel.
- **Trivially testable.** Tests inject deterministic fake agents; the kernel's
  own logic (sequencing, council selection, governance verdicts, audit writes)
  is verified with zero network calls and zero API keys.
- **Composable.** A "council" can mix providers — e.g. two different models plus
  a retrieval agent — because they all satisfy the same signature.
- **Stable core.** Provider churn (new models, new SDKs) lives in adapters and
  host code, not in the kernel.

---

## 5. Reliability model

Aether OS treats reliability as something the *kernel* structures, not something
you hope the model provides. Three composable mechanisms:

1. **Council / debate (`run_council`).** Instead of trusting a single response,
   multiple agents answer the same task and a `judge` callable selects or
   synthesizes the final answer. Diversity of agents is meant to catch
   idiosyncratic failures of any single one.
2. **Verifier hook.** The orchestrator supports an optional verifier that checks
   a candidate result before it is accepted, allowing a "generate → check" loop
   rather than "generate → hope".
3. **Governance gate.** Even a correct-looking result cannot perform a
   consequential action unless the `AllowlistPolicy` permits it. Deny-by-default
   means the blast radius of a bad decision is bounded, and every decision is
   recorded in the append-only `AuditLog`. High-risk actions escalate to a human
   `Approver` (`NEEDS_APPROVAL`).

Together these are intended to make the *system* more reliable than any single
model call — the **design goal** is on the order of a 2x improvement in
end-to-end reliability versus single-shot prompting. **This is a design target,
not a measured benchmark; no reliability numbers here are claimed as tested.**

---

## 6. Governance in detail

`governance.py` is the safety spine of the kernel.

| Concept          | Meaning                                                                     |
| ---------------- | --------------------------------------------------------------------------- |
| `Action`         | A described, proposed operation an agent wants to perform.                  |
| `Decision`       | The outcome of evaluating an `Action` against policy.                       |
| `Verdict`        | `ALLOW` · `DENY` · `NEEDS_APPROVAL`.                                         |
| `AllowlistPolicy`| **Deny-by-default**: only explicitly allowed actions pass automatically.    |
| `Approver`       | Human decision point for `NEEDS_APPROVAL` (high-risk) actions.              |
| `AuditLog`       | **Append-only JSONL** record of every decision — tamper-evident by design.  |
| `Governor`       | Orchestrates policy check → approval (if needed) → audit write.             |

The flow is intentionally boring and inspectable: propose an action, evaluate it
against the allowlist, escalate to a human if the policy says so, and record the
result no matter what. Nothing consequential happens off the record.

---

## 7. Component reference (built today)

| Path                          | Public surface                                              | Tier / role          |
| ----------------------------- | ---------------------------------------------------------- | -------------------- |
| `aether/kernel/memory.py`     | `MemoryStore`                                              | Memory L1 (SQLite/FTS)|
| `aether/kernel/skills.py`     | `SkillRegistry`                                            | Skill discovery      |
| `aether/kernel/orchestrator.py`| `Orchestrator.run_sequential`, `run_council` (+ verifier) | Coordination         |
| `aether/kernel/governance.py` | `Action`, `Decision`, `Verdict`, `AllowlistPolicy`, `AuditLog`, `Governor`, `Approver` | Governance |
| `aether/cli.py`               | `remember`, `recall`, `memories`, `skills`                | Adapter (CLI)        |

**Base-tier dependency policy:** standard library only. `SkillRegistry` parses
YAML-ish frontmatter with **no hard PyYAML dependency**.

---

## 8. What's built vs. roadmap

| Area                                   | Status        | Notes                                             |
| -------------------------------------- | ------------- | ------------------------------------------------- |
| Memory L1 (relational / FTS)           | ✅ Built/tested| `MemoryStore`, SQLite + FTS5, LIKE fallback       |
| Skill discovery + frontmatter parsing  | ✅ Built/tested| `SkillRegistry`, `*/SKILL.md`, no hard PyYAML dep |
| Orchestrator (sequential + council)    | ✅ Built/tested| Injected agents, optional verifier hook           |
| Governance (policy + audit + approval) | ✅ Built/tested| Deny-by-default, append-only JSONL, human approver|
| CLI adapter                            | ✅ Built/tested| `remember` / `recall` / `memories` / `skills`     |
| Memory L2 (vector / semantic)          | ⏳ Roadmap     | Embedding-based recall                            |
| Memory L3 (graph)                      | ⏳ Roadmap     | Entity + relation memory                          |
| MCP / VS Code / web adapters           | ⏳ Roadmap     | Additional front doors to the same kernel         |
| Self-improving Researcher agent        | ⏳ Roadmap     | Closes the self-improvement loop                  |
| Sandboxing                             | ⏳ Roadmap     | Isolated execution of agent actions               |
| Cryptographic skill verification       | ⏳ Roadmap     | Signed / verifiable `SKILL.md`                    |
| Cost / telemetry                       | ⏳ Roadmap     | Usage + cost accounting                           |
| Web dashboard                          | ⏳ Roadmap     | Visual monitoring + control                       |

---

## 9. Design principles, restated

- **The kernel coordinates; it never calls a model.** Providers are injected.
- **Deny-by-default, always audited.** Safety is structural, not advisory.
- **Memory is durable and tiered.** Start with real full-text recall (L1).
- **Skills live on disk.** Discover and route on `description`, don't hardcode.
- **Honesty about status.** Built means built and tested. Everything else is
  labeled roadmap, and all "2x" style figures are design goals, not results.
