#!/usr/bin/env python3
"""Audit a dual-vault Obsidian setup: which files exist on only one side, which
diverged, and which wikilinks are actually broken (with a fixable/missing split).

Usage:
    dual-vault-audit.py <primary_vault> <mirror_vault> [--only-mirror-files]

Why a script: hand-rolled `diff -r` can't tell "mirror-only draft" from
"diverged shared file", and naive wikilink checkers count image embeds and doc
examples as broken links. Both mistakes produce numbers you'll get argued with.

Design notes baked in:
  * Only *.md are compared (mirror may carry .obsidian/ and assets/ noise).
  * A wikilink to a NON-md target (![[x.png]]) is valid if that file exists on
    disk — checked via a real filesystem walk, not the .md index.
  * Broken links are split into "fixable" (target exists, link text drifted:
    spaces/hyphens differ) vs "missing" (target genuinely absent).
"""
import hashlib
import os
import re
import sys
import urllib.parse

LINK = re.compile(r"!?\[\[([^\]]+?)\]\]")
SKIP_DIRS = {".git", ".obsidian", ".trash", ".git_private"}


def walk_any(root, ext=None):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if ext and not f.endswith(ext):
                continue
            full = os.path.join(dirpath, f)
            out[os.path.relpath(full, root)] = full
    return out


def norm(s):
    """Fold case/spaces/punctuation so 'Skill 路由表' == 'Skill路由表'."""
    return re.sub(r"[\s\-_—–·・（）()、，,。.]", "", s).lower()


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    primary, mirror = (os.path.abspath(p) for p in sys.argv[1:3])

    mds_p = walk_any(primary, ".md")
    mds_m = walk_any(mirror, ".md")

    def digest(path):
        return hashlib.md5(open(path, "rb").read()).hexdigest()

    h_p = {k: digest(v) for k, v in mds_p.items()}
    h_m = {k: digest(v) for k, v in mds_m.items()}

    main_only = sorted(set(h_p) - set(h_m))
    mirror_only = sorted(set(h_m) - set(h_p))
    diverged = sorted(k for k in set(h_p) & set(h_m) if h_p[k] != h_m[k])

    print(f"primary: {primary}  ({len(mds_p)} md)")
    print(f"mirror : {mirror}  ({len(mds_m)} md)\n")
    print(f"[main_only]   {len(main_only)}  (mirror missing -> plain rsync fixes)")
    for k in main_only:
        print("   M>", k)
    print(f"\n[mirror_only] {len(mirror_only)}  (drafts; decide whether to migrate back)")
    for k in mirror_only:
        print(f"   R> {k}  ({os.path.getsize(mds_m[k])}B)")
    print(f"\n[content_diff] {len(diverged)}  (same path, different bytes)")
    for k in diverged:
        newer = "MIRROR" if os.path.getmtime(mds_m[k]) > os.path.getmtime(mds_p[k]) else "PRIMARY"
        print(f"   ~ {k}  ({newer} newer)")

    # ---- wikilink health, per vault -------------------------------------
    all_files_p = walk_any(primary)          # any extension, for embed checks
    all_files_m = walk_any(mirror)

    def broken(root, mds, all_files, subset=None):
        file_norms = {norm(os.path.basename(p)): p for p in all_files}
        base_norms = {}
        for rel in mds:
            base_norms.setdefault(norm(os.path.basename(rel)[:-3]), []).append(rel)
        out = []
        for rel, path in sorted(mds.items()):
            if subset is not None and rel not in subset:
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
            text = re.sub(r"```.*?```", "", text, flags=re.S)   # fenced code
            for hit in LINK.finditer(text):
                tgt = hit.group(1).split("|")[0].split("#")[0].split("^")[0].strip()
                if not tgt:
                    continue
                tgt = urllib.parse.unquote(tgt)
                base = os.path.basename(tgt)
                stem = base[:-3] if base.endswith(".md") else base
                if stem in base_norms or norm(stem) in file_norms:
                    continue
                out.append((rel, tgt))
        return out

    for label, root, mds, allf, subset in (
        ("PRIMARY", primary, mds_p, all_files_p, None),
        ("MIRROR", mirror, mds_m, all_files_m, set(mirror_only) or None),
    ):
        rows = broken(root, mds, allf, subset)
        file_norms = {norm(os.path.basename(p)): p for p in allf}
        fixable, missing = [], []
        for src, tgt in rows:
            hit = file_norms.get(norm(os.path.basename(tgt)))
            (fixable if hit else missing).append((src, tgt, hit))
        scope = "mirror-only files" if subset else "all files"
        print(f"\n[broken links · {label} · {scope}] total {len(rows)} "
              f"= fixable {len(fixable)} + missing {len(missing)}")
        for src, tgt, hit in fixable:
            print(f"   FIX  {src}: [[{tgt}]] -> {hit}")
        for src, tgt, _ in missing:
            print(f"   MISS {src}: [[{tgt}]]")


if __name__ == "__main__":
    main()
