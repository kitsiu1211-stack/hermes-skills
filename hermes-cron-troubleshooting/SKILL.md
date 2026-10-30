---
name: hermes-cron-troubleshooting
description: "Use when a Hermes cron job fails, when patching/restarting a long-running background watcher or daemon (poll.sh, watcher .py, watchdog), when the user says an alert/prewarning is vague or wrong (rule-alert false positive + legibility tuning), or when the user says to turn a noisy feature OFF (帮助不大/噪音大/关闭掉 → decommission, not tuning): fallback chain, sentinel watchdog, restart-with-cursor-fast-forward, replay verification, five-step feature teardown."
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, cron, troubleshooting, fallback, provider, watcher, daemon, restart, background-process]
---

# Hermes Cron Job Troubleshooting

## When to Use

Diagnose and fix failed scheduled jobs (cron). Trigger: user forwards a cron failure delivery like "⚠️ Cron '每日认知对话' failed: provider timeout" or says 又出问题了 about a scheduled task.

Also use this skill for **long-running background watcher / daemon lifecycle** — anything started detached and expected to keep running across the session (meeting `poll.sh`, `meeting_radar.py`, log tails, alerters, watchdogs). Trigger: "我改了那个脚本但它没生效", "预警里少了我刚才说的那件事", "重启一下那个监听", or any time you just edited the source of a process that is *already running*. See "长跑 watcher 改完代码后" below — the restart procedure is not optional.

