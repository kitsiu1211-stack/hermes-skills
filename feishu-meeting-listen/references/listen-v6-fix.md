# listen_subtitles.py V5→V6 修复记录

## 问题

V5 在会议结束后永远卡住，不保存字幕，不输出纪要。实测：内部学习会议跑了 55 分钟未退出，字幕 0 条。

## 根因分析（两次迭代）

### 第一版 V6（失败）：`--page-all` + `--page-size` 冲突

首版修复移植了 V3 poll.sh 的 `--page-all`，但**同时保留了 `--page-size 100`**。两个 flag 冲突——lark-cli 在会议结束后卡在分页循环中，永远不返回 `"user is not in the meeting"` 错误。结果：TRAE Work Specialist 面试旁听 31 分钟后仍未检测到结束。

### 第二版 V6.1（成功）：去掉 `--page-all`

```python
# ❌ 首版 V6（卡死 — 两个 flag 冲突）
[LARK_CLI, "--page-size", "100", "--page-all", "--format", "json"]

# ✅ V6.1 修复（只用 --page-size）
[LARK_CLI, "--page-size", "50", "--format", "json"]
```

**结束检测**：合并 stdout + stderr，检测 `"user is not in the meeting"`：
```python
output = result.stdout + result.stderr
if "user is not in the meeting" in output:
    break
```

Python `capture_output=True` 默认分离 stdout/stderr，不会像 bash `2>&1` 自动合并。必须显式拼接。

## V3 poll.sh 的参考设计

V3 只用 `--page-all`（不带 `--page-size`）：
```bash
lark-cli vc +meeting-events --meeting-id <id> --page-all --format json 2>&1
```

Bash 的 `2>&1` 自动合并 stdout+stderr。Python 版如果用 `--page-all` 就不能再加 `--page-size`。

## 工作副本

| 文件 | 状态 |
|------|------|
| `/tmp/listen_subtitles_v6.py` | 首版（有 bug，`--page-all`+`--page-size`） |
| `/tmp/listen_v6_fixed.py` | ✅ 修复版（只用 `--page-size`） |
| `~/Documents/.../listen_subtitles.py` | 被僵尸进程锁死，无法替换 |

## 兜底写入

```python
finally:
    if all_lines:
        transcript_file.write_text("\n".join(all_lines))
    else:
        transcript_file.write_text("(无字幕)")
```

无论正常退出/异常/kill，都会写盘到 `~/.hermes/meeting_transcripts/<meeting_id>.txt`。
