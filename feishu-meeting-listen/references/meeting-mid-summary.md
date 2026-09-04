# 会议中实时提取内容

## 场景

会议进行中，用户想看"最近 5 分钟在聊什么"。

## 命令

```bash
python3.11 << 'PYEOF'
import json
from collections import Counter

# 读取日志文件
lines = open("/Users/bytedance/meeting_logs/<meeting_id>.jsonl").readlines()

# 估算最近 5 分钟的行数（约 80 条）
recent = []
for line in lines[-80:]:
    d = json.loads(line.strip())
    if d.get("type") == "transcript":
        recent.append(d)

speakers = Counter()
for t in recent:
    speakers[t["speaker"]] += 1

print(f"最近 ~5 分钟 ({len(recent)} 条)\n")

# 非袁鑫杰发言全部展示，袁鑫杰发言每 3 条取 1 条
for i, t in enumerate(recent):
    sp = t["speaker"]
    if "袁鑫杰" not in sp:
        print(f"[{t['time'][11:19]}] {sp[:15]:15s} {t['text']}")
    elif i % 3 == 0:
        print(f"[{t['time'][11:19]}] {sp[:15]:15s} {t['text']}")
PYEOF
```

## 会后生成完整纪要

```bash
python3.11 << 'PYEOF'
import json
from collections import Counter, defaultdict

lines = open("/Users/bytedance/meeting_logs/<meeting_id>.jsonl").readlines()
transcripts = [json.loads(l) for l in lines if json.loads(l).get("type")=="transcript"]

# 发言人统计
speakers = Counter(t["speaker"] for t in transcripts)
# 时间范围
first, last = transcripts[0]["time"], transcripts[-1]["time"]
# 非自己发言
others = [t for t in transcripts if "袁鑫杰" not in t["speaker"]]
# 按发言人分组
by_speaker = defaultdict(list)
for t in others:
    by_speaker[t["speaker"]].append(t["text"])

# 抽样展示叙事弧线
for i in range(0, len(transcripts), max(1, len(transcripts)//20)):
    t = transcripts[i]
    print(f"[{t['time'][11:19]}] {t['text'][:120]}")
PYEOF
```

## 注意事项

- 日志行数 / 会议分钟数 ≈ 10-15 行/分钟，估算窗宽
- 提取"非袁鑫杰"发言时先单独展示，避免被自己说话淹没
- 叙事弧线用固定间隔采样（≈20 个点），不要全量展示
