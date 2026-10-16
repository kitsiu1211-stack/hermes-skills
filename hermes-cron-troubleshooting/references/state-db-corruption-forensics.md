# state.db 损坏：根因取证与复发预防

实测案例 2026-10-11（承接 `state-db-corruption-recovery.md`——那份讲「怎么救」，这份讲「为什么坏、会不会再坏」）。
修复只解决「现在能写」；取证才决定要不要改配置、要不要加哨兵。命令不套 `timeout`（macOS 无 coreutils）。

## 0. 一句话结论

不是突发事件，是攒了几个月的病在 10-08 集中发作。取证的价值在于把「用户看到的所有 cron 一起挂」翻译成一条可复发的因果链。

## 1. 定位起止：按天/按小时直方图

```bash
cd ~/.hermes/logs
grep -h "database disk image is malformed" *.log *.log.* \
  | grep -oE "^20[0-9-]+ [0-9]{2}" | sort | uniq -c      # 按月-日-小时
```

**两个必须踩过的坑：**

1. **裸词 `malformed` 会被污染**。日志里还有两种无关的 malformed：
   - `agent.message_sanitization: Repaired malformed tool_call arguments for ...`
   - `tools.approval: Hardline block: command parser limit or malformed executable payload`
   只 grep 裸词会把它们一起统计进来（本次第一遍就被带偏）。**必须 grep 完整短语** `database disk image is malformed` / 或直接 grep `state.db`。
2. **必须带轮转文件** `*.log.*`。本机轮转规律：`agent.log.1`(→8/25)、`errors.log.1`(→9/17)、`gateway.log.1`(→8/23)、`errors.log.2`。只看当前 `*.log` 会以为问题只从 10-08 开始。
   - 判据：`date` 只能给「今天」；先看 `head -1 <log>` / `tail -1 <log>` 得到每个文件的时间覆盖范围，再决定 grep 哪些文件。

取证产出应该是一句话：「最早已于 X 出现、Y 起爆发、Z 起全线失败」。本案例：7-04 出现轻症 → 9-18 起间歇 → 10-08 01:13 首发 malformed → 10-08~10-11 每天 342~684 条。

## 2. 三类早期预警指标（复发哨兵，看到就处置）

按危险度从低到高，任何一条出现都早于 `malformed`：

| 日志片段 | 含义 | 首次实测 |
|---|---|---|
| `Persisted transcript lagged live cached history for session ... (possible FTS write corruption)` | 落库追不上内存，Hermes 把对话留在内存里兜着。**用户完全无感** | 2026-07-04（至 8-14 累计 183 次） |
| `Automatic rebuild of stale FTS indexes failed (database disk image is malformed); canonical writes remain enabled with FTS detached.` / `FTS indexes failed` / `FTS detached` | FTS 影子索引写失败 → 自愈摘掉索引、正文继续写。此时库「还能用」 | 2026-10-08 起每小时 24 条（当天 2061 条） |
| `... state.db ... disk I/O error (state.db may be on NFS/SMB/FUSE/ZFS)` | 第二进程打不开 WAL（见 SKILL.md 句柄污染节） | 2026-09-18 09:06 |

一句话：**`malformed` 是终局，不是起点**。前面还有两层自愈垫着，这就是「为什么以前一直没爆」。

## 3. 根因三层（2026-10 这一次）

1. **FTS 旧存储布局把库撑到 1GB**。消息本体只占 204MB，索引吃掉其余（见第 5 节的 dbstat）。旧布局下索引随消息量超线性膨胀。
2. **运行时踩过 SQLite 的 WAL-reset bug**。中招区间 **3.7.0–3.51.2**（排除 backport 3.50.7–3.50.x、3.44.6–3.44.x），判定逻辑在 `hermes_cli/sqlite_runtime.py: is_sqlite_wal_reset_vulnerable()`，`hermes_cli/doctor.py` 会打 `SQLite x.y.z (WAL-reset bug)` 标签。`hermes update` 发现后会自修运行时并打印：
   ```
   ⚠ Hermes venv links SQLite 3.50.4, which has the WAL-reset bug.
   → Provisioning a private Python 3.11 runtime with fixed SQLite...
   ✓ Managed Python runtime repaired (SQLite 3.50.4 → 3.53.1)
   ```
   查历史：`grep -l "WAL-reset bug" ~/.hermes/logs/*` （本机命中 `update.log`，配 `grep "hermes update started" update.log` 得到发生日期）。
