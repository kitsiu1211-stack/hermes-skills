# 实时语音对话调试全记录 (2026-07-17)

## 目标

实现会议内低延迟双向实时语音：ASR → LLM → TTS → 会议音频

## 最终成功架构

```
MacBook 麦克风 → PyAudio → Paraformer-realtime-v2 (DashScope WS)
                                    ↓
                              DeepSeek LLM
                                    ↓
                    豆包 TTS (小何 2.0, 子进程隔离)
                                    ↓
                            afplay → 扬声器 (用户可听到)
```

**端到端延迟 ~2-3 秒**（ASR 流式 + LLM 1s + TTS 500ms + afplay）

## 关键排坑（按发现顺序）

### 1. 豆包凭据混用 → 结论矛盾

**症状**：前面说豆包通了，后面又不通

**根因**：
- 话题中：新版 API Key (`X-Api-Key: c3c35e49`) → 通过
- 主流程复测：旧版凭据 (`X-Api-App-Id + X-Api-Access-Key`) → `data:null`

**教训**：凭据统一到 `config/.env`，复测前读上次成功脚本确认凭据一致。

### 2. BlackHole 回路不通

**测试**：PyAudio 往 BlackHole 输出 660Hz tone → 同时从 BlackHole 输入读取 → 峰值仅 458（噪声级别）

**结论**：直接往 BlackHole 输出数据**不会被回路读回**。BlackHole 的回路机制依赖系统级音频路由。

### 3. 会议旁听才是正确路由

**关键发现**：
- `afplay → 会议旁听（多输出设备）` → BlackHole 能收到音频 ✅
- `PyAudio → 直接写 BlackHole` → BlackHole 收不到 ❌

**为什么**：会议旁听是 Apple Multi-Output Device，系统 CoreAudio HAL 负责将音频流复制到所有子设备（包括 BlackHole）。PyAudio 直写绕过了 HAL 路由层。

### 4. 正确音频路由配置

```
系统输出: 会议旁听 (MacBook Air扬声器 + BlackHole 2ch)
飞书麦克风: BlackHole 2ch (收 TTS)
飞书扬声器: 会议旁听 (听其他人)
```

`afplay` 往系统默认输出（会议旁听）播放 → 音频同时到扬声器（用户听到）和 BlackHole（飞书麦克风收到）。

**仅用户本人时**：回声消除导致 TTS 不通过扬声器——飞书认为这是麦克风通道的音频，消掉了。

### 5. Paraformer sentence_end 不可靠

**症状**：短句 "Hello浪子。" Paraformer 不标 `sentence_end=True`，触发逻辑完全跳过。

**修复**：不依赖 `sentence_end`。任意 ASR 中间结果含关键词即走判断流程，仅靠冷却（2s）控制频率。

### 6. 去重跨会话残留

**症状**：重启 V4 后"浪子"被标记为已回复 → 不响应

**根因**：去重 hash 文件 `r_<md5>` 持久化在 `~/.hermes/cache/meeting_voice/`，跨脚本重启不自动清理。

**修复**：**完全去除内容去重**。短触发词（「浪子」）MD5 恒等 → 全拦截。仅靠冷却（2秒）控制频率。

### 7. TTS `asyncio.run()` 主线程阻塞 → 线程方案失败 → 最终子进程隔离

**症状**：`[TTS] synthesizing '...'` 后卡死，永不返回。但手动独立脚本中同代码秒级成功。

**第一次尝试（线程隔离）**：
```python
def _run_tts_thread(text, result_holder):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(doubao_tts(text))
    loop.close()
    result_holder.append(result)
```
**结果**：仍卡在 `synthesizing`。线程内新事件循环仍与主线程 PyAudio+WebSocket 回调冲突。

**根因**：主线程运行着 `while True` 音频处理 + `websocket.WebSocketApp.run_forever()`（ASR），`websockets.connect()`（TTS）的事件循环调度被阻塞。

**最终修复（子进程隔离）**：
```python
def speak(text):
    result = subprocess.run([
        sys.executable, "-c", f"""
import asyncio, json, uuid, os, sys
sys.path.insert(0, os.path.expanduser("~/.hermes/scripts"))
from doubao_tts_proto import ...

async def tts():
    # 独立的 Python 进程，无事件循环冲突
    ...
    print("OK")  # 父进程通过 stdout 判断成功

asyncio.run(tts())
"""
    ], capture_output=True, text=True, timeout=30)
    if "OK" in result.stdout:
        subprocess.run(["afplay", path], timeout=30)
```

### 8. `.env` 尾部注释污染变量值 🔥

**症状**：手工独立 Python 脚本 TTS 正常，但 V4 脚本内 TTS 返回空音频。`[SPEAK]` 打印了但无声。极难排查。

**根本原因**：
```
# 错误的 .env：
DOUBAO_TTS_SPEAKER=zh_female_xiaohe_uranus_bigtts  # 小何 2.0

# Python 解析 split("=",1) 读到：
speaker = "zh_female_xiaohe_uranus_bigtts  # 小何 2.0"
```

包含 `#` 注释的 speaker 名导致豆包 API 返回空音频（不报错，静默失败）。

**为什么手工脚本正常**：手工测试时硬编码了正确的 speaker 名。

**修复**：`.env` 中**禁止行尾 `#` 注释**。所有注释独占一行。排查时 `print()` 加载后的实际值。

**教训**：手工能通、脚本不通 → 必是环境差异。`.env` 加载后 `print()` 实际值是第一步排查手段。

## 豆包 TTS 协议要点

- **端点**：`wss://openspeech.bytedance.com/api/v3/tts/bidirection`
- **Resource ID**：`seed-tts-2.0`
- **音色**：`zh_female_xiaohe_uranus_bigtts`（小何 2.0）
- **协议库**：`~/.hermes/scripts/doubao_tts_proto.py`（从官方 SDK 提取）
- **握手**：StartConnection → StartSession → TaskRequest → FinishSession
- **音频流**：`MsgType.AudioOnlyServer`（二进制），在 `SessionFinished` 事件前持续接收

## 当前限制

- 飞书会议仅用户本人时，回声消除导致 TTS 不通过扬声器播放（麦克风通道被消）
- 会议路由（TTS → 飞书参会者听到）待修：需聚合设备合并 MacBook 麦克风 + BlackHole
- 常量橙色麦克风指示灯（V4 持续占用 MacBook 麦克风做 ASR）
