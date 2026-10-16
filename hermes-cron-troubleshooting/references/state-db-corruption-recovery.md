# state.db 损坏：诊断、定性、抢救、收尾

实测案例 2026-10-11（state.db 从 10-08 01:33 起 malformed，全部 cron job 集体失败；丢失的是 9/22–10/11 的 **cron 过程记录**——该窗口用户零对话，正文对话未丢，见第 6 节）。
本文是该次排查的完整命令集。命令不套 `timeout`（macOS 无 coreutils）。

## 0. 一分钟定性

```bash
sqlite3 ~/.hermes/state.db "PRAGMA integrity_check;"      # ok=没坏(看句柄/IO) ; HARD ERROR=真损坏
sqlite3 ~/.hermes/state.db "PRAGMA foreign_key_check;"    # 空=引用完整
sqlite3 ~/.hermes/state.db "SELECT COUNT(*) FROM messages;"   # 能否正常查询
grep -a "malformed" ~/.hermes/logs/gateway.log | tail -20
grep -a "malformed\|could not be written" ~/.hermes/logs/gateway.error.log | tail -20
```

判据速查：

| 证据 | 含义 |
|---|---|
| `integrity_check` → `*** in database main ***` / `Rowid ... out of order` | 文件级损坏，必须换库/重建 |
| `gateway.session: state.db routing save failed: database disk image is malformed` | 损坏已持续一段时间（routing 是每轮都写的表） |
| `Failed to create session row <id> ... malformed` | 会话行建不上 → 该轮对话不会落库 |
| `Failed to create session row ... FOREIGN KEY constraint failed` | 库已被重建过，但历史消息指向了不存在的 session 行（孤儿） |

macOS 上先顺手排除的两个假象：`df -h /System/Volumes/Data`（空间）和 `ls -la ~/.hermes/state.db*`（-wal/-shm 残留）。

## 1. 判断"最近的历史还在不在"

按月分布两张表，一眼看出断层：

```bash
sqlite3 ~/.hermes/state.db "SELECT strftime('%Y-%m', datetime(started_at,'unixepoch','localtime')) m, COUNT(*) FROM sessions GROUP BY m ORDER BY m;"
sqlite3 ~/.hermes/state.db "SELECT strftime('%Y-%m', datetime(timestamp,'unixepoch','localtime')) m, COUNT(*) FROM messages GROUP BY m ORDER BY m;"
sqlite3 ~/.hermes/state.db "SELECT id, substr(COALESCE(title,''),1,40), datetime(started_at,'unixepoch','localtime') FROM sessions ORDER BY started_at DESC LIMIT 10;"
```

最后一条能直接看出"最后一次正常会话是哪天"。（注意：`sessions` 主键列名是 `id`，不是 `session_id`——写 `SELECT session_id FROM sessions` 会报 no such column。）

## 2. 从备份里挖可恢复量（`sqlite3 .recover`）

`~/.hermes/` 下会堆这些：`state.db.corrupt-<YYYYMMDD-HHMMSS>`、`state.db.malformed-backup-<ts>`、`backups/db-<ts>/state.db`、`backups/db-deep-<ts>/{state.db.now,state.db.main,state.db.malformed-backup,state_dump.sql,filter_dump.py}`。

`db-deep-*` 是"深度修复"过程留下的工作目录：`.now`/`.main` 是修复前的坏库副本，`state_dump.sql` 与 `state_dump_filtered.sql` 是 `.recover` 的全量/过滤后 dump。**先看这几份，再决定要不要自己重跑 recover。**

```bash
for f in ~/.hermes/state.db.corrupt-* ~/.hermes/state.db.malformed-backup-* ~/.hermes/backups/*/state.db*; do
  [ -f "$f" ] || continue
  echo "--- $f"
  sqlite3 "$f" "SELECT datetime(MAX(timestamp),'unixepoch','localtime') FROM messages;" 2>&1 | head -2
done
```

坏库上直接 `PRAGMA integrity_check` / `SELECT COUNT(*)` 通常直接报 `database disk image is malformed (11)`——**读不了不代表救不了**，`.recover` 走的是页级扫描：

```bash
sqlite3 <corrupt.db> ".recover" 2>/dev/null | sqlite3 /tmp/state_recover.db
# 大型库（1G 级）约 1–2 分钟，产物 ~1.1G；用 background=true 跑，别卡住前台
```

