# 会议纪要 Python 分析模板

## 快速统计（第一步）

```python
import json
from collections import Counter

lines = open("~/meeting_logs/<meeting_id>.jsonl").readlines()

speakers = Counter()
transcripts = []

for line in lines:
    d = json.loads(line.strip())
    if d.get("type") == "transcript":
        speakers[d.get("speaker", "?")] += 1
        transcripts.append(d)

print(f"总字幕: {len(transcripts)} 条")
print(f"时间: {transcripts[0]['time']} → {transcripts[-1]['time']}")

for sp, count in speakers.most_common():
    print(f"  {sp}: {count} 条 ({count/len(transcripts)*100:.0f}%)")
```

## 提取非本人发言（第二步）

```python
others = [t for t in transcripts if "袁鑫杰" not in t.get("speaker","")]
for t in others:
    print(f"[{t['time'][11:19]}] {t['speaker'][:15]:15s} {t['text'][:120]}")
```

## 追踪完整叙事弧线（第三步）

```python
# 每 ~N/20 条取一个样本，看全场讲了几段
for i in range(0, len(transcripts), max(1, len(transcripts)//15)):
    t = transcripts[i]
    print(f"[{t['time'][11:19]}] {t['text'][:150]}")
```

## 逐发言人展开（当有多人时）

```python
from collections import defaultdict
by_speaker = defaultdict(list)
for t in others:
    by_speaker[t["speaker"]].append(t["text"])

for sp, texts in sorted(by_speaker.items(), key=lambda x: -len(x[1])):
    print(f"\n=== {sp} ({len(texts)} 句) ===")
    for t in texts if len(texts) <= 30 else texts[::max(1, len(texts)//10)]:
        print(f"  {t}")
```

## 关键注意事项

- `time` 字段格式：`2026-07-30T14:23:47+08:00`，切片 `[11:19]` 取 `HH:MM:SS`
- 单人会议的 narrative arc 用 15-20 个采样点覆盖全场
- 多人会议优先提取非本人发言，本人发言量大时每 N 条取一条防噪音
- 轮询次数 × 10 秒 ≈ 会议时长（poll.sh 10s 间隔）
