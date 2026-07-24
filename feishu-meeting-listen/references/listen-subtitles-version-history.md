# listen_subtitles.py 版本演进

## V3（原始版—2026-07-22 上午）

**机制**：`empty_count > 4` 判会议结束

**问题**：
- API 超时（45s `lark-cli` timeout）→ 返回空事件 → 误判为会议结束
- 会议静默 20s（看文档/倒水）→ 触发空轮计数 → 误杀
- 实际案例：CodeM 培训、CEO 对话各被误杀 2 次以上

## V4（修复版—2026-07-22 下午，已验证稳定）

### 修复 1：会议结束检测

**方案**：空轮 → 先验证 → 再判结束

```python
if consecutive_empty >= MAX_EMPTY_BEFORE_CHECK:
    if not meeting_still_active(mid):  # 调 +meeting-list-active 验证
        # 真结束
    else:
        # API 暂时空，会议仍在——继续等
        print("[API 静默 N 轮，会议仍在进行，继续等待...]")
```

**验证**：CEO 对话会议期间出现 4 次「API 静默」，均未误杀。会后正常结束。

**教训**：API 空返回 ≠ 会议结束。必须交叉验证 `+meeting-list-active`。

### 修复 2：120002 不可入会检测

**问题**：大湾区 Power Hour 会议的「允许智能体加入会议」开关关闭。`lark-cli vc +meeting-events` 返回错误码 120002。旧版将其当空事件处理 → 空转 376 轮 → 0 字幕。

**方案**：`get_events()` 返回 `(events, error)` 元组。检测到 120002 立刻退出：

```python
def get_events(meeting_id):
    data = json.loads(r.stdout)
    if not data.get("ok", True):
        code = data.get("error", {}).get("code", "")
        if code in (120002,):
            return None, f"智能体不可入会 (错误 {code})"
    return data.get("data", {}).get("events", []), None
```

主循环：
```python
events, err = get_events(mid)
if err:
    print(f"\n[无法旁听] {err}")
    break
```

**输出**：
```
[无法旁听] 智能体不可入会 (错误 120002)
```

**教训**：旁听前应检测 API 错误（120002/120003/120004），不能把所有非 200 当空事件。