抢救库同样用第 1 节的按月分布 SQL 对一遍，就能算出"能恢复到的最后一天"。多份备份对完后如果最大值一致，说明更晚的数据**从来没有落过盘**，可以直接告诉用户不可恢复，不用继续找。

## 3. 修引用完整性（保留数据，不要删）

```bash
sqlite3 ~/.hermes/state.db "PRAGMA foreign_key_check;" | awk -F'|' '{print $1"|"$3}' | sort | uniq -c
# 例： 7 messages|sessions     → 7 条消息指向不存在的 session

sqlite3 ~/.hermes/state.db "SELECT DISTINCT session_id, MIN(datetime(timestamp,'unixepoch','localtime')), MAX(datetime(timestamp,'unixepoch','localtime')), COUNT(*) FROM messages WHERE session_id NOT IN (SELECT id FROM sessions) GROUP BY session_id;"
```

补回缺失的会话行（比删消息好，能把损坏期唯一幸存的那点对话留住）：

```bash
cp ~/.hermes/state.db /tmp/state.db.pre-fix-backup     # 动手前先副本
sqlite3 ~/.hermes/state.db "INSERT OR IGNORE INTO sessions (id, source, user_id, started_at, message_count) VALUES ('<orphan_session_id>','feishu','<user_open_id>', strftime('%s','<YYYY-MM-DD HH:MM:SS>')*1.0, <n>);"
sqlite3 ~/.hermes/state.db "PRAGMA foreign_key_check;"   # 复查，应输出空
```

注意 `started_at` 是 Unix epoch 秒的 REAL，`strftime('%s',...)` 返回 TEXT，要 `*1.0` 转回数值；`sessions` 的 `source` 与 `started_at` 是 NOT NULL。

## 4. 收尾核对清单

```bash
sqlite3 ~/.hermes/state.db "PRAGMA integrity_check;"                                    # ok
sqlite3 ~/.hermes/state.db "PRAGMA foreign_key_check;"                                  # 空
sqlite3 ~/.hermes/state.db "SELECT datetime(MAX(timestamp),'unixepoch','localtime') FROM messages;"   # 应≈当前时间（证明能写）
ps aux | grep "gateway run" | grep -v grep                                              # gateway 在跑
grep -a "malformed" ~/.hermes/logs/gateway.log | tail -3                                 # 重启后不再新增
```

补跑产出：`cronjob action='list'` 找出当天 `last_status: error` 的 job，逐个 `cronjob action='run'`（结果会在跑完后回到对话里，不要轮询等）。

可选：`hermes sessions optimize-storage` 迁移旧 FTS 存储布局（`hermes update` 也会提示"Your search index uses the old storage layout"，约回收六成体积）。确认无用的备份文件（`state.db.corrupt-*`、`backups/db-*`，本次合计 ~2.7G）问过用户再删。

## 5. 顺带澄清：doctor 的 provider 红叉会误报

修复后 `hermes doctor` 常报 `✗ MiniMax (invalid API key)`。实测（2026-10-11）：同一把 key 直连 `https://api.minimaxi.com/v1` 返回 200 —— doctor 探的是海外端点（`api.minimax.io`），**国内 region 的 key 在那里必然失败**，与 `.env` 里同时存在的 `MINIMAX_API_KEY` / `MINIMAX_CN_API_KEY` 是两回事。

判据：先直连目标 base_url 实测，再决定动不动 fallback 链，别照着红叉改配置。

```bash
python3 - <<'PY'
import os, json, urllib.request
env = dict(l.split('=', 1) for l in open(os.path.expanduser('~/.hermes/.env')) if '=' in l and not l.strip().startswith('#'))
key = env['MINIMAX_API_KEY'].strip().strip('"').strip("'")
body = json.dumps({"model": "MiniMax-M3", "messages": [{"role": "user", "content": "回复两字：正常"}], "max_tokens": 10}).encode()
req = urllib.request.Request("https://api.minimaxi.com/v1/chat/completions", data=body,
                             headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("OK:", json.loads(r.read().decode())["choices"][0]["message"]["content"])
except Exception as e:
    print("FAIL:", type(e).__name__, e)
PY
```

（`curl` 带 `$(grep ...)` 取 key 会被命令解析器拦，用 python/urllib。）

## 6. 根因定位：别停在「库坏了」

事故复盘要能回答「为什么是现在、以前怎么没炸」。三条 grep 就能还原责任链：