3. **多进程 + 网关长期不重启**。网关是 launchd 常驻（本案例 9-16 22:38 → 10-10 10:09，连续 23 天），每天还有 cron 拉起的独立 hermes 进程开同一个库。

三层同时到顶的那天，自愈彻底失效 → 写库全线失败 → 才出现「所有定时任务一起挂」。
**为什么以前没爆**：自愈一直盖着（摘 FTS + 对话留内存），用户看到的是「一切正常」。

## 4. 谁有权写 state.db（血泪规则）

```bash
~/.hermes/hermes-agent/venv/bin/python -c "import sqlite3;print(sqlite3.sqlite_version)"   # 本机 3.53.1 ✅ 安全
sqlite3 --version                                                                          # 本机 3.51.0 ⚠️ 在中招区间
/usr/bin/python3 -c "import sqlite3;print(sqlite3.sqlite_version)"                          # 本机 3.51.0 ⚠️ 同上
```

- ✅ 只有 **venv 的 python** 可以写 state.db（含补孤儿 session 行这种小操作）。
- ⚠️ `/usr/bin/sqlite3` 和 `/usr/bin/python3` 仍在 WAL-reset bug 区间。第二进程用它们碰 state.db，就可能把在跑的 gateway 的 WAL 重置掉——正是第 3 节第 2 条的触发面。
- 2026-10-11 实测：补孤儿 session 行时误用了 `/usr/bin/sqlite3`（当时单写者、量极小，未出事），事后已纠正为 venv python。**写操作前先默念一句：venv。**
- 只读查询用 CLI 一般安全，但没必要冒险，统一走 venv 最省心。

## 5. 量化 FTS 膨胀（决定要不要 optimize-storage）

```bash
sqlite3 ~/.hermes/state.db "SELECT name, SUM(pgsize)/1048576.0 AS mb FROM dbstat GROUP BY name ORDER BY mb DESC LIMIT 12;"
```

本案例：`messages` 204MB / `messages_fts_trigram_data` 130MB / `messages_fts_data` 57MB——索引类合计 ≈ 消息本体。
判据：**索引总量接近或超过消息本体 = 该跑 `hermes sessions optimize-storage`**（`hermes update` 也会提示 `Your search index uses the old storage layout ... typically frees ~60%`）。
表定义旁证（`content='messages'` 外内容 FTS5）：`sqlite3 state.db "SELECT sql FROM sqlite_master WHERE name LIKE 'messages_fts%';"`

## 6. 修复后的加固（macOS LaunchAgent）

`~/Library/LaunchAgents/ai.hermes.gateway.plist` 增加：

- `LowPriorityIO = true` —— 给 gateway 独立 jetsam 配额，防大 FTS 重建时被 macOS 内存压力杀掉（注释里写明事故出处，后人别删）。
- `ThrottleInterval = 30` —— 提高 launchd 最小重启间隔，防崩溃循环把 launchd 打成重启风暴。
- `ExitTimeOut = 25` —— 停止时给 25s 优雅 drain 再升级到 SIGKILL。

改完 `launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway` 生效，`launchctl list | grep hermes` 看 pid/退出码。

## 7. 补跑之后要独立核验（别信自述）

```bash
sqlite3 ~/.hermes/cron/executions.db "SELECT job_id,status,error FROM executions ORDER BY rowid DESC LIMIT 3;"
lark-cli im +messages-mget --as bot --message-id om_xxx      # 卡片真的在不在
```

- `cronjob action='run'` 的返回体里 `Result: ok` 只是调度器自述，交付物要另行核验。
- 坑：**`lark-cli im +messages-list` 不存在**（子命令只有 `+messages-mget / +messages-edit / +messages-send / +messages-reply / +messages-search / +messages-read-status`）。核验单条卡片用 `+messages-mget --message-id`。
- 坑：核验 cron 输出文件里的失败标记要匹配 `^## Error$` 整块，别裸搜 `## Error`——skill 正文里的 `## Error Handling` 章节会误命中（本次 `grep -c "## Error"` 返回 1，实际是成功跑完）。

## 8. 例行备份（本次的短板）

这次抢救全靠**临时**备份（`backups/db-*`、`backups/db-deep-*`、`state.db.corrupt-*`），之前**没有任何例行 state.db 备份**——能救回来纯属修复流程自带留档。
建议补一条定期任务：`VACUUM INTO`（比 cp 安全，WAL 模式下不会拷到撕裂镜像）或 `hermes backup`，落到 `~/.hermes/backups/` 之外的位置（同盘同目录不防误删）。
