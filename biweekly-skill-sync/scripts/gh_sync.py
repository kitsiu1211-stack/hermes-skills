#!/usr/bin/env python3
"""Push skill files to GitHub via the Git Data API.

Why: on this machine `git clone`/`git push` to github.com times out (port 443 blocked),
but `gh api` works. One commit per manifest entry, ref updated by fast-forward.

Usage:
    python3 gh_sync.py <owner/repo> <manifest.json>

manifest.json:
    {"commits": [ {"message": "...", "files": [ {"local": "/abs/path",
                                                 "path": "repo/relative/path",
                                                 "sanitize": true|false} ]} ]}

`sanitize: true` rewrites real credentials to placeholders before upload
(mirror keeps the sanitized copy; the local working copy is left untouched).
"""
import base64
import json
import re
import subprocess
import sys
import time

SECRET_PATTERNS = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-]{20,}"), r"\1<your-token-here>"),
    (re.compile(r"(sk-)[A-Za-z0-9_\-]{20,}"), r"\1your-api-key-here"),
]


def gh(endpoint, method="GET", payload=None):
    cmd = ["gh", "api", endpoint, "-X", method]
    if payload is not None:
        cmd += ["--input", "-"]
    last = None
    for attempt in range(3):
        p = subprocess.run(
            cmd,
            input=json.dumps(payload).encode() if payload is not None else None,
            capture_output=True,
        )
        if p.returncode == 0:
            out = p.stdout.decode().strip()
            return json.loads(out) if out else {}
        last = p.stderr.decode().strip()
        time.sleep(2 + attempt * 3)
    raise RuntimeError("gh api %s %s failed: %s" % (endpoint, method, last))


def blob_sha(repo, data):
    r = gh(
        "repos/%s/git/blobs" % repo,
        "POST",
        {"content": base64.b64encode(data).decode(), "encoding": "base64"},
    )
    return r["sha"]


def main():
    repo, manifest_path = sys.argv[1], sys.argv[2]
    manifest = json.load(open(manifest_path))
    info = gh("repos/%s" % repo)
    branch = info["default_branch"]
    ref = gh("repos/%s/git/ref/heads/%s" % (repo, branch))
    parent = ref["object"]["sha"]
    base_tree = gh("repos/%s/git/commits/%s" % (repo, parent))["tree"]["sha"]
    print("repo=%s branch=%s parent=%s" % (repo, branch, parent[:8]))

    for entry in manifest["commits"]:
        tree_entries = []
        for f in entry["files"]:
            data = open(f["local"], "rb").read()
            if f.get("sanitize"):
                txt = data.decode("utf-8")
                for pat, rep in SECRET_PATTERNS:
                    txt = pat.sub(rep, txt)
                data = txt.encode("utf-8")
            sha = blob_sha(repo, data)
            tree_entries.append(
                {"path": f["path"], "mode": "100644", "type": "blob", "sha": sha}
            )
            print("   blob %-58s %6d B" % (f["path"], len(data)))
        tree = gh(
            "repos/%s/git/trees" % repo,
            "POST",
            {"base_tree": base_tree, "tree": tree_entries},
        )["sha"]
        commit = gh(
            "repos/%s/git/commits" % repo,
            "POST",
            {"message": entry["message"], "tree": tree, "parents": [parent]},
        )["sha"]
        gh(
            "repos/%s/git/refs/heads/%s" % (repo, branch),
            "PATCH",
            {"sha": commit, "force": False},
        )
        print("  COMMIT %s  %s" % (commit[:10], entry["message"].split("\n")[0]))
        parent = commit
        base_tree = tree
    print("DONE %s -> %s" % (repo, parent))


if __name__ == "__main__":
    main()
