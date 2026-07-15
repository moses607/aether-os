"""
Aether OS — CLI
===============

A tiny, dependency-free terminal entrypoint over the kernel primitives, so the
project is usable the moment you clone it:

    python -m aether.cli remember "Ship Aether OS v0.1 on Friday" --kind decision
    python -m aether.cli recall launch
    python -m aether.cli memories
    python -m aether.cli skills --path skills

This is the terminal-first adapter. Web dashboard and MCP/VS Code adapters are
on the roadmap and sit behind the same kernel API (see ARCHITECTURE.md).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from aether.kernel.memory import MemoryStore
from aether.kernel.skills import SkillRegistry

DEFAULT_DB = "aether.db"


def _cmd_remember(args: argparse.Namespace) -> int:
    with MemoryStore(args.db) as store:
        mid = store.remember(args.text, namespace=args.namespace, kind=args.kind)
        print(f"remembered #{mid} [{args.kind}] in '{args.namespace}'")
    return 0


def _cmd_recall(args: argparse.Namespace) -> int:
    with MemoryStore(args.db) as store:
        hits = store.recall(args.query, namespace=args.namespace, limit=args.limit)
        if not hits:
            print("(no matches)")
        for m in hits:
            print(f"#{m.id} [{m.kind}] {m.content}")
    return 0


def _cmd_memories(args: argparse.Namespace) -> int:
    with MemoryStore(args.db) as store:
        rows = store.all(namespace=args.namespace, limit=args.limit)
        print(f"{store.count()} memories total; showing {len(rows)}")
        for m in rows:
            print(f"#{m.id} [{m.kind}] ({m.namespace}) {m.content}")
    return 0


def _cmd_skills(args: argparse.Namespace) -> int:
    reg = SkillRegistry().discover(args.path)
    print(f"discovered {len(reg)} skill(s) in '{args.path}':")
    for name in reg.names():
        skill = reg.get(name)
        assert skill is not None
        print(f"  - {name}: {skill.description[:90]}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aether", description="Aether OS kernel CLI")
    p.add_argument("--db", default=DEFAULT_DB, help="path to the SQLite memory store")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("remember", help="store a memory")
    r.add_argument("text")
    r.add_argument("--namespace", default="default")
    r.add_argument("--kind", default="fact")
    r.set_defaults(func=_cmd_remember)

    rc = sub.add_parser("recall", help="full-text recall")
    rc.add_argument("query")
    rc.add_argument("--namespace", default=None)
    rc.add_argument("--limit", type=int, default=10)
    rc.set_defaults(func=_cmd_recall)

    m = sub.add_parser("memories", help="list recent memories")
    m.add_argument("--namespace", default=None)
    m.add_argument("--limit", type=int, default=20)
    m.set_defaults(func=_cmd_memories)

    s = sub.add_parser("skills", help="discover skills in a directory")
    s.add_argument("--path", default="skills")
    s.set_defaults(func=_cmd_skills)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
