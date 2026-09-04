# listen 脚本生产指南

## 结论：用 V3 poll.sh，不要用 V6 Python 脚本

V6 三次迭代均未稳定，**直接使用 V3 poll.sh**：

```bash
bash ~/.hermes/skills/feishu/feishu-meeting-listen/scripts/poll.sh <meeting_id> <meeting_title>
```

## 演化链路：V3→V6 失败根因

| 版本 | 方案 | 问题 |
|------|------|------|
| V3 (poll.sh) | `--page-all` 全量拉 + `grep "user is not in the meeting"` | ✅ 稳定可靠 |
| V5 (listen_subtitles.py) | `meeting-list-active` 检测结束 | ❌ API 先停，脚本后检测 → 卡死不保存 |
| V6 | `--page-all` + `--page-size 50` 同时使用 | ❌ 分页冲突 → API 永远不返回错误 → 脚本永久卡死 |
| V6.1 | 去 `--page-all`，仅 `--page-size 50` | ❌ 会议结束后 events API 先无数据 → 空转等待 |

## 关键教训

1. **生产脚本用 V3 bash，不要重写。** V3 的 `--page-all` + `grep "user is not in the meeting"` 是最可靠的组合
2. **`--page-all` 和 `--page-size` 不要同时用** — 导致分页循环卡死
3. **会议结束检测必须合并 stderr** — 错误消息可能走 stderr (`result.stdout + result.stderr`)
4. **文件锁问题** — 僵尸进程持有目录锁时，从 `/tmp/` 运行新脚本

## lark-cli 操作铁律（本会话验证）

- `docs +search` 字段名：`data.results`（非 `data.items`），标题在 `result_meta.title_highlighted`
- `docs +update` 需 `--command overwrite --content -`（stdin 传 XML）
- `docs +fetch` 返回的 `document.content` 是 HTML 转义文本，需 `html.unescape(re.sub(...))` 解码
- `whiteboard` 无 `+create`，需在 doc XML 中用 `<whiteboard type="svg">...</whiteboard>` 直接嵌入
- SVG 嵌入 doc 前须将 `"` 替换为 `&quot;`

## 演化链路

```
V3 (poll.sh)  → 稳定可靠，bash 全量拉取 + "user is not in the meeting" 检测
V5 (listen_subtitles.py)  → 会议结束后卡死不保存，0 字节输出
V6 (listen_subtitles_v6.py)  → 移植 V3 检测逻辑，但 --page-all + --page-size 冲突 → 卡死
V6.1 (listen_v6_fixed.py)  → ✅ 生产就绪
```

## V5 Bug 根因
`meeting-list-active` 返回空后 events API 已不返回数据 → `等待最後字幕...` 死循环 → 0 字节输出

## V6 Bug 根因
`--page-all` + `--page-size 100` 同时使用 → API 分页循循环卡死 → 会议结束后脚本永远检测不到 `"user is not in the meeting"` → 实测：旁听 348 轮静默后仍然卡在等待循环

## V6.1 生产版修复（三处）

### 1. 去掉 `--page-all`
仅用 `--page-size 50`，正常分页拉取

### 2. 合并 stdout + stderr 做结束检测
```python
output = result.stdout + result.stderr
if "user is not in the meeting" in output:
    break
```

### 3. 避开文件锁
旧 listen_subtitles.py 僵尸进程持有 Codex_Project 目录锁 → 新脚本从 `/tmp/` 运行：
```bash
cp /tmp/listen_v6_fixed.py /tmp/listen.py && python3.11 /tmp/listen.py
```

## 生产脚本位置
`/tmp/listen_v6_fixed.py` — 可直接使用
`/tmp/listen_subtitles_v6.py` — V6 有 Bug 版本，V6.1 卡死时参考

## 正确的调用命令
```bash
python3.11 /tmp/listen_v6_fixed.py
# 自动检测活跃会议并旁听
```
