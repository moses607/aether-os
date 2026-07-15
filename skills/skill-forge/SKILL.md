---
name: skill-forge
description: Meta-skill that generates new, high-quality SKILL.md files on demand from a described workflow. It clarifies the job-to-be-done, extracts a repeatable method, writes sharp frontmatter and triggers, and self-checks against a rubric before emitting a drop-in file. Use when the user says "make a skill", "turn this workflow into a skill", "create a SKILL.md", or wants to extend Aether OS with a new capability. Trigger on any request to package a process, checklist, or expertise into a reusable skill. Works with any capable model.
version: 1.0.0
tags: [meta, authoring]
---

# Skill Forge

A skill is compressed judgment: it turns a fuzzy request into a repeatable procedure a model can run cold, with no prior context. The forge's job is to strip a workflow down to its load-bearing method (principle → numbered steps → output template → rules) and nothing else. A skill earns its place only if it changes what the model does; description without instruction is dead weight. Write for a competent stranger who will follow the file literally.

## 1. Clarify the job-to-be-done
1. Name the ONE task this skill exists to do; if you can't say it in a sentence, it's two skills.
2. Identify the user and the moment they reach for it (the trigger context).
3. List the inputs it consumes and the single artifact it must produce.
4. Ask at most 2 sharp questions only if a core ambiguity blocks the method; otherwise infer and proceed.

## 2. Extract the repeatable method
1. Write the core principle in one first-principles sentence — WHY the method works, not what it is.
2. Decompose the doing into 2-3 numbered method sections; each step must be an observable action, not an aspiration ("rank sources by recency", not "consider quality").
3. Design the output template as a concrete, fill-in structure the model can pattern-match against.
4. Distill 5-6 hard rules — opinionated defaults, failure modes to avoid, and the non-negotiables.

## 3. Write frontmatter and self-check
1. Choose a kebab-case name matching the folder; write a 2-4 sentence description that states what it does AND embeds specific trigger phrases ("Use when...", "Trigger on...").
2. End the description with "Works with any capable model." and keep tags to 2 provider-agnostic labels.
3. Run the rubric below; if any answer is "no", revise before emitting.
4. Emit the complete file — nothing but valid SKILL.md, ready to drop into skills/.

## Output template
```
---
name: <kebab-name>
description: <what it does + "Use when..." / "Trigger on..." phrases>. Works with any capable model.
version: 1.0.0
tags: [<a>, <b>]
---

# <Title>
<one first-principles paragraph>

## <Method section 1..3, numbered steps>

## Output template
```<concrete fill-in structure>```

## Rules
- <5-6 hard rules>
```

## Rules
- One skill, one job — split anything that needs "and" in its core sentence.
- No skill ships without a real method AND a concrete output template; prose-only guidance is rejected.
- Triggers must be specific verbs and phrases a user would actually type, never generic ("help me").
- Steps are actions with observable outputs; delete any step a model can't execute literally.
- Stay provider-agnostic: no tool names, model names, or vendor APIs baked into the method.
- Target 2800-3800 chars of dense, specific content — cut every sentence that doesn't change behavior.
