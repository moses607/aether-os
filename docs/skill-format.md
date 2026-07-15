# Aether OS — `SKILL.md` Format Specification

A **skill** in Aether OS is a folder containing a single `SKILL.md` file. That
file describes a capability in plain Markdown with a small structured header. The
kernel's `SkillRegistry` (`aether/kernel/skills.py`) discovers these files, reads
their frontmatter, and makes them available to route on.

Skills are **files, not code.** You add a capability by writing a document, not
by registering a Python object. This keeps skills portable, diffable, and
readable by both humans and models.

> **Status note.** Discovery + frontmatter parsing (`name`, `description`,
> `version`, `tags`) is **built and tested** today. The richer optional fields
> (`inputs`, `requires`, `risk`) and "skill fusion" described below are part of
> the **evolved format**: write them now for forward-compatibility, but treat
> anything beyond the four core fields as convention the base registry does not
> yet enforce. Cryptographic skill verification is **roadmap**, not built.

---

## 1. File layout & discovery

```
skills/
├── summarize-thread/
│   └── SKILL.md
├── draft-reply/
│   └── SKILL.md
└── extract-invoice/
    └── SKILL.md
```

- The registry scans for **`*/SKILL.md`** — one skill per folder, and the folder
  is the natural home for any companion files the skill references.
- The file **must** be named `SKILL.md`.
- Discovery is by directory walk; there is no central registry file to edit.

---

## 2. Frontmatter

`SKILL.md` opens with a YAML-ish frontmatter block delimited by `---`. It is
parsed **without a hard PyYAML dependency**, so keep it to simple
`key: value` pairs and flat lists — do not rely on advanced YAML features
(anchors, nested maps, multi-line block scalars).

### 2.1 Required fields

| Field         | Type   | Purpose                                                         |
| ------------- | ------ | -------------------------------------------------------------- |
| `name`        | string | Stable identifier for the skill.                               |
| `description` | string | What the skill does and **when to use it** — the routing key.  |

The `description` is the single most important field: **the model routes on
`description`.** Write it so a model choosing among skills can tell, from this
line alone, whether this skill applies. Lead with the trigger ("Use when…").

### 2.2 Optional fields

| Field       | Type          | Purpose                                                            |
| ----------- | ------------- | ----------------------------------------------------------------- |
| `version`   | string        | Semantic version of the skill, e.g. `1.2.0`.                      |
| `tags`      | list of string| Coarse grouping / filtering, e.g. `[email, writing]`.            |
| `inputs`    | list of string| Named inputs the skill expects (evolved format; convention).      |
| `requires`  | list of string| Other skill `name`s this skill composes with (see §5, fusion).    |
| `risk`      | string        | `low` · `medium` · `high` — hint for the governance gate.        |

`risk` is advisory metadata for the human/governance layer; it does not itself
grant or deny anything. Deny-by-default governance still applies to any action
the skill leads an agent to propose.

### 2.3 Frontmatter example

```yaml
---
name: extract-invoice
description: >
  Use when the user provides an invoice, receipt, or bill and wants the
  key fields pulled out. Extracts vendor, date, line items, and total.
version: 0.3.0
tags: [finance, extraction]
inputs: [document_text]
requires: [normalize-currency]
risk: low
---
```

---

## 3. Body conventions

Below the frontmatter, the body is ordinary Markdown for the agent to follow. The
recommended shape is **principle → method → output template → rules**:

```markdown
## Principle
One or two sentences on the goal and mindset. *Why* this skill exists and
what "good" looks like.

## Method
The step-by-step procedure the agent should follow. Numbered steps.

## Output template
The exact shape the result should take — a schema, a heading structure, a
JSON skeleton, or a filled example.

## Rules
Hard constraints and guardrails: what to never do, edge cases, when to
stop and ask, when to defer to another skill.
```

Keep each section tight. The body is instructions an agent will actually read at
run time, so favor imperative, unambiguous prose over background.

---

## 4. Auto-discovery & routing

How a skill goes from a file on disk to something an agent uses:

1. **Scan.** `SkillRegistry` walks the skills directory for `*/SKILL.md`.
2. **Parse.** Each file's frontmatter is read into a skill record
   (`name`, `description`, `version`, `tags`, …).
3. **Expose.** The registry surfaces the available skills (the CLI can list them
   via `python -m aether.cli skills`).
4. **Route.** When a task comes in, the model selects a skill by matching the
   task against each skill's **`description`**. This is why the description must
   describe *when to use* the skill, not just what it is.

Routing is a model decision over descriptions, not a hardcoded dispatch table.
Adding, removing, or rewording a skill changes routing with no code change.

---

## 5. Skill fusion (composition)

**Skill fusion** is composing several skills to accomplish a task no single skill
covers. The `requires` field declares the composition:

- A skill lists the `name`s of skills it builds on in `requires`.
- At routing time, selecting the top-level skill implies pulling in its required
  skills so their methods are available together.
- Fusion is meant to be **flat and explicit**: prefer a small number of named
  dependencies over deep chains, so the composed behavior stays readable and the
  governance/`risk` picture stays clear.

Example: a `reconcile-statement` skill might `requires: [extract-invoice,
normalize-currency]` — it routes as one capability but fuses three skills'
methods.

> Fusion is a **convention of the evolved format.** Declare `requires` now for
> forward-compatibility; the base registry parses it but does not yet enforce
> automatic loading of dependencies.

---

## 6. Minimal valid example

The smallest skill that the registry will discover and route on needs only the
two required fields plus a body:

```markdown
---
name: summarize-thread
description: >
  Use when the user wants a long email or chat thread condensed into the
  key points, decisions, and open action items.
---

## Principle
Turn a noisy thread into the few things a busy reader needs.

## Method
1. Identify participants and the thread's purpose.
2. Pull out decisions made and questions still open.
3. List concrete action items with owners, if named.

## Output template
**Summary:** <2–3 sentences>
**Decisions:** <bullets>
**Open items / actions:** <bullets, with owners>

## Rules
- Never invent decisions or owners that are not in the source.
- If the thread has no clear action items, say so explicitly.
```

Save that as `skills/summarize-thread/SKILL.md` and it will be discovered on the
next scan.

---

## 7. Authoring checklist

- [ ] Folder contains a file named exactly `SKILL.md`.
- [ ] Frontmatter has `name` and `description`.
- [ ] `description` leads with **when to use** the skill (it is the routing key).
- [ ] Frontmatter uses only simple `key: value` pairs and flat lists.
- [ ] Body follows **principle → method → output template → rules**.
- [ ] Optional `version`, `tags`, `inputs`, `requires`, `risk` added where useful.
- [ ] `requires` lists only real skill `name`s for fusion.
- [ ] `risk` set honestly for anything that could lead to a consequential action.
