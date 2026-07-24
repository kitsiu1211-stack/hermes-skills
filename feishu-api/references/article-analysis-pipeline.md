# 公众号文章分析流水线

当用户分享微信公众号/外部文章链接时，执行以下完整流水线：

## 流程

### 1. 抓取文章
```bash
browser_navigate(url) → browser_snapshot(full=true)
```
从 snapshot 提取全文内容。微信文章内容在 `#js_content` 或正文段落中。

### 2. 双重拆解
同时跑两个技能，产出写入 `~/Documents/Hermes Context/articles/`：

**ljg-rank（降秩）**：找领域背后真正撑着它的几根独立的力
- 输出：`{ts}--{领域}的秩__rank.md`
- 核心：递归下沉找 root rank → 反生成验证 → 可选坐标系

**ljg-learn（概念解剖）**：从 rank 找出的骨架里挑一个核心概念做八维解剖
- 输出：`{ts}--概念解剖-{概念名}__concept.md`
- 核心：定锚 → 八刀 → 内观 → 压缩

### 3. 输出卡片
拆完直接出飞书交互式卡片，不再问意图。按内容量拆分（最多2张）：

```python
# 卡片1: Rank 摘要
# 卡片2: Learn 摘要

import json, subprocess
FEISHU_CLI = "/Users/bytedance/.npm-global/bin/feishu-cli"

payload = {
    "params": {"receive_id_type": "open_id"},
    "data": {
        "receive_id": "ou_dc055b0b5b0b5db2b1af5e79c0536db6",
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False)
    }
}
subprocess.run([FEISHU_CLI, "exec", "im.v1.message.create", "--params", json.dumps(payload, ensure_ascii=False)])
```

## 卡片规则
- 手机优先：Header 正常表达不堆大词
- 信息精炼分段：加粗/分割线/缩进
- 超限按逻辑拆卡：概述+分拆+结论
- 优先1张，最多2张
- 禁云文档兜底
- 卡片即完整输出，不补文字摘要

## 写入路径
所有 rank 和 learn 产出 → `~/Documents/Hermes Context/articles/`
不碰用户的知识图谱 vault（`~/Documents/Obsidian Vault/`）
