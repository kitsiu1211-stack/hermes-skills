# Updating Hermes on a live gateway host

Use when the user approves a Hermes update while the agent is running inside the gateway (Feishu/Telegram/etc.). The gateway restart is the event that matters: it takes your own process down, so every step below is ordered around surviving it.

## 0. Answer the status question with evidence first

Before claiming an update happened or is running, check all four:

```bash
hermes --version                                   # parse the first line: vX.Y.Z (date) · upstream <sha> · local <sha>
ps ax | grep -i "hermes.*update" | grep -v grep    # empty = nothing running
ls -la ~/.hermes/.hermes-update-in-progress.lock ~/.hermes/.backup.lock 2>&1
tail -20 ~/.hermes/logs/update.log                 # last run's outcome
```

`hermes --version` unchanged plus a lock file whose mtime matches the last failed attempt = a dead run, not an in-progress one. Say that plainly; do not imply progress that isn't there.

## 1. Preflight (read-only)

```bash
cd ~/.hermes/hermes-agent && hermes update --plan
```

Shows install kind, profiles, every service to be restarted and its PID/supervisor. If the plan lists a gateway, assume this conversation dies when the update starts.

Clear stale locks only after the `ps` check came back empty:

```bash
rm -f ~/.hermes/.hermes-update-in-progress.lock ~/.hermes/.backup.lock
```

## 2. Fix the remote if fetches truncate

Symptom in `update.log`: `Failed to fetch updates from origin. error: N bytes of body are still expected`.

```bash
cd ~/.hermes/hermes-agent && git remote -v
curl -sS -o /dev/null -w 'github.com HTTP %{http_code} in %{time_total}s\n' --max-time 12 https://github.com
GIT_TERMINAL_PROMPT=0 git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=10 \
  ls-remote https://github.com/NousResearch/hermes-agent.git HEAD
```

If official GitHub responds, point `origin` at it (there is no `--source` / `--mirror` flag on `hermes update`):

```bash
git remote set-url origin https://github.com/NousResearch/hermes-agent.git
```

`git ls-remote` succeeding against upstream while `origin/main` is old is normal — the local ref only updates on fetch.

## 3. Launch detached with a grace delay

macOS ships no `setsid` binary, and `nohup` alone keeps the process in the gateway's process group, so `launchctl kickstart -k` on the gateway can take the updater down with it. Fork a new session:

```python
import subprocess, os
log = os.path.expanduser("~/.hermes/logs/update-<stamp>.log")
f = open(log, "w")
p = subprocess.Popen(
    ["/bin/bash", "-lc", "sleep 25; exec hermes update --yes"],
    stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
    start_new_session=True, cwd=os.path.expanduser("~/.hermes/hermes-agent"))
print("detached pid", p.pid, "log", log)
```

- The `sleep 25` is load-bearing: it lets the current turn finish and deliver its reply before the gateway goes down.
- `--yes` accepts config-migration and stash-restore prompts non-interactively; run `hermes config migrate` separately afterwards only if the update reports pending API-key entries.
- Do not use `--no-gateway-restart` when the goal is to run the new code — the old gateway keeps serving old code.

## 4. Tell the user before the process dies

Use the platform CLI directly so delivery does not depend on the agent loop that is about to be killed:

```bash
lark-cli im +messages-send --chat-id '<chat_id>' --as bot \
  --text '开始更新了：源已切到 GitHub 官方，25 秒后动手。过程中网关会重启，可能断几分钟。跑完我把版本号发你。'
```

Check the JSON for `"ok": true`; that is the delivery receipt, not the tool call returning.

## 5. Completion watcher (outlives the restart)

A detached watcher can report the outcome while the agent itself is offline:

```python
import subprocess, time, json, os

CHAT = os.environ.get("REPORT_CHAT", "<chat_id>")

def ver():
    return subprocess.run(["hermes", "--version"], capture_output=True, text=True,
                          timeout=60).stdout.splitlines()[0].strip()

def updating():
    out = subprocess.run(["/bin/ps", "-axo", "command"], capture_output=True, text=True).stdout
    return "hermes update" in out

deadline = time.time() + 22 * 60
time.sleep(60)
while time.time() < deadline and updating():
    time.sleep(20)
time.sleep(10)
text = f"更新跑完了。当前版本：{ver()}\n如果飞书这边正常回复，就说明网关已带着新代码起来了。"
subprocess.run(["/bin/bash", "-lc",
    f"lark-cli im +messages-send --chat-id {CHAT} --as bot "
    f"--idempotency-key update-report-<stamp> --text {json.dumps(text, ensure_ascii=False)}"],
    capture_output=True, text=True, timeout=90)
```

Launch it the same way (`start_new_session=True`), log to `~/.hermes/logs/update-watch.log`. The idempotency key makes a retry safe.

## 6. Verify afterwards

```bash
hermes --version             # first line is the deliverable
hermes update --plan         # should now report the new sha, nothing pending
grep -c "feishu.*connected" ~/.hermes/logs/gateway.log  # platform actually came back
```

Report the version string and the platform state. A restart that comes back with no messaging adapters loaded looks identical to success from the version string alone — confirm the platform line too.

## Pitfalls

- Never report "updated" from the updater's exit code; the version string is the only evidence.
- A gateway restart can come back with `No messaging platforms enabled.` and need a second restart — the platform log line is the check, not the PID.
- Deleting the lock files before the `ps` check can corrupt a genuinely running update.
- `timeout` is not available on macOS; bound probes with `curl --max-time` / git's `http.lowSpeedTime`.