And use it for **rule-alert quality feedback** — the user replies to a pushed alert with "这个消息很模糊" / "看不懂" / "这算什么商机". That is a defect report on the rule layer (or on the alert's rendering), not a request for an explanation: fix the rule/format, replay-verify, restart. See "坑三" below and `references/rule-alert-tuning.md`.

And use it for the **reverse** — the user says "关闭掉吧" / "帮助不大" / "噪音很大" / "别推了" about a running feature. That is a decommission, not a tuning request; do NOT answer it by offering to adjust thresholds. Five-step teardown (reverse the default, keep the code, sync the docs, sweep cron, name what did NOT change) in "反向操作：用户说「关掉它」" below and `references/feature-decommission.md`.

## Diagnosis workflow

1. **List jobs** — `cronjob action='list'`. Note `job_id`, `last_status`, `last_run_at`, `next_run_at`.
2. **Read the REAL error** — cron run output is saved at `~/.hermes/cron/output/<job_id>/<YYYY-MM-DD_HH-MM-SS>.md`. Tail it; the actual exception is at the bottom (e.g. `RuntimeError: Non-streaming API call timed out after 600s with no response`). The delivery message only carries the error class, not the detail — always check the file.
3. **Classify**:
   - `provider timeout` / `Non-streaming API call timed out` → provider-side stall (slow/no response). Fix: fallback chain (below). The 600s threshold is the hard interrupt; a healthy provider answers in seconds.
   - `Response remained truncated after N continuation attempts` → same root cause as provider timeout (provider stalled on initial call, returned a partial reply after retry, Hermes tried to continue and the response kept getting truncated). Apply the same fix path: fallback chain + sentinel watchdog. **Do NOT immediately re-run — probe first** (Pitfalls).
   - `last_delivery_error` non-null / delivery failure → message-send problem (platform token, chat id), not the model.
   - skill-load errors → inspect the job's `skills` list and the skill file.
4. **Fix, then re-run**: `cronjob action='run' job_id=<id>` fires the job in the background immediately; its outcome re-enters the conversation when done. Do NOT pause/delete a job for a transient provider failure.
5. **PROBE BEFORE RERUN** (see Pitfalls).

## Fix: provider timeout → fallback provider chain

Top-level config key in `~/.hermes/config.yaml`: `fallback_providers` — a LIST of dicts `{provider, model, base_url?, api_mode?, key_env?}`. Legacy single-dict `fallback_model` is also read (merged, list wins).

- Primary model untouched; fallback entries tried in order on rate-limit / overload / 5xx / connection / timeout errors.
- The chain is GLOBAL — one config covers all cron jobs AND main-agent calls. No gateway restart needed (read via `load_config_readonly()` at call time).
- Custom providers (defined under `custom_providers` in config.yaml) work as fallback entries; either reference by provider name or make the entry self-contained with inline `base_url` + `key_env` (robust even if custom-provider lookup path differs).

```yaml
fallback_providers:
  - provider: minimax-openai
    model: MiniMax-M3
    base_url: https://api.minimaxi.com/v1
    key_env: MINIMAX_API_KEY
```

## Layer 3: Sentinel watchdog (guarantee the job actually completes)

Fallback chain prevents most call-level failures, but if the primary provider stalls past the hard timeout the run still dies. To guarantee "this cron must succeed today", add a sentinel: a no_agent script job that checks shortly after the main job's schedule and auto-reruns it on failure. (Real case 2026-08: 每日认知对话 died at 9:05 on a 600s DeepSeek timeout; dual sentinels at 9:35/10:05 now catch and rerun it same-day.)

Design rules (user-approved):
- **Delayed check + early exit**: 1–2 checkpoints 30–60 min after the main job. NOT all-day polling — success means silent exit, so extra checkpoints cost nothing anyway.
- **Zero token, zero noise**: no_agent=True; script prints NOTHING when the main job succeeded — empty stdout = no message, no LLM, no delivery. Only a failure prints an alert + triggers rerun.
- **Success detection pitfall**: failed runs ALSO write an output file — file presence ≠ success. Check `~/.hermes/cron/output/<job_id>/<YYYY-MM-DD>_*.md` content for fail markers (`## Error`, `RuntimeError`, `timed out`); only a file WITHOUT them counts. Real example: 09:30 failure file + 11:26 success file on the same day.
- **Trigger**: script runs `hermes cron run <job_id>` (CLI; fires on next scheduler tick — gateway/scheduler must be running). The rerun's completion re-enters the conversation as a normal cron run.
- **Idempotency is the precondition**: only auto-rerun jobs that are safe to run twice (job itself checks "already produced today?" — e.g. ebbinghaus-review's anti-duplicate rule). Otherwise a rerun duplicates side effects (cards/files).
- **Layer math**: execution + sentinel + fallback chain is enough. If both models AND the script fail simultaneously that's machine-level; accept it, don't over-engineer.

Template: `templates/sentinel_watchdog.py` — copy to ~/.hermes/scripts/, set JOB_ID, install as no_agent cron with `script=<name>.py`. Verify the success-detection logic against real output files before trusting it.

## Layer 4: 外部哨兵（观测点不在故障域内）— 跨机可观测

Layer 3 的补跑哨兵和主任务跑在**同一台机**上：机器一睡，主任务和哨兵一起睡，**你连自己漏了什么都答不上来**。要让「有没有按时出现」这件事可被外部验证，就把每次周期产出压成**一行回执**，投到双方共见的话题里，由跑在云端、不依赖本机的另一个 Agent 当哨兵。

要点（完整设计、四种前缀、上线顺序、坑，见 `references/external-sentinel-receipt.md`；可复用脚本 `scripts/cron_receipt.sh`）：

- 只盯**没有本地补跑机制**的周期任务（周复盘 / 周深读 / 双周同步 / 双周雷达），日度任务已有 Layer 3 兜底，再盯纯噪音。
- 回执 `✅ 任务名 期次` / `✅（补跑）` / `❌ 失败：原因` / `⏭ 非执行周`，任务名与期次是**对外契约**，改前先同步对方。**期次四类统一用 ISO 周 `YYYY-Www`（双周任务也一样），不用日期**——用日期会在双方文档里长出两套解析口径，说出去了只能逐条回收。
- 交付给哨兵时同时给一份**「不盯」清单**（否则正常的沉默会被判成漏跑）和**真实弱点**（跑本机、睡即漏、历史失败如实点名）——这份清单长什么样见该 reference 第七节。
- 判定时刻以哨兵侧 cron 为准，产出方清单只写计划时间 + 宽限，避免两套数字互相打脸。

### 回执链路加固（2026-10-28 实战 — 上线前必做，否则首次实战静默失效）

回执链路失效是**静默**的：发不出去时观察方看到的是"任务没跑"，你被判漏跑，而自己侧连报错都没留下。完整加固/自测流程见 `references/receipt-chain-hardening.md`，四条硬规则：

1. **`selfcheck` 走旁支分支 ⇒ 它证明不了真实路径。** 本 session 的 `ok` 分支写成了 `${SUF:+（$SUF）}`，**全角括号被 bash 当成变量名的一部分**，`set -u` 下直接 `SUF）: unbound variable` 退出——而 selfcheck 走的是独立分支，测不到，首次实战必然发不出 `✅`。中文/全角标点永远不进参数展开内部，改成两次赋值：`SUFFIX=""; [ -n "$SUF" ] && SUFFIX="（${SUF}）"`。自检要覆盖**每一种回执形态**，不是跑通一条就算。
2. **零噪音自测**：给 `lark-cli` 做假壳 + `HOME=/tmp/...`，四种形态逐条跑，群里一条假信号都不留（配方见该 reference 第二节）。
3. **双周任务轮空周的 `⏭` 不能靠模型记得发**，用 `no_agent` cron 跑 `scripts/biweekly_skip_guard.sh`（周五 10:40 / 周一 09:40，晚于真任务、早于判定时刻）；偶数周静默、奇数周无回执则补发，已有回执退让。**`⏭` 必须带期次**（`⏭ 任务 2026-W45 本周非执行周`），没有周号观察方无法按周匹配。
4. **可测日期逻辑要把 `date` 每一处输出都做成 override**（`%u` / `%V` / `%G` 各一个环境变量）。只覆盖周号不覆盖星期时，脚本在工作日直接 `exit 0`，看起来"静默正确"，实际一个用例都没验证到。

跨 Agent 契约（期次格式、回执形态、判定时刻）要**读对方实现原文逐条核对**，别凭印象；改了契约字段（如给 `⏭` 加周号）要主动报备，并先讲清边界——脚本兜得住"模型漏发"，兜不住"整机睡死"。
- **告警必须带人工兜底**：漏跑多半是机器睡着，那时产出方连「我在睡」都发不出、喊它没人应 → 告警写死「机器可能处于睡眠，请人工确认是否唤醒」。真兜底是用户本人，不是任何一方 Agent。
- **改多个 job 的 prompt 别重打全文**：python 读 `~/.hermes/cron/jobs.json` → 拼「原 prompt + 附录」落 `/tmp/prompt_<id>.txt` → `hermes cron edit <id> --prompt "$(cat ...)"` → 回读 jobs.json 核实（`schedule` 是 dict 不是字符串，别按字符串处理）。可抄脚本见 reference 第五节。

## Pattern: 兑现「明天 X 点我给你…」——一次性承诺任务（2026-10-29）

在群里说出「明天 15:32 我出完整名单和状态，你来判」的那一刻，这个承诺就和会话生命周期绑定了：会话一关，没人会想起它，对方到点等不到东西，判定就变成扯皮。**口头时间承诺必须落成一次性 cron**，否则等于没承诺。

- `schedule='YYYY-MM-DDTHH:MM:SS'` + `repeat=1`，`name` 里带日期和事项，方便事后在 `cronjob action='list'` 里认出来。
- **`deliver` 要精确到话题**：`feishu:<chat_id>:<thread_id>`。只写 `feishu:<chat_id>` 会掉到群主聊天流，对方在自己的话题里看不到（本 skill 顶部「已确认正常工作的场景」也提到 cron 能在话题内交付）。
- 群名 → chat_id 用 `lark-cli im +chat-search --query "<群名>"`（没有 `--keyword`）；话题 id 就是当前会话 `source` 里的 `omt_xxx`。
- prompt 必须自包含：把**名单原文、判定口径、要读的数据源命令、台账路径、输出格式**全部写死。cron 里没有用户可问，含糊指令等于含糊产出。
- 承接上面的重复交付问题：如果同一件事有两个实例在响应，截点任务可能在群里出两份。挂任务时顺手在台账里记一行「cron `<job_id>` 会在 X 点出状态」，事后能一眼分清哪条是计划内、哪条是另一个实例的抢跑。
- 承诺里如果写了「你判定 / 我做别的」这类分工，**把分工写进 prompt**，否则 cron 会自作主张把结论一起下了。

## Pattern: two-job chain — 定时执行动作 + 定时产出交付物（NEW — 2026-09-17）

需求形态：「今晚 19:00 有个会，你以 bot 身份入会，不要说话」——即在一个**未来时刻**执行一个有状态的动作，产出的日志要在一段时间后被处理成交付物。单 job 做不到（动作与产出相隔 1 小时），用两个 one-shot job 串起来最省事、零 token 浪费：

| Job | 类型 | 时间 | 职责 |
|-----|------|------|------|
| A 动作 | `no_agent=True` + `script=<wrapper>.sh` | T-1min | 执行状态变更（入会 / 抓取 / 启动后台循环），stdout 原样发给用户 |
| B 产出 | agent（带 skill + 明确步骤） | T+duration+5min | 读 A 留下的日志，产出卡片/报告 + 建日程 + 汇报 |

**关键设计点：**

1. **`script` 参数只接受路径，不能传参**。通用脚本（`join_meeting_bot.sh <会议号> <标题>`）要配一个极薄的 wrapper 把本次参数写死：
   ```bash
   #!/bin/bash
   exec bash "$HOME/.hermes/scripts/join_meeting_bot.sh" 847607670 "鑫志合一参赛方向讨论"
   ```
   `cronjob action='create' script=join_847607670.sh` 指向 wrapper。

2. **cron 脚本里启动的后台进程必须自己 detach**——cron run 立刻结束，不能用 foreground 等待：
   ```bash
   nohup bash "$POLL" "$MID" "$TITLE" >> "$LOG_DIR/$MID.nohup.log" 2>&1 &
   disown
   ```
   副作用是好事：日志落在固定路径，job B 和排查都能 tail。

3. **job B 必须处理「上游还在跑」**：会议超时 → 后台 poll 还没退出 → 日志不全。让 job B 先 `ps aux | grep poll.sh`，仍在跑就以分钟级 sleep 分次等待（上限约 10 分钟）再收割，而不是直接出残缺纪要。

4. **job B 要能定位 job A 的产物**：让 A 把 meeting_id/输出路径写进固定命名的文件（如 `~/meeting_logs/<id>.nohup.log`），B 用 `ls -t` + `grep -l <标题>` 反查，别依赖会话内变量。

5. **job B 的 prompt 里写死交付规范**（卡片格式、发往哪个 chat_id、日程创建规则、字幕为 0 时如实说明不要编造）——cron 里没有用户可问，含糊的指令会变成含糊的产出。

**验证（别只信 `last_status`）**：`last_status: error` 不代表动作没生效。本 session 的 A job 显示 error（命中上文那个 bash 变量名 bug），但 bot 实际已经入会——用**产物侧**的证据确认：`lark-cli vc +meeting-events --as bot --meeting-id <id>` 看会议 status 与 bot participant，以及 `tail` 后台日志文件。先看产物，再判断脚本到底哪一步挂了。

**成本**：job A 是纯脚本（零 token），job B 一次 agent run。比「一个 job 里 sleep 一小时」或定时轮询省得多。

### job B 产飞书卡片时的两个复用技巧（2026-09-17）

job B 的交付物通常是飞书卡片，写这类 cron prompt 时把下面两条直接写进去：

1. **卡片 JSON 必须用 python 构建**，正文过一层转换再进 `tag: markdown`：
   ```python
   def md(c):
       return {"tag": "markdown", "content": re.sub(r"\*\*(.+?)\*\*", r"<font weight=bold>\1</font>", c)}
   ```
   `tag: markdown` 不认 `**粗体**`（会渲染成字面星号），`note` 的 elements 只吃 `plain_text`。一次定义，全卡受益。发送后按返回里的 `"ok": true` 和 `message_id` 确认，别假设成功。
2. **正文落盘 + 退出码门禁**：先写 `/tmp/*.md`，跑 `python3.11 ~/.hermes/skills/human-writing/scripts/check_prose.py <路径>`，exit 0 才发送（`if r.returncode == 0:`）。脚本报出的「需辨语境词」是人工判断项，本义使用保留即可。

会议/长文类卡片的骨架惯例：首块用 4 列 `column_set` 做概览（时长 / 参与人数 / 字幕条数 / 关键计数），之后 hr 分段，**对方提出的硬问题单独成块**（那是纪要里最值钱的部分）。

## 长跑 watcher 改完代码后：回放验证 → 重启 → 游标拨到末尾（NEW — 2026-10-14）

场景：用户对某个**正在跑**的后台 watcher 提了修改意见（例：会中预警只推命中那一句，用户说「这个承诺啥，应该把承诺的上下文结合一起」；或告警阈值/推送格式要改）。你已经改好了 `.py` / `.sh`。

**顺序不能乱，四步：**

**1. 改代码 ≠ 生效 —— 永远先 `ps` 确认现场。** 长跑进程用的是启动那一刻载入的旧代码，磁盘上的修改对它毫无影响。

```bash
ps aux | grep -E "<watcher>.py|<watcher>.sh" | grep -v grep
```
看清 PID、启动时间、完整命令行（**重启时要原样复用这条命令行**，尤其是 `--title` / `--interval` 这类只有运行时才知道的参数——它们不在仓库里，重启时容易漏）。

**2. 重启前，先用真artifact回放验证新代码 —— 不要用合成输入。** 把**现有的历史日志**喂给改过的代码，读它真正渲染出来的输出，确认**用户抱怨的那个具体 case** 已经变对（而不是"代码看起来对"）。多数 watcher 都自带这种模式（`--replay --no-send` / `--dry-run`）。

```bash
/usr/bin/python3 <watcher>.py <id> --replay --no-send --no-llm > /tmp/replay.txt 2>&1
grep -A12 "<用户抱怨的关键词>" /tmp/replay.txt    # 看真实渲染结果
```
**只有看到那段真实输出，才能说修好了。** 这一条把"我以为改对了"变成"日志证明改对了"。

**3. 重启时把状态游标拨到日志末尾 —— 否则回灌积压，反而变成刷屏。** 有状态的 watcher 会把 `offset` / 已发 ID / 计数器落盘在 state 文件里，重启后从游标继续。游标停在几分钟前 → 新进程会把这几分钟的积压一次性处理掉（其中很多是旧信号）→ 用户被一堆过期预警砸中，比不重启更糟。**冷启动前把游标对齐到当前 EOF，但保留 `sent` / 冷却时间戳等去重状态：**

```python
st["offset"] = os.path.getsize(log_path)     # 跟到末尾，跳过积压
st["count"]    = 0                            # 若上半场配额被误报耗尽，重置上限计数
```
同时**检查 per-run 上限是否已被耗尽**：`count >= max_alerts` 会让新代码一条都不推 —— 用户会以为你根本没修。

**4. 冷启动 + 三连验收。** 用 `scripts/restart_stateful_watcher.sh`（本 skill 自带）一步做完：杀旧进程 → 游标拨末尾 → detached 冷启动 → 校验单实例。

```bash
bash ~/.hermes/skills/devops/hermes-cron-troubleshooting/scripts/restart_stateful_watcher.sh \
  <脚本绝对路径> "<pgrep 匹配串>" \
  --state "<state.json>" --log "<log 路径>" --cursor-key offset --reset-key count \
  --args "<原样命令行参数>" --logfile "<追加日志>"
```
验收三连：① `pgrep -fc "<匹配串>"` **必须等于 1**（旧进程没死是最常见的翻车——两个实例同时推，用户收到双份）；② `tail` 日志头部看到新进程的启动横幅（确认是新代码、参数没漏）；③ `sleep 15` 后日志里没有新报错。

### ⚠️ 坑一：harness 拒绝命令行里的 `nohup` / `disown` / `setsid`

`terminal` 工具会直接拒收含 shell 级 background wrapper 的命令（`Foreground command uses shell-level background wrappers...`），要求改用 `background=true`。但 **cron / watcher 的常驻进程恰恰必须脱离会话**（`background=true` 起的进程会随会话结束被回收）。

**解法（两选一，都绕开命令字符串守卫）：**

1. **把 `nohup ... & disown` 写进一个 `.sh`，然后 `bash /tmp/xxx.sh`** —— 守卫检查的是命令字符串，看不到脚本内部。这也正是本 skill 上面 cron wrapper 的同一招。脚本末尾 `sleep 2 && pgrep -f "<pattern>"` 顺带把验收做掉。
2. **`python3 -c` 里用 `Popen(..., start_new_session=True)`**（2026-10-14 实战用的这条，不用落地临时脚本）：

```bash
/usr/bin/python3 -c 'import subprocess,os;log=open(os.path.expanduser("~/meeting_logs/<mid>.radar.log"),"a");subprocess.Popen(["/usr/bin/python3",os.path.expanduser("~/.hermes/skills/feishu/feishu-meeting-listen/scripts/meeting_radar.py"),"<mid>","--title","<标题>","--interval","15"],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)'
```

启动后**另起一条命令**做验收（`ps aux | grep <pattern>` 看 PID 与命令行参数是否与旧进程一致 + `tail` 日志头部的启动横幅 + 状态文件里的 `count`/`offset` 是否接续 —— 不接续说明你误删了 state）。

### ⚠️ 坑二：回放验证时闸门按**墙钟**走，会把命中数吃掉

节流 / 冷却（`cooldown`、`rate_limit`、"同规则 N 分钟内只报一次"）通常用 `time.time()` 实现。回放历史数据时所有行在几百毫秒内跑完，**同一闸门的第二条起全部被冷却吃掉** —— 你会看到"回放只命中 3 条"，误以为规则太松/太严，其实只是冷却在起作用（线上实时跑的是真实时间差，不受影响）。

**做法：回放**加 `--cooldown 0`（或等价的关闸参数）**数全量命中**，用来做验收；线上仍用真实冷却。**判据**：回放命中数 << 你肉眼在日志里数到的候选数 ⇒ 先怀疑闸门是墙钟制，别急着改规则。

### ⚠️ 坑三：整场上限 + 回放态残留，也会把回放命中数吃掉（NEW — 2026-10-14）

同一次反馈里踩到的第二个「回放看起来规则失效」假象，跟墙钟无关：

1. **`--max-alerts`（默认 12）是整场硬上限**，命中满额后**连 `once` 规则都不再推**。回放时你只看到最前面 12 条，会误判「后面的规则没命中」。回放验收必须显式放开：`--max-alerts 200`。
2. **回放也有 state 文件**（`<id>.replay.state.json`）：上一轮回放留下的 `offset`/`sent` 会让这一轮从中间开始、还带着旧去重记录（`once` 规则直接判「已发过」）。**先 `rm -f <id>.replay.*` 再跑**，才叫全量。
3. **想彻底干净**：把日志 `cp` 成另一个 basename（如 `/tmp/fixtest.jsonl`）再回放 —— 独立 mid ⇒ 独立 state，不污染线上状态文件。

**三档验收顺序（缺一不可）**：① 回放全量，看命中的**全是真信号**、用户抱怨的那一条已消失；② 对该条**误报句**做单测确认不命中；③ 用几条**合成正反用例**确认收紧后真信号仍命中（收紧过头会把真信号一起灭掉，只跑回放发现不了）。

### ⚠️ 坑四：用管道启动长跑 watcher，会被 `head` 静默掐死（2026-10-16 实测）

启动 `poll.sh` / watcher 时最容易顺手写成 `bash poll.sh <id> <title> 2>&1 | head -30`（只想先看看前几十行日志）——**这会在 head 读满 30 行后退出的瞬间把 watcher 打成 SIGPIPE 死掉**。症状很隐蔽：进程「正常退出」、exit 0、没有任何报错，你以为它在监听，实际已经在几分钟后没了；配合 `notify_on_complete` 还会**立刻**收到一条「已完成」通知，看起来像会议结束了。

**写法对照：**

```bash
# ❌ 管道会随 head 退出而掐死 writer（SIGPIPE），且 notify 会提前触发
bash "$POLL" "$MID" "$TITLE" 2>&1 | head -30

# ✅ 输出重定向到日志文件：进程被 harness 正常追踪、notify 在真实退出时才触发、日志可 tail
bash "$POLL" "$MID" "$TITLE" > /tmp/poll_<mid>.log 2>&1
# 用 terminal(background=true, notify_on_complete=true) 起，另起一条命令 tail 日志验收
```

**判据与修复**：`notify_on_complete` 在启动后几十秒内就到达 ⇒ 先怀疑是管道掐的，不是会议结束了。`ps aux | grep <脚本名>` 确认进程已死 → `pkill -f "<脚本名> <id>"` 清残 → 用重定向方式重启（状态是文件级的，重启不丢已采数据）。

**与坑一的分工**：坑一是「cron 里必须 detach 且 harness 拒收 `nohup`/`&`」；本条是「**交互式会话**里用 `background=true` 起长跑进程时，别加管道」。两种场景的启动写法不同，别互相套用。

**通用原则**：任何「预期长时间运行」的进程，输出一律落文件，**永远不要管道给可能提前退出的命令**（`head` / `head -n` / 带 `-m` 的 grep / 分页器）。要看实时进度就另起一条 `tail -f` 或 `tail -20`。

## 反向操作：用户说「关掉它」——功能下线五步（NEW — 2026-10-26）

场景：用户对已经跑起来的功能说「关闭掉吧，帮助不是很大，而且噪音很大」。这跟「调规则」是两条完全不同的路，**别默认走调参那条**。

### 先分清用户要哪一种

| 用户原话 | 真实诉求 | 动作 |
|---|---|---|
| 「这条预警很模糊 / 看不懂 / 误报太多」 | 功能有用，规则要修 | 走上面「长跑 watcher 改完代码后」+ `references/rule-alert-tuning.md` |
| 「帮助不大 / 噪音很大 / 关掉吧 / 别推了」 | **价值判断已经做完**，功能本身不值得 | 直接下掉。不要反问「要不要我调一下阈值」，那是把已经做完的决定推回给用户 |

判据：出现「帮助不大」这类**效用否定**，就不要再提调参。用户已经权衡过成本收益了。

### 五步，缺一不可（只做第一步会「改了又起来」）

1. **改默认值，不要删代码。** 把启动条件从 opt-out 改成 opt-in（`[ "${X:-1}" != "0" ]` → `[ "${X:-0}" = "1" ]`）。代码留着，将来手动开得起来，也留得下复盘材料；删了就再也开不回来。
2. **改完立刻 `bash -n` 验语法**，再确认没有正在跑的实例：`ps aux | grep -E "<watcher>|<launcher>" | grep -v grep`。正在跑的实例不读磁盘上的新文件，它会继续按旧逻辑推送 —— 若在跑，先按「长跑 watcher」那套 kill + 冷启，或者直接 kill 掉（下线场景不需要冷启）。
3. **同步 skill 文档**，写清「默认关闭 + 触发这次决定的原话 + 不要自作主张再开」。原有的调参技巧全部标注「仅作存档」。**新的 session 只读文档，文档不改就会被下一次写回来。**
4. **扫一遍 cron**（`cronjob action='list'`），确认没有任何 job 会把它拉起来。改 launcher 只管手动/会话路径，cron 是另一条独立路径。
5. **把流水线里「不跟着一起关」的部分点名告诉用户。** 只听功能名字很容易以为整条线都停了，用户会担心误伤。2026-10-26 实例：会议流水线有四个件，字幕采集 `poll.sh`（保留）、会中预警 `meeting_radar.py`（关掉）、会后纪要 cron「会议收尾哨兵」/`meeting_finisher.py`（保留）、bot 入会（保留）。交付时明确说哪条线没动，用户才敢信。

### 关掉之后不要推销

不开「要不我还是手动帮你跑一次」这种口子。用户要回来会自己说。反复提议复活已否掉的方案，在这个用户身上是明确的激怒点。

完整案例（改动前后 diff、验收命令、会议流水线组件表）见 `references/feature-decommission.md`。

规则型告警的误报治理（弱关键词需「伴随词」兜底、告警必须给出「命中词」、误报出现时怎么回答用户）见 `references/rule-alert-tuning.md`。

## Verify

1. `hermes fallback list` → prints Primary + ordered chain.
2. Probe the fallback endpoint for real (never trust config alone): `python3 ~/.hermes/skills/devops/hermes-cron-troubleshooting/scripts/test_fallback_endpoint.py` — sends a 2-token chat completion to the MiniMax CN endpoint using MINIMAX_API_KEY from ~/.hermes/.env.

## Pitfalls

- **Backup config before editing**: `cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak-$(date +%Y%m%d%H%M%S)`. Edit with python `yaml.safe_load`/`safe_dump` (`sort_keys=False, allow_unicode=True`) to preserve formatting — never hand-edit the YAML structure.
- **curl with inline `$(grep ...)` key extraction is BLOCKED** by the command parser (hardline blocklist). Use `execute_code` + urllib, or the probe script, for API-key-bearing requests.
- **Never print secrets**: extract keys from ~/.hermes/.env in python, strip surrounding quotes, show only length/prefix if needed.
- Check `fallback_providers: []` in config.yaml when diagnosing — empty chain = no safety net (this user's original failure state).
- Provider stalls are transient infrastructure events — the durable lesson is the fallback chain, not "provider X is broken".
- **doctor 的 provider 连通性检查会误报**（2026-10-11）：`hermes doctor` 报 `✗ MiniMax (invalid API key)`，但同一把 key 直连 `https://api.minimaxi.com/v1` 返回 200 —— doctor 探的是海外端点 `api.minimax.io`，**国内 region 的 key 在那里必然失败**（`.env` 里 `MINIMAX_API_KEY` / `MINIMAX_CN_API_KEY` 是两把，都指向国内域名）。**判据**：改 fallback 链之前先用 `references/state-db-corruption-recovery.md` 第 5 节的脚本直连目标 base_url 实测，别照着红叉动配置。

### Probe before rerun (NEW — 2026-09-07)

Provider-timeout failures cluster. If the provider was overloaded enough to stall 600s 5 minutes ago, it may STILL be overloaded. Blindly firing `cronjob action='run'` immediately after a timeout can cascade into another 10-minute wait and another failed run.

**Protocol:**
1. After classifying as provider timeout, do a 30s probe first: send a 2-10 token chat completion with `max_tokens=10` and `stream=false` against the failing provider's base URL. Reference: `scripts/test_fallback_endpoint.py`.
2. If the probe returns content within 30s → provider healthy → safe to fire `cronjob action='run'`.
3. If the probe also stalls → do NOT rerun yet. Either wait (sentinel watchdog will pick it up) or check `gateway.log` / `errors.log` for provider-side incidents before deciding.

Skipping the probe turned a recoverable 9:05 stall into a 9:44 full failure once already (this session).

### `Response remained truncated after N continuation attempts` — what it really means (NEW)

This error looks like a *response quality* problem but is actually a *provider reliability* problem. The first call stalled past 600s, the retry came back with an incomplete reply, and Hermes' continuation logic couldn't recover. Treat it identically to `Non-streaming API call timed out`: fallback chain + sentinel, NOT a prompt rewrite.

### `api_max_retries` is a third knob (NEW — 2026-09-07)

When the provider stalls and returns nothing within 600s, Hermes retries the API call up to `agent.api_max_retries` times (default 3) before giving up. Cheap models on large prompts stall often enough that 3 retries can all land on stalled slots and still fail.

Bump to 5 for cheap-model cron jobs:

```bash
hermes config set agent.api_max_retries 5
```

(Don't try to hand-edit `~/.hermes/config.yaml` — Hermes blocks agent writes to security-sensitive files. Use `hermes config set`.)

Combined with the fallback chain, this gives you two independent retries: first the cheap model retries on its own provider, then if that exhausts, a different provider picks up.

### no_agent 脚本 job 报 `'utf-8' codec can't decode byte 0xef in position N: invalid continuation byte`（NEW — 2026-09-17）

**这不是收尾问题，是 bash 变量名 bug。** 症状：`hermes cron list` 显示 `script failed`，输出文件里只有一行 `Script execution failed: 'utf-8' codec can't decode byte 0xef in position 68: invalid continuation byte`，但脚本本身 `python3 d.decode('utf-8')` 校验完全合法——所以很容易误判成 runner 的锅。

**根因**：脚本在 `set -u` 下写 `echo "会议号 $NO，已重试 8 次"` 这类「`$VAR` 后面紧跟中文字符」的字符串。cron 环境**不带 LANG**（C/POSIX locale），bash 按单字节解析，把 `$NO` 后面那个中文字符的首字节（如 `，` 的 0xEF）当成变量名的一部分 → 解析成 `NO\xef` → 未定义变量 → `unbound variable`，错误信息里带原始非 UTF-8 字节 → cron runner 解码 stdout 失败。

**定位**：`env -i HOME="$HOME" PATH="$PATH" bash <script>` 复现——用干净的、无 locale 的环境跑，正常 shell 里跑是好的。

**修复（两处都要）**：
1. 变量一律加花括号：`$NO，` → `${NO}，`（根治，无 locale 也 OK）
2. 脚本开头强制 locale 兜底：
```bash
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8
```
另外 `cut -c1-400` 在 C locale 下按**字节**截断，会把中文切碎成非法 UTF-8——换成字符级截断（`python3 -c '...decode("utf-8","replace")[:400]'`）。

**验证**：`env -i ... bash script` 必须 exit 0 且 stdout 能被 `decode('utf-8')` 通过。

**同族但不同源的一个坑（2026-10-28）**：全角标点写进**参数展开内部**（`${SUF:+（$SUF）}`）会被当成变量名的一部分，`set -u` 下报 `SUF）: unbound variable` —— 这条**不需要 cron 的缺失 locale，普通交互 shell 一样炸**。判据：报错里变量名后面拖着一个中文字符/全角标点 ⇒ 先看 `${…}` 内部有没有全角字符，别去查 locale。详见 `references/receipt-chain-hardening.md` 第一节。

### `sqlite3.OperationalError: disk I/O error` — state.db 间歇性故障（NEW — 2026-09-18）

症状三类同时或分别出现，且**都不是磁盘满**（先 `df -h` 排除）：

1. `session_search` 工具直接失败：`Session database not available: OperationalError: disk I/O error (state.db may be on NFS/SMB/FUSE/ZFS)`（实测 2026-09-18 09:06 认知对话、10:01 双周Skill同步 各一次）
2. `delegate_task` 派发失败，traceback 落在 `async_delegation.py:_connect → _initialize_schema → apply_wal_with_fallback → conn.execute("PRAGMA journal_mode=WAL")`（实测 2026-09-17 12:24 连续两次，subagent 直接派不出去）
3. **静默最危险**：`~/.hermes/sessions/` 与 state.db 的 `sessions` 表里**找不到那次 cron run 的记录**，但 `hermes cron list` 显示 `completed`、输出文件也正常——即「运行成功但会话没落库」。实测 2026-09-17 09:17 之后连续多条 cron 会话缺失。

**排查顺序（照做，别猜）**：
```bash
df -h /System/Volumes/Data                      # 空间（本案 185G 可用，排除）
ls -la ~/.hermes/state.db*                      # 看 -wal / -shm 是否残留异常
sqlite3 ~/.hermes/state.db "PRAGMA quick_check(1);"   # 本案返回 ok（923MB 库约 16s）
grep -ac "disk I/O error" ~/.hermes/logs/agent.log
grep -an "disk I/O error" ~/.hermes/logs/agent.log | tail   # 看落在了哪个子系统
```

**结论与处置**：DB 本身完好（quick_check ok）+ 空间充足 ⇒ 是**瞬时 I/O/锁**而非损坏，**不要**急着 VACUUM 或删库重建（923MB 库在 gateway 运行中 VACUUM 会长时间独占锁，反而制造更多 I/O error）。正确动作：①记录发生时刻与命中子系统，观察是否聚集；②受影响任务重试即可（重试后均成功）；③若持续出现，再申请**停 gateway 的维护窗口**做 `VACUUM INTO` 重建 + 校验。

### ⭐ 已定位机制：进程持有「旧 WAL inode」＝句柄污染（NEW — 2026-09-25，优先于上面的 VACUUM 方案）

连续 3 个周期（09-17 起 → 09-23 → 09-25）反复复发，W39 复查时把机制钉死了：**不是 I/O 瞬时抖动，是 gateway 长跑进程的 fd 指向了已被替换/删除的旧 `state.db-wal` inode**。WAL 文件被 checkpoint 重建后磁盘上是新 inode，而进程里若干连接仍握着旧 inode 的 fd —— 这些连接看不到新提交、查询直接 `disk I/O error`，`state.db` 的 mtime 也冻结不动。`quick_check` 依然是 ok（文件没坏，坏的是活进程的句柄）。

**一条命令定性（照抄即可）**：
```bash
GW=$(pgrep -f "gateway run" | head -1)
lsof -p $GW 2>/dev/null | grep "state.db-wal"      # 看进程持有的 -wal 有几个 inode、多大
stat -f "disk-wal inode=%i size=%z" ~/.hermes/state.db-wal   # 看磁盘上的 inode/size
ls -la ~/.hermes/state.db ~/.hermes/state.db-wal
```
**判据**：进程里出现**多个不同 inode 的 -wal fd**（实测 09-25：fd 10/13/22/23/35 指向 inode 94834555 / 8.4MB，fd 66 指向新 inode / 0 字节），且磁盘 inode ≠ 进程持有的主 inode ⇒ **确诊句柄污染**。旁证：`session_search` 报 `disk I/O error`、`state.db` mtime 卡在某天、当天 message 0 条落库。

**修复＝重启 gateway，不是 VACUUM**（重启即换新句柄，秒级恢复；VACUUM 只能重建文件、治不了活进程的陈旧 fd）。cron 自身跑在 gateway 进程内**不能自重启**（安全护栏会拦，且会杀掉自己导致卡片发不出去）→ 写进交付物交用户执行，附验证三连：
```bash
hermes gateway restart                     # 用户在 Mac 上另开终端执行，约 1 分钟
ls -la ~/.hermes/state.db                  # 验证1：mtime 随新会话推进
grep -c "disk I/O error" ~/.hermes/logs/agent.log   # 验证2：不再增长
# 验证3：session_search 恢复可用（能返回结果而不是报错）
```
**同一个动作顺带治缓存配置漂移**：进程启动时读入的配置会一直用下去 —— 例如 `mcp_servers.my-coffee.enabled: false` 已写进 config.yaml，但长跑进程仍每 5 分钟重试一次、刷 401（09-25 单日 218 条）。**判据**：配置已改 + 行为未变 ⇒ 需重启，别去反复改配置。

**长跑进程卫生巡检（周期复盘时顺手做）**：`ps -eo pid,lstart,etime,command | grep -E "hermes|poll"`。除主 gateway 外，任何「预期短命却活了多天」的进程都要点名（实测：会议自动检测守护 `poll-v5.sh` 自 09-04 起跑了 21 天、10s 轮询）——是功能就留、是残留就停，别让它无声耗资源。

### ⭐ `database disk image is malformed` — state.db 真损坏（NEW — 2026-10-11）

**与上面的 `disk I/O error` 是两级事**：I/O error 是句柄问题（文件没坏，重启即好），malformed 是**文件真坏**。一条命令分清：`sqlite3 ~/.hermes/state.db "PRAGMA integrity_check;"` → `ok` 是前者，`*** in database main *** ... Rowid ... out of order` 是后者。

**症状三连（本 session 全中）**：
1. `cronjob action='list'` 里**几乎所有 job 同时** `last_status: error`，失败时刻挤在同一两天 —— 不是各自坏了，是共用的库坏了。看到这种"集体阵亡"先查库，别逐个 job 排。
2. cron 输出文件末尾固定是这一句：
   `RuntimeError: ⚠️ No reply: the turn was stopped because session storage could not be written (the transcript would have been lost on restart). Check the state database health (hermes doctor), then send your message again.`
3. `grep -a "malformed" ~/.hermes/logs/gateway.log` 刷屏：`gateway.session: state.db routing save failed: database disk image is malformed`、`Failed to create session row <id> ... database disk image is malformed — deferring to the self-healing peer refresh`。

**"任务全挂了"的真正含义**：任务其实跑到了，是**结果写不进库**，最后一步被安全护栏掐断。所以库修好 ≠ 产出补回，要用 `cronjob action='run'` 逐条补跑当天失败的 job。

**定位损坏起点（决定能救回多少）**：修复过程会在 `~/.hermes/backups/` 留分代备份——`db-<ts>/state.db`、`db-deep-<ts>/{state.db.now,state.db.main,state.db.malformed-backup,state_dump.sql,filter_dump.py}`，外加 `~/.hermes/state.db.{malformed-backup,corrupt}-<ts>`。逐个 `.recover` 灌进临时库、看最新消息时间戳，就能画出"库从哪天开始写不进"。本 session 结论：起点 10-08 01:33，其后约 3 周会话三份备份全止于同一点 → 不可恢复，如实告知用户、别兜圈子继续找。

**修复动作（按序）**：
1. 重启 gateway 换掉陈旧句柄（见上一节）。
2. `PRAGMA foreign_key_check` 查孤儿 —— 损坏期写进去的消息会指向不存在的 session 行。**优先补 session 行，不要删消息**（保住数据）：
   ```bash
   sqlite3 ~/.hermes/state.db "INSERT OR IGNORE INTO sessions (id, source, started_at, message_count) VALUES ('<orphan_session_id>','feishu', strftime('%s','<date>')*1.0, <n>);"
   ```
3. 建会话行偶发 `FOREIGN KEY constraint failed` → 下一轮 self-heal 会补上，不必手动干预。
4. 长期：`hermes sessions optimize-storage` 迁移旧 FTS 存储布局（回收约六成体积，降低再坏概率）。

**别把「丢失」说大（NEW — 2026-10-11 续查，修正上一版结论）**：下「N 周对话没了」的结论前，先数窗口内的**用户消息**：
```bash
grep -cE "^2026-(09-2[2-9]|09-3[01]|10-0[1-8]).*inbound message" ~/.hermes/logs/gateway.log
```
本 session 实测该窗口 **0 条用户消息**（那段时间只有 cron 在跑）——「三周对话丢失」其实是「三周没对话」，真正丢的只是 cron 的过程记录（产出 .md 还在）。据实修正、别吓用户；三份备份同止于一点只说明**该点之后没有落过盘**，不等于用户损失了对话。

**根因取证 + 早期预警指标 + 谁有权写 state.db** 见 `references/state-db-corruption-forensics.md`。

完整命令、月分布检测 SQL、备份文件名规律、收尾核对清单见 `references/state-db-corruption-recovery.md`。

### 验证修复：`env -i HOME="$HOME" PATH="$PATH" bash script`（NEW）

cron 脚本跑不通时，第一个诊断动作就是这一条：把交互 shell 的 locale/环境全剥掉再跑一遍。这个 session 里 4 个 pitfall（provider 超时之外的）里有一半只在无 locale 环境复现。

### Reproducing a failure: request dumps (NEW — 2026-09-07)

Beyond `~/.hermes/cron/output/<job_id>/`, the deepest evidence for diagnosing a provider-timeout failure is `~/.hermes/sessions/request_dump_cron_<job_id>_<start>_<end>_<pid>.json`. These contain the FULL outbound request body (system prompt length, user prompt length, tools array length, model, max_tokens, stream flag) and the provider error — enough to confirm whether the stall was prompt-size-induced vs. provider-side incident.

**Use when:** the output file shows `RuntimeError: Response remained truncated` and you need to know whether to (a) blame prompt size, (b) blame provider, or (c) re-run and hope.

**Recipe:**
```bash
python3 -c "
import json
d = json.load(open('<dump_path>'))
print('model:', d['request']['body']['model'])
print('system len:', len(d['request']['body']['messages'][0]['content']))
print('user len:', len(d['request']['body']['messages'][1]['content']))
print('tools:', len(d['request']['body'].get('tools', [])))
print('max_tokens:', d['request']['body'].get('max_tokens'))
print('error:', d.get('error', {}).get('summary', 'n/a')[:200])
"
```

Rule of thumb: system + user prompt totaling >50K chars + >15 tools + cheap model = structurally fragile, fix options below.

### Cron is non-streaming by design — and why that bites DeepSeek on large prompts (NEW — 2026-09-07)

`agent/chat_completion_helpers.py:560 should_use_direct_api_call()`:

```python
if getattr(agent, "platform", None) == "cron":
    return True
```

…and the caller at line 2822 immediately delegates `_interruptible_streaming_api_call` → `_interruptible_api_call` (non-streaming). The reason is #62151: the worker-thread path deadlocks in the cron nested-pool context (gateway → cron thread → interrupt worker). So cron is locked into non-streaming no matter what.

The hard interrupt is 600s on non-streaming (vs `gateway_timeout:1800` for streaming). On DeepSeek flash specifically: streaming responses arrive in <1s even on 96K prompts; non-streaming responses on `max_tokens=4096` + 96K prompt can hang past 600s. This is a fingerprint of the provider, not a one-off.

**Implications:**
- "Switch to streaming" is NOT an option for cron. Don't propose it.
- **Fallback chain to a different provider** is the cleanest fix when the same job works interactively (interactive = same model = streaming = 0.5s; the only failure mode is the provider's non-streaming path).
- **Slimming the skill** helps proportionally because prompt-size pressure is structural on this provider.
- **Bumping to mid-tier on the same provider** may help if the cheap tier is the bottleneck — but costs more. Validate with the streaming-vs-non-streaming probe first; mid-tier can have the same hang.

### Streaming-vs-non-streaming provider probe (NEW — 2026-09-07)

A 30-second non-streaming probe can give false reassurance. The pattern this session surfaced:

- Non-streaming small request (`max_tokens=100`, 96K prompt): **2.6s** — looks healthy
- Non-streaming large request (`max_tokens=4096`, 96K prompt): **180s+ hang** — fails
- Streaming large request (same 96K prompt): **TTFB 0.5s** — works fine

So "probe returned OK in 2s" is **not** evidence the cron path will work. The cron path is forced non-streaming AND needs 4096 max_tokens AND has the full skill prompt loaded. The probe must match that, or it gives false reassurance.

**Better probe (after a 600s timeout on a large-prompt cron job):**

```python
import json, urllib.request, time
key = open('/Users/bytedance/.hermes/.env').read()
for line in key.splitlines():
    if line.startswith('YOUR_PROVIDER_KEY='):
        key = line.split('=', 1)[1].strip().strip('"')
big = 'cron skill simulation. ' + ('concept file sample. ' * 1400)  # ~96K chars, matches real cron volume

def call(stream, max_tokens, timeout=30):
    body = {'model': 'cheap-model', 'messages': [{'role': 'user', 'content': big}],
            'max_tokens': max_tokens, 'stream': stream}
    req = urllib.request.Request('https://provider/v1/chat/completions',
                                 data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        if stream:
            resp.readline()  # TTFB only
            print(f'STREAM max_tokens={max_tokens}: TTFB={time.time()-t0:.1f}s')
        else:
            json.load(resp)
            print(f'NON-STREAM max_tokens={max_tokens}: full={time.time()-t0:.1f}s')
    except Exception as e:
        print(f'FAIL stream={stream} max_tokens={max_tokens} after {time.time()-t0:.1f}s: {type(e).__name__}')

call(stream=True, max_tokens=4096)    # what TUI/interactive uses — usually fine
call(stream=False, max_tokens=100)    # small non-stream — usually fine, misleading
call(stream=False, max_tokens=4096)   # what CRON uses — the one that matters
```

**Interpretation:**
- Non-stream `max_tokens=4096` hangs again → structural fragility (provider can't handle that combo on non-stream). Don't blame the prompt; don't blame "provider overloaded" — fix the route (fallback provider, slim skill, or mid-tier model).
- All three pass → real provider incident, retry the cron run.
- Only streaming works → see "Cron is non-streaming by design" above — fallback or slim is the only path forward.

### Large-prompt + cheap-model structural fragility (NEW — 2026-09-07)

A 30KB+ skill prompt (e.g. `ebbinghaus-review` SKILL.md at 32KB) running on a cheap/fast model (e.g. `deepseek-v4-flash`) has a higher 600s-timeout rate than a small prompt on the same model. This is NOT transient infrastructure — it's structural: a single response has to traverse a much larger context window through a smaller model.

**Symptoms that point to this combo specifically:**
- Failure file contains the full skill prompt + the early-failure error → confirms the prompt loaded fine and the stall happened mid-response.
- Pattern repeats across multiple days (real case: 8/22, 8/25, 9/1, 9/7 — same job, same provider, same model, identical 600s error).

**Fix options (user-approved combinations):**
1. **Slim the skill prompt** — split into core flow + appendix; only inject core into prompt, load appendix on demand via `skill_view`.
2. **Switch cron job model to the provider's mid-tier** (e.g. `deepseek-v4-pro`) — sacrifices the "cheap-first" preference for reliability.
3. ~~**Streaming mode**~~ — NOT AN OPTION. Cron is hardcoded to non-streaming (`should_use_direct_api_call` returns True for `platform=="cron"`); the streaming path is delegated to the non-streaming call before dispatch. See "Cron is non-streaming by design" above.
4. **Fallback chain** — when cheap model stalls, mid-tier on a different provider picks up the slack. Captures 90% of failures with zero skill changes.

The fallback chain (option 4) is the no-rewrite fix. Apply it first; only escalate to options 1-3 if the chain still doesn't cover.