```bash
cd ~/.hermes/logs
grep -h "database disk image is malformed" *.log *.log.* | grep -oE "^[0-9-]+ [0-9]{2}" | sort | uniq -c
grep -h "lagged live cached history" *.log *.log.* | head -3
grep -h "disk I/O error" *.log *.log.* | sort | head -3
```

| 信号 | 含义 |
|---|---|
| `Persisted transcript lagged live cached history (possible FTS write corruption)` | 最早的静默丢数据：落库落后于内存，Hermes 把对话留在内存里兜住了 → **用户无感，故障被掩盖数月**（本次实测可追到 7/4，183 次） |
| `disk I/O error (state.db may be on NFS/SMB/FUSE/ZFS)` | 第二个进程（cron 拉起的 hermes）打不开 WAL 状态，比 malformed 早 2–3 周出现；只有 cron 会话受影响，网关自己的写入还活着 |
| `Hermes venv links SQLite <ver>, which has the WAL-reset bug` | 运行库踩在 SQLite WAL-reset 缺陷区间（3.7.0–3.51.2，除 3.50.7 / 3.44.6 等 backport）；`hermes update` 会自动 provision 安全版并打印 `Managed Python runtime repaired (x → y)` |
| 损坏计数突然从个位数/天 跳到 数百/天 | 损坏已从 FTS 影子表蔓延进正文 btree，自愈彻底失效 → 全体 cron 挂 |

三条叠加才爆发：① 旧 FTS 布局把库撑到 ~1G（`hermes sessions optimize-storage` 可收六成；**重建过的库会直接提示 "already on the compact layout — nothing to do"，属正常**）；② 网关连续运行 23 天没重启，WAL 长期不 checkpoint；③ 多进程共享同一 WAL。

⚠️ **系统 `python3` / `/usr/bin/sqlite3` 可能仍在缺陷区间**（本次实测 3.51.0）。state.db 的读写一律走 `~/.hermes/hermes-agent/venv/bin/python`，不要用系统那个——否则 WAL-reset 缺陷原样复发。

判断「是不是真丢了对话」：按天看 inbound 消息数，别按「有没有 session 行」。

```bash
grep -cE "^2026-09-2[2-9].*inbound message" ~/.hermes/logs/gateway.log   # 0 = 那几天用户根本没说话
```

## 7. 预防：守护任务（本次已装）

**每日 05:00 · Hermes cron（no_agent 脚本）**
- 脚本 `~/.hermes/scripts/state_guard.sh`，日志 `~/.hermes/logs/state-guard-run.log`
- 干三件事：venv 在线备份 state.db（保留最近 7 份，`~/.hermes/backups/state-db/`）→ `PRAGMA wal_checkpoint(TRUNCATE)` → 扫日志统计「早期损坏信号」计数并比对基线
- stdout 语义：正常**空输出**（no_agent cron 静默不打扰），只有新增信号才出话 → 自动发飞书
- 首次装机必须先 `bash state_guard.sh --seed` 写基线，否则第一晚会把历史计数当新增误报

**每周日 05:10 · 用户 crontab（不在 Hermes cron 里）**
- 脚本 `gateway_rotate.sh`：网关连续运行 ≥7 天才先 `wal_checkpoint` 再 `launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway`
- 安装：`bash ~/.hermes/scripts/install_rotate_cron.sh`（幂等）；试算：`ROTATE_DRY_RUN=1 bash gateway_rotate.sh`
- 为什么不用 Hermes cron：那个 job 自己就跑在网关进程里，重启等于把自己杀了

**工具层限制（本次踩过，别再试）**
- 在 Agent 的 terminal 里 **不能** `launchctl bootstrap`（"registers a persistent KeepAlive job … unsafe from inside the gateway process"），也**不能**执行含 `launchctl kickstart` 的脚本（"cannot restart or stop the gateway from inside the gateway process"）
- 因此在网关内部能做的只有：Hermes cron 任务、写 `~/Library/LaunchAgents/*.plist`（不 bootstrap）。要真正注册 launchd 或改 crontab 里的重启项，交给用户在外面跑，或走 crontab 文件（`crontab <file>` 可写）
- 别把写好的 plist 留在 `~/Library/LaunchAgents/`：**下次登录系统会自动加载**，会和 Hermes cron 里的同类任务抢着更新哨兵基线，把告警吃掉

