#!/usr/bin/env python3
"""Vault integrity check: read_file prefix pollution + wikilink resolution.

Two jobs, both cheap and both things a previous session got wrong once:

1. `--corruption` (default on): find .md files whose body contains NESTED
   `NN|` line-number prefixes (e.g. "     1|     1|     1|---"). One layer is
   normal quoting in a note; two or more means an agent took `read_file`
   output and wrote it back as file content.
2. `--linkcheck`: verify every `[[wikilink]]` target of the given files
   resolves to a real file in the vault (basename match or relative path).
   Use `--files` to scope to the files you just added/migrated instead of
   re-reporting the vault's historical broken-link backlog.

Usage:
  python3 vault-integrity-check.py <vault_dir>
  python3 vault-integrity-check.py <vault_dir> --files builders/*.md "concepts/主题36-xxx.md"
  python3 vault-integrity-check.py <vault_dir> --fix-corruption --dry-run

Exit code 0 = clean, 1 = problems found (so it can gate a commit).
"""
from __future__ import annotations

import argparse
import os
import re
import sys

SKIP_DIRS = {".git", ".obsidian", ".trash", "node_modules", "_archive_ignore"}
PREFIX = re.compile(r"^\s*\d+\|")
LINK = re.compile(r"\[\[([^\]|#]+)")


def walk_md(vault: str):
    for dirpath, dirnames, filenames in os.walk(vault):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".md"):
                yield os.path.join(dirpath, name)


def nested_prefix_issue(text: str) -> bool:
    for line in text.split("\n"):
        if PREFIX.match(line) and PREFIX.match(PREFIX.sub("", line, count=1) or ""):
            return True
    return False


def strip_all_prefixes(text: str) -> tuple[str, int]:
    out, changed = [], 0
    for line in text.split("\n"):
        orig, cur = line, line
        while PREFIX.match(cur):
            cur = PREFIX.sub("", cur, count=1)
        if cur != orig:
            changed += 1
        out.append(cur)
    return "\n".join(out), changed


def index_names(vault: str) -> dict[str, list[str]]:
    names: dict[str, list[str]] = {}
    for path in walk_md(vault):
        stem = os.path.splitext(os.path.basename(path))[0]
        names.setdefault(stem, []).append(path)
    # non-md assets are legitimate link targets too (image embeds)
    for dirpath, dirnames, filenames in os.walk(vault):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if not name.endswith(".md"):
                names.setdefault(name, []).append(os.path.join(dirpath, name))
    return names


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("--files", nargs="*", default=None,
                    help="scope linkcheck to these files (paths relative to vault or absolute)")
    ap.add_argument("--no-corruption", dest="corruption", action="store_false")
    ap.add_argument("--fix-corruption", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vault = os.path.abspath(os.path.expanduser(args.vault))
    problems = 0

    if args.corruption:
        print("== 1. read_file 前缀污染扫描 ==")
        dirty = []
        for path in walk_md(vault):
            text = open(path, encoding="utf-8", errors="ignore").read()
            line = text.split("\n", 1)[0]
            if nested_prefix_issue(text):
                dirty.append(path)
                rel = os.path.relpath(path, vault)
                if args.fix_corruption:
                    fixed, changed = strip_all_prefixes(text)
                    if args.dry_run:
                        print(f"  [dry-run] {rel}: 会剥掉 {changed} 行前缀")
                    else:
                        open(path, "w", encoding="utf-8").write(fixed)
                        print(f"  fixed   {rel}: 剥掉 {changed} 行前缀")
                else:
                    print(f"  DIRTY   {rel}")
        if args.dry_run and dirty:
            problems += len(dirty)
        elif dirty and not args.fix_corruption:
            problems += len(dirty)
        if not dirty:
            print("  clean: 没有嵌套行号前缀")

    # linkcheck: scope or whole vault
    print("== 2. wikilink 解析检查 ==")
    names = index_names(vault)
    if args.files:
        targets = []
        for f in args.files:
            p = f if os.path.isabs(f) else os.path.join(vault, f)
            if os.path.isfile(p):
                targets.append(p)
            else:
                print(f"  !! 找不到文件: {f}")
                problems += 1
    else:
        targets = list(walk_md(vault))

    broken = []
    for path in targets:
        text = open(path, encoding="utf-8", errors="ignore").read()
        for raw in LINK.findall(text):
            ref = raw.strip()
            base = os.path.splitext(os.path.basename(ref))[0]
            if base in names:
                continue
            if os.path.exists(os.path.join(vault, ref)):
                continue
            if os.path.exists(os.path.join(vault, base + ".md")):
                continue
            broken.append((os.path.relpath(path, vault), ref))
    for f, ref in broken:
        print(f"  BROKEN  {f} -> [[{ref}]]")
    print(f"  检查 {len(targets)} 个文件，断链 {len(broken)} 条")
    problems += len(broken)

    print("== 结论 ==")
    print("  clean" if problems == 0 else f"  {problems} 处问题")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
