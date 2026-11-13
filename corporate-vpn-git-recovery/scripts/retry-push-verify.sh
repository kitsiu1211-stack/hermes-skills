#!/bin/bash
# 恢复企业 VPN 后补推并验证远端。
# 用法: retry-push-verify.sh "<repo-dir>" <owner>/<repo> [branch]
# 退出码: 0=远端已确认含本地 HEAD；1=push 失败；2=push 后远端 SHA 不匹配；3=参数/环境问题
set -u

REPO_DIR="${1:-}"
SLUG="${2:-}"
BRANCH="${3:-main}"

if [ -z "$REPO_DIR" ] || [ -z "$SLUG" ]; then
  echo "usage: $0 \"<repo-dir>\" <owner>/<repo> [branch]" >&2
  exit 3
fi
cd "$REPO_DIR" || { echo "repo not found: $REPO_DIR" >&2; exit 3; }

LOCAL_SHA=$(git rev-parse --short HEAD)
AHEAD=$(git rev-list --count "origin/$BRANCH..HEAD" 2>/dev/null || echo "?")
echo "repo      : $REPO_DIR"
echo "local HEAD: $LOCAL_SHA"
echo "ahead of origin/$BRANCH: $AHEAD"

# 1) 连通探测（失败不直接退出，push 仍可能成功；但先告诉人）
API_CODE=$(curl -sS -m 8 -o /dev/null -w '%{http_code}' https://api.github.com 2>/dev/null || echo "000")
echo "api.github.com: $API_CODE"
echo "gh auth       : $(gh auth status 2>&1 | grep -m1 -o 'account [^(]*' | head -1)"

# 2) 补推（不要用 timeout —— 本机没有该命令）
echo "--- git push ---"
if ! GIT_TERMINAL_PROMPT=0 git push origin "HEAD:$BRANCH" 2>&1 | tail -6; then
  echo "PUSH FAILED — 检查 VPN 是否真的连上（飞连=CorpLink，菜单栏常驻无窗口）" >&2
  exit 1
fi

# 3) 本地复核
AHEAD_AFTER=$(git rev-list --count "origin/$BRANCH..HEAD")
echo "ahead after push: $AHEAD_AFTER"
if [ "$AHEAD_AFTER" != "0" ]; then
  echo "本地仍领先 $AHEAD_AFTER 个 commit" >&2
  exit 1
fi

# 4) 远端 API 复核（push 输出不算证据）
REMOTE_SHA=$(gh api "repos/$SLUG/commits/$BRANCH" --jq '.sha' 2>/dev/null | cut -c1-"${#LOCAL_SHA}")
echo "remote  HEAD: ${REMOTE_SHA:-<api failed>}"
if [ "${REMOTE_SHA:-}" != "$LOCAL_SHA" ]; then
  echo "远端 SHA 与本地不一致（或 API 取不到）——不要向用户宣称已推送" >&2
  exit 2
fi

echo "OK: https://github.com/$SLUG/commit/$LOCAL_SHA"
