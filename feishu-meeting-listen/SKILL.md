---
name: feishu-meeting-listen
description: Agent-driven Feishu meeting observer. Three modes - Voice interaction, Chat reply, Silent eavesdrop. Standard meetings for voice/chat, any meeting for eavesdrop.
category: feishu
---

# 飞书会议旁听（智能体入会）

## 🚨 核心纪律

**唯一入会方案**：官方 Bot 入会（`main.py`）或字幕旁听（`meeting_transcribe.py`）。

**Bot 入会前提**：
1. 灰度资格（你在智能体入会体验群 `oc_8a93e6271847efa53ced90301647ea66`）
2. 🚨 **会议权限「允许智能体加入会议」必须勾选**（官方 doc `VXnpdcUFWotAmexKWmUcAwA4nCe` §7.2 明确要求：会议右下角 → 安全设置 → 智能会议权限 → 勾选该项。**这是 ByteView 无音频流的最高概率根因。** Bot 能入会但听不到声音，99% 是这个开关没开。官方验证清单中「会议语音触发豆包 ASR / Chat / TTS」已打 ✅）
3. 标准会议（9 位号）+ 至少 1 个真人在场说话（空会议豆包会断开，错误码 45000001）
4. **戴耳机**——外放回声会让 Bot 被自己打断（barge-in 默认开启）
5. `--check` 全绿（凭据就位）
6. `config.yaml` 的 `opening_line` + `doubao_model` 已填充——两个字段通过 `_start_session_payload` 传给豆包（`opening_line` 在根级别，不是 `dialog` 子字段）；`say_text()` 已从 main.py 移除，不触发语音

**🎭 人设灵活性**（2026-07-21 修正）：
- ❌ **旧 persona**：锁死「AI销售助手，只能提供客户洞察」——豆包端到端模型严格跟随 `system_role`，用户说「你不智能」就是因为人设太窄，LLM 只能回答客户相关，无法动态适配会议类型
- ✅ **新 persona**：通用智能助理，根据会议类型动态适配——客户会议→C360洞察，内部会议→纪要待办，闲聊测试→正常对话
- **persona.md 原则**：不要加「只能」「仅限」「核心职责是…」等硬限制词。给豆包足够的灵活性去理解用户实际意图。加一句「用户说下会/退出时回复确认并准备离会」让模型配合 auto-exit

**🚨 Bot 入会无声——诊断优先级**（2026-07-23 更新）：

**🎯 一级诊断：Bot 入会时序竞争**（2026-07-23 发现）：`lark-cli vc +meeting-join --as bot` 后立刻启动 `main.py` → ByteView WebSocket 握手成功但**无音频流**（`[bv] raw msg` 从未出现）。**修复**：bot join 后 `sleep 3` 再启动 main.py。同一会议 378074339/900264021 的 8 次失败→1 次成功验证了时序是关键变量。**现在启动流程**：先 join，sleep 3，再启动 main.py。

**🎯 二级诊断：ByteView 音频兼容性**（2026-07-23 发现）：即使 bot 入会+时序正确，部分正式会议仍无 ByteView 音频流。`[bv] raw msg` 从未出现 = 会议创建时未启用实时音频能力。**「袁鑫杰的视频会议」模板创建的会议有音频，其他模板创建的可能没有。** 无音频时降级为字幕旁听+会议聊天框文字回复。详见 `references/byteview-meeting-compatibility.md`。

**核心发现**：ByteView 音频一直在流（每秒 10+ 条 4800 字节音块），之前误判为「ByteView 不推流」是因为日志只打印每 50 条。真正根因在**豆包侧 `send_audio` 漏 `session_id`**——加 `raw msg` 日志后确认真相，修复后 ASRResponse 事件狂涌。

1. **先加 ByteView raw 消息日志**：在 `receive_audio` 开头加 `log("bv", "raw msg", idx=idx, raw_len=len(message))` → 验证音频是否真的在流。**不要只看 `fwd` 日志**——`fwd` 每 50 条才打印一次，会被误判为没数据。
2. **查豆包 `session_id`**：新版 `protocols.py` 的 `Message` 类中 `send_audio` 必须带 `flag=WithEvent` + `event=TaskRequest` + `session_id=self.session_id`。旧版 `NoSeq` flag 不含 session_id → **豆包静默丢弃所有音频**（10 次测试零响应）。
3. **验证 ASR**：修复后应出现 `[doubao] recv msg type=FullServerResponse event=ASRResponse payload_size=736`（payload_size 递增 = 逐字识别）
4. **等 TTS 音频流**：ASR 积够语言后出 `AudioOnlyServer` 消息 → `forward_doubao_to_byteview` 发回会议

**修复代码**（`voice_agent/doubao.py` 第 91-93 行）：
```python
# ❌ 旧版（无声）
msg = Message(type=MsgType.AudioOnlyClient, flag=MsgTypeFlagBits.NoSeq)
msg.payload = audio

# ✅ 新版（带 session_id）
msg = Message(type=MsgType.AudioOnlyClient, flag=MsgTypeFlagBits.WithEvent)
msg.event = EventType.TaskRequest
msg.session_id = self.session_id
msg.payload = audio
```

**官方参考 doc**：`VXnpdcUFWotAmexKWmUcAwA4nCe` — 飞书语音 Agent 入会与豆包实时语音完整配置方案（含完整代码附录）

**豆包排坑速查**：`references/doubao-realtime-debug.md`

**绝对不要对用户说「帮我回忆一下」或让用户替你回忆任何事情。** 会议日志、客户信息、历史对话——全部自己去 `meeting_logs/`、`session_search`、C360 CLI 查。找不到就诚实说「我翻遍了但没找到」，不要反问用户。回忆和检索是你的工作，不是用户的。

## 触发条件

**入会触发器**（2026-07-21 用户偏好）：用户发来任何消息 → 立即 `lark-cli vc +meeting-list-active --as user` → 有会议就 `main.py --meeting-no <no>` 入会。不需要用户说「旁听」「入会」「进会」——Agent 主动检测、主动入会。❌ 不用定时任务、不用脚本、不用 cron。

**聊天监控**：入会后 `poll_meeting_chat()` 自动运行，检测「浪子」触发回复。

**字幕旁听**：用户说「旁听会议」→ `listen_subtitles.py`（bot 入会 + 字幕轮询）。详见 `references/subtitle-polling.md`。

**🎯 三种入会模式**（2026-07-22 最终定型）：

| 模式 | 入会方式 | 触发 | 回复 | 适用 |
|------|---------|------|------|------|
| **语音交互** | bot `+meeting-join` | 语音 → 豆包 ASR → Hermes → 豆包 TTS | 语音播回会中 | 需要交互的标准会议 |
| **弹幕回复** | bot `+meeting-join` | 弹幕'浪子' → Hermes → `vc +meeting-message-send` | 文字回弹幕 | 需要交互的标准会议 |
| **静默旁听** | ❌ 不入会 | 字幕流 → 会后自动出纪要 | 飞书卡片 | 纯旁听，不打扰 |

**🚨 纪要客户识别铁律**（2026-07-22）：
会议标题 ≠ 字幕内容中提到的所有公司。不要从字幕中猜客户——字幕里讨论的其他公司（如案例引用）不是会议对象。
- ✅ 正确：纪要客户 = 会议标题中的客户名（如标题为「AI解决方案沟通」则不要猜客户，如实写「AI解决方案沟通」）
- ❌ 错误：字幕中提到「拓竹有 5 家门店了」→ 纪要写成「拓竹 x 飞书」。拓竹是案例引用，实际客户是智能派
- **判断标准**：标题写了谁就是谁的会，标题没写就不猜

**静默旁听关键发现**（2026-07-22）：
- ✅ `--as user` 轮询 `+meeting-events` **可以用于长时间旁听**。之前误判为「不可靠」是因为会议结束后 API 返回空 JSON 触发未捕获的 `JSONDecodeError`。**加 `try/except` 处理后完全稳定**。
- ✅ 用户自己已在会中 → 用户身份直接读自己的字幕流，无需 bot 入会。
- ✅ `transcript_received` 事件的字段是 `transcript_received_items`（不是 `transcript_items`）——这是之前脚本采集不到文字的根因。
- ❌ `--as bot` 不入会直接读事件 → `code 120004: bot is not in the meeting`。Bot 必须先入会才能读事件。
- **结论**：静默旁听用 `--as user` 不入会，语音/弹幕交互才用 bot 入会。`listen_subtitles.py` 已更新为此方案。

## 当前架构（2026-07-22 三模式最终定型）

```
模式 1: 语音交互（bot 入会）
  入会: ✅ Bot +meeting-join --as bot
  方案: main.py — ByteView WebSocket + 豆包端到端实时语音
  语音: 豆包 ASR → Hermes → 豆包 ChatTTSText TTS
  离会: ASR 检测"下会/退出/离开"→ 自动退出
  适用: 标准会议，灰度资格，owner 开启「允许智能体入会」

模式 2: 弹幕回复（bot 入会）
  入会: ✅ Bot +meeting-join --as bot
  方案: poll_meeting_chat() 监听 chat_received → "浪子"触发
  回复: lark-cli vc +meeting-message-send --as bot 文字回弹幕
  适用: 标准会议，bot 具有 vc:meeting.message:write 权限

模式 3: 静默旁听（不入会）✅ 2026-07-22 验证稳定
  入会: ❌ 不入会，--as user 直接读 events
  方案: listen_subtitles.py — 每 5s 轮询 +meeting-events
  字幕: transcript_received → transcript_received_items[].text
  输出: 增量保存 → 会结束自动写 inbox + bot 消息通知 → Hermes 出纪要
  适用: 任何会议（用户本人在会即可），零打扰
```

**🚨 模式 3 脚本特性**（2026-07-22 最终修复）：
- **不入会**：`--as user` 直读，无 bot join/leave 开销
- **增量保存**：每收新字幕即写盘，crash 不丢数据
- **异常兜底**：`JSONDecodeError` / API 空返回不崩；45s 超时防 API 响应慢
- **会议结束检测**：❌ 旧方案（空轮计数）→ ✅ 新方案（`meeting_still_active()` 验证）
  - 连续 4 轮 API 返回空 → 调用 `lark-cli vc +meeting-list-active` 确认会议是否仍在活跃列表
  - 仍在活跃 → 打日志「API 静默 N 轮，会议仍在进行，继续等待...」
  - 已不活跃 → 判定结束，再等几轮收最后字幕
  - **教训**：API 超时 ≠ 会议结束。静默 20 秒太常见（看文档、倒水），必须验证真结束。
- **多会议支持**：每个会议传 meeting_id 参数独立启动一个进程。`listen_subtitles.py <meeting_id>`。
- **自动触发纪要**：会结束 → 写 `meeting_inbox.json` + bot 发「纪要请求」→ Hermes 处理
- 脚本位置：`~/Documents/Codex_Project/feishu-voice-agent-starter/listen_subtitles.py`

**🚨 Bot 入会仅支持标准会议**：个人视频通话无 9 位号，`auto_detect_meeting()` 自动降级为字幕旁听。

**💬 会中聊天 — 标准+个人会议均支持**（2026-07-21 验证，2026-07-23 修复限流）：`vc +meeting-events --as bot` 的 `chat_received` 事件在个人会议中也正常推送。已在个人会议 556362268 中验证捕获「浪子，这个会议主题是什么」消息。

**🚨 chat poll 限流修复**（2026-07-23）：`+meeting-events --as bot` 每 3s 轮询触发 **99991400 频率限制**（`request trigger frequency limit`）。修复：轮询间隔从 3s → 10s（`main.py` L296）。**必须用 `--as bot`**（`--as user` 之前出过问题——用户反馈）。

**📦 V4 永久死亡**（`meeting_voice.py`）。用户多次强调「不要跑 V4」。永不复活。TTS 切 Fish Audio 为临时方案，官方入会走豆包端到端。

### 模式 0: V3 poll.sh（主力旁听方案）✅

**当前激活方案**。固定 meeting_id，bash 脚本，每 10 秒拉字幕/聊天/进出事件，JSONL 持久化。稳定可靠。

```bash
# 用法
bash ~/.hermes/skills/feishu/feishu-meeting-listen/scripts/poll.sh <meeting_id> <meeting_title>

# Agent 启动（background=true, notify_on_complete=true）
# 脚本自动检测离会 → 退出 → Agent 收到 notify → 生成纪要
```

**特性**：
- 固定 meeting_id——不跳、不丢、不误切
- Python set() 去重——sentence_id 级别
- JSONL 格式干净：`{type, speaker, text, sentence_id, time}`
- 检测到 "user is not in the meeting" 自动退出
- 零 token 消耗（纯 bash + Python，不进 LLM）

**meeting_transcribe.py 已弃用**（2026-07-20）。该脚本用 `+meeting-list-active` 自动检测 meeting_id，会议结束/切换时 ID 漂移导致日志丢失。V3 poll.sh 固定 ID 传入，从架构上消除此问题。

### 🆕 官方入会（Bot 真实入会 + 豆包端到端实时语音）

**2026-07-21 session_id 修复**：累计 10 次测试定位到根因——`send_audio` 漏 `session_id`。修复后 ByteView→Doubao 音频全量送达，豆包 ASRResponse 单句递增（payload 736→868 字节，逐字识别中）。TTS 音频流待完整句子触发后验证。

> ⚠️ 端到端模型需足够语音上下文才触发 TTS 回复——单字或短词不会出声。建议连续说完整句子。`opening_line` 已通过 `start_session` payload 传入（根级别，非 dialog 子字段），`say_text()` 已从 main.py 移除。

```bash
cd ~/Documents/Codex_Project/feishu-voice-agent-starter
python3 main.py    # 自动检测活跃会议 + 入会
# 或 python3 main.py --meeting-no <9位号>
```

**🛑 事件驱动入会阻塞**（2026-07-21）：
- `vc.meeting.participant_meeting_joined_v1` 事件需要 `vc:meeting.meetingevent:read` scope
- App `cli_a964fd626078dcbc` 存在远程事件消费者（`online_instance_cnt=1`），阻塞所有本地事件订阅
- 开放平台在线实例状态未知，需用户去控制台检查
- **当前方案**：用户发消息 → Agent 扫描活跃会议 → 立即入会。不需要定时任务、不需要脚本

通过 `vc +meeting-events` 的 `chat_received` 事件 + `meeting_chat_reply.py` 监控脚本。触发词"浪子"→ DeepSeek API 即时生成内容相关回复 → `lark-cli vc +meeting-message-send` 发回会议聊天框。API 超时自动 fallback 模板。详见 `references/meeting-chat-reply.md`。

**🎯 回复模式**（2026-07-21 最终架构——两条完全独立链路，统一大脑）：

| 触发 | 大脑 | 回复方式 |
|------|------|---------|
| 会中弹幕「浪子」 | Hermes（文件队列 bridge） | 文字发回会议聊天 (`@sender 回复内容`) |
| 会中语音说话 | 豆包 ASR → Hermes（bridge） | 豆包 ChatTTSText（event=500）TTS → ByteView 播回 |

🚨 **两条链路绝不互串**：弹幕永远用文字回，语音永远用语音回。

**Bridge 架构**（2026-07-21 最终方案——HTTP push，不用文件轮询）：

**文件队列已废弃**（2026-07-21 下午实测）：
| 方案 | 延迟 | 可靠性 | 结论 |
|------|------|--------|------|
| ~~文件队列（inbox/outbox 轮询）~~ | ~~1-45s~~ | 依赖 Hermes 主动检查，会超时。beta "暂时不确定"占大多数 | ❌ 废弃 |
| **HTTP push（localhost:19876）** ✅ | ~0ms | Hermes 直接 POST，bot 立即行动。已验证端到端 | ✅ 生产 |

**关键代码**（`main.py`）：
- `_ask_hermes(channel, sender, text, meeting_id)` — 写 inbox 文件仅作标记（`push_question`），不轮询 outbox。**fire-and-forget 模式**：函数无返回值，回复异步通过 HTTP push 到达
- `_run_http_server(lark, meeting_id, doubao, stop_event)` — aiohttp 监听 `localhost:19876/reply`，Hermes POST `{"channel":"chat"/"voice", "sender":"袁鑫杰", "reply":"..."}` → voice 走 `doubao.say_tts()` / chat 走 `lark.meeting_message_send()`
- `@routes.post("/reply")` handler 区分 channel：voice → `doubao.say_tts(reply)`，chat → `lark.meeting_message_send(meeting_id, f"@{sender} {reply}")`
- **不要从 `_ask_hermes` 返回值**——它是 fire-and-forget。回复通过 HTTP push 异步到达

**Hermes 侧回复**：收到用户消息 → `read_file ~/.hermes/meeting_inbox.json` → 思考 → `curl -X POST http://localhost:19876/reply -H "Content-Type: application/json" -d '{"channel":"...","sender":"...","reply":"..."}'`

**语音链路**（`forward_doubao_to_byteview()`，2026-07-21 新架构）：
1. ByteView 音频 → 豆包 ASR 识别文字
- `receive_audio()` 现在 `yield str`（ASR 文字）+ `yield bytes`（豆包 TTS，全部转发不丢弃）——返回类型改为 `AsyncIterator[bytes | str]`
- `forward_doubao_to_byteview` 用 `isinstance(msg, bytes)` vs `isinstance(msg, str)` 分支路由：bytes → 直接 forward 到 ByteView，str → 走 Hermes bridge → `doubao.say_tts()`
- **🐛 ASR 空白调试**（2026-07-21）：当 ASR 始终返回空文本时，在 `receive_audio()` 的 ASRResponse 分支加 `asr_raw = msg.payload.decode("utf-8")` 打印原始 JSON payload，确认字段路径。已知豆包可能因环境噪音生成 ChatResponse+TTS 响应但 ASR text 为空。
3. Bridge 问 Hermes 获取回复文字
4. `doubao.say_tts(reply)` 通过 **ChatTTSText（EventType=500）** 触发豆包纯 TTS——这是豆包协议的 TTS-only 上游事件，不经过 Chat 模型，直接将文字转语音。区别于 `say_text()`（SayHello=300，触发全链路 ASR→Chat→TTS）
5. 豆包 TTS 音频经 ByteView 播回会议
6. 豆包仅做 ASR + TTS——大脑是 Hermes，嘴是豆包 TTS

**ChatTTSText 关键发现**（2026-07-21）：`protocols.py` 的 `EventType` 枚举中 `ChatTTSText = 500`，注释为 "(Ground-Truth-Alignment) text for speech synthesis"。这是纯 TTS 上游事件，不需要改变 WebSocket 模式或启动新连接。

**用户明确要求**：
- 「不要在发现弹幕说时用语音说，这样就混了」
- 「语音回复你是写死的么 我理解应该和弹幕回复是同样的链路 只不过加上豆包 tts 变成语音回复」
→ 统一用 DeepSeek。语音 = ASR + DeepSeek + TTS，弹幕 = DeepSeek + 文字。同一大脑，不同嘴。

**文字回复实现**（`main.py` `poll_meeting_chat()`, 2026-07-21 验证通过）：
1. `chat_received` 事件检测到「浪子」→ 构造回复文本
2. 调用 `lark.meeting_message_send(meeting_id, reply)` 发送
3. `lark_cli.py` 的 `meeting_message_send()` 封装 `lark-cli vc +meeting-message-send --as bot --msg-type text`
4. 🚨 必须用 `--as bot`（非 user）——需在飞书开发者控制台申请 app scope `vc:meeting.message:write`，链接：`https://open.feishu.cn/page/scope-apply?clientID=cli_a964fd626078dcbc&scopes=vc%3Ameeting.message%3Awrite`。授权后 `--as bot` 即可发送，回复显示为 bot 身份。`--as user` 虽立即可用但回复者显示为用户本人。

**关键命令**：`lark-cli vc +meeting-message-send --as bot --meeting-id <id> --msg-type text --text "回复内容"`
**防死循环**：10 秒 cooldown + `sender == "浪子"` 跳过自消息。bot 发送的回复也会产生新的 `chat_received` 事件，必须过滤。

**🐛 已知：事件系统被远程消费者阻塞**（2026-07-21）：
- 本地 `lark-cli event consume` 报 `another event bus is already connected (1 remote)` for all event types (IM + VC)
- 远程消费者源未知（可能来自开放平台→事件订阅→在线实例）
- 影响：无法实现事件驱动的自动入会；`vc.meeting.participant_meeting_joined_v1` 对个人会议不触发（双重阻塞）
- **当前方案**：用户发消息 → Agent 扫 `+meeting-list-active` → 立即 `main.py` 入会。无需脚本、无需定时任务。

**🐛 已知：日志溢出**（2026-07-21）：
- ByteView `raw msg` 每秒 10+ 条 → 10 分钟内数千条 → chat poller 的 `[chat]` 日志被淹没，无法回溯
- **临时方案**：加大 `fwd` 日志间隔（50→200），减少音频日志密度；用 `grep 'chat\|trigger'` 单独搜索

| 特性 | 说明 |
|------|------|
| 入会方式 | Bot API 真实入会 (`lark-cli vc +meeting-join --as bot`) |
| 音频 | ByteView WebSocket 双向 24kHz PCM |
| 语音模型 | 豆包端到端实时语音（一体 ASR+LLM+TTS） |
| 听到范围 | ⚠️ 代码/连接验证通过，**端到端会议内语音发言待验证**（SayHello TTS 无声，见下方 Bug） |
| 所需权限 | `vc:meeting.bot.join:write` + `vc:meeting.bot.realtime:write` ✅ 已授权 |
| 会议检测 | 已融合 `auto_detect_meeting()`，不传 `--meeting-no` 自动获取 |
| 限制 | 仅标准会议（9位号），需 owner 开启「允许智能体入会」 |
| 前置条件 | 灰度资格 + 会议安全设置 + `main.py --check` 全绿 |

**🫧 豆包端到端语音质量实测（2026-07-23 持续优化）**：

浪子在会议中已能正常对话（ASR → 豆包端到端 LLM+TTS → ByteView 回传）。实测发现以下质量特征：

| 问题 | 表现 | 状态 |
|------|------|------|
| 语音卡顿 | 句子中间卡顿，无法完整说一段话 | ✅ **2026-07-23 已修复**：`byteview.py` `send_audio()` 保留分片+去 sleep |
| 语音延迟 | 用户说话后等 2-3 秒才有回复 | ✅ **2026-07-23 已优化**：`doubao.py` `_start_session_payload()` 中 `end_smooth_window_ms` 从 1500→500ms，省 ~1s。实测验证有效 |
| 仅普通话 | 用户要求说粤语 → 浪子「我暂时只会说普通话」 | ⚠️ 豆包模型限制 |
| 看不到聊天 | 用户发「浪子，你能看到我的信息么」→ 不确定 | ⚠️ 端到端模型无聊天感知 |
| 字节音频不流 | Bot 入会后 ByteView 无 raw msg | ✅ **2026-07-23 已修复**：bot join 后 `sleep 3` 再启 main.py |
| 字节音频兼容 | 部分正式会议 ByteView 无音频流 | ⚠️ 会议创建时决定，监控 `raw msg` 出现降级 |

这些是模型能力边界，非代码 Bug。向用户展示浪子能力时主动说明三点限制。

**🐛 豆包静默会话**（2026-07-23 发现）：偶发——豆包连接成功、session started、ByteView 音频持续流入（raw msg 不断），但豆包零响应（无 ASR/无 Chat/无 TTS）。`opening_line` 也不触发。**根因不明（可能豆包服务端异常）**。**workaround**：kill 进程 → 重入会 → 重启 main.py，通常新会话恢复正常。同一会议 273700435 上 2 次静默后第 3 次正常。

**🐛 已知 Bug：Bot 入会 + 豆包不出声**（✅ 2026-07-21 已定位并修复）

- **根因**：`voice_agent/doubao.py` `send_audio()` 使用新版 `protocols.py` 二进制协议的 `Message` 类，但 `AudioOnlyClient` 消息的 `flag: NoSeq` 不包含 `session_id`。导致豆包收到音频后无法关联会话，静默丢弃。10 次测试中 ByteView→Doubao 音频全量送达，但零 ASR/TTS 事件。
- **修复**：改 `flag=NoSeq` 为 `flag=WithEvent` + `event=TaskRequest` + `session_id=self.session_id`
- **验证**：修复后首次入会即出现 `[doubao] recv msg type=FullServerResponse event=ASRResponse payload_size=736`（payload 从 736→868 字节逐句递增，确认逐字识别中）
- **教训**：ByteView 无音先别怀疑飞书——加 raw msg 日志看 ByteView 侧是否真的在发消息。`fwd` 日志每 50 条才打印一次，会误判为「没数据」

**🚪 语音离会机制**（2026-07-21 实现）：
- **原理**：`doubao.py` `receive_audio()` 解析 ASRResponse payload 中的 JSON `result`/`text` 字段，检测到「下会/退出/离开/不用了/没事了」关键词时设置 `self.exit_requested = True`
- **main.py 新增 `_monitor_exit()` 协程**：每 0.5s 轮询 `doubao.exit_requested`，检测到后设置 `stop_event` → 触发 `finally` 块 → `byteview.close()` + `lark.leave_meeting()` → Bot 自动离会
- **注意**：豆包 TTS 回复「好的，随时叫我」后会通过 ASR 抽到自己的回复文本，不会误触 exit——因为检查的是 `result`/`text` ASR 字段（真人语音），不是 TTS 文本
- **代码位置**：`voice_agent/doubao.py` L96-L128（ASR 检测）+ `main.py` L142-L155（`_monitor_exit` 协程）

**💬 会中聊天 @浪子 回复机制**（2026-07-21 ✅ 已验证全链路）：
- **数据源**：`vc +meeting-events` 的 `chat_received` 事件——无需 IM 事件订阅。标准+个人会议均支持。
- **轮询**：`main.py` 中 `poll_meeting_chat()` 协程每 3 秒轮询，`message_type=1`（文本）+ `seen_ids` 去重
- **回复**：纯 lark-cli 直接回复。**不走豆包、不走 TTS**。`lark.meeting_message_send(meeting_id, reply)` 用 `lark-cli vc +meeting-message-send --as bot --msg-type text` 发回会议聊天框
- **格式**：`@{sender} 回复内容` —— @ 明确回复对象，多人会议不混乱
- **防死循环**：10 秒 cooldown + 跳过 sender="浪子" 的自消息（bot 回复也会产生新的 chat_received 事件）
- **权限**：bot 需在开放平台控制台申请 `vc:meeting.message:write` scope（**app 级别 scope，非用户授权**）→ `--as bot` 发送。申请链接：`https://open.feishu.cn/page/scope-apply?clientID=cli_a964fd626078dcbc&scopes=vc%3Ameeting.message%3Awrite`
- **智能回复**（2026-07-21 最终方案）：不用豆包。poller 检测到「浪子」→ 问题写入 `~/.hermes/meeting_question.json` → Hermes（DeepSeek）读取、思考、调用 `lark-cli vc +meeting-message-send --as bot` 回复到会中。零豆包管线。
- **注意**：`--as user` 虽然立即可用但回复者显示为用户本人，非 bot。正式使用必须用 `--as bot`。

**用户明确要求**：
- 「不要在发现弹幕说时用语音说，这样就混了」
- 「语音回复你是写死的么 我理解应该和弹幕回复是同样的链路 只不过加上豆包 tts 变成语音回复」
- 「为什么要豆包理解，你不能调用 lark cli 的能力直接回复么？」
- 「不要用豆包，但你不是接了 DeepSeek 么」
- 「我理解应该是你入会之后，其实你大脑还是DeepSeek……像一个实时的AI助理一样」
- **「会议只是我的另一个耳朵和嘴巴，同一个 Hermes 大脑」**——不要把 main.py 做成独立 DeepSeek 调用者。Hermes 是唯一的大脑，main.py 只做 ASR 耳朵 + TTS 嘴巴
→ **最终架构**：main.py 只是耳朵（ASR）和嘴巴（TTS），大脑是 Hermes。`~/.hermes/meeting_inbox.json` / HTTP push 桥接。

**🚨 用户说「开麦」时**：不要在被告知「Bot API 无麦克风权限」后就放弃。执行以下流程：
1. Bot 已在会中（从 `vc +meeting-join` 返回确认）
2. 启动语音管线：`cd ~/Documents/Codex_Project/feishu-voice-agent-starter && python3 main.py --meeting-no <no>`
3. 语音管线依赖：ByteView WebSocket + 豆包端到端实时语音 + BlackHole 音频路由
4. 如果管线启动失败，告知具体阻塞点（BlackHole 驱动？豆包凭据？ByteView 连接？），不要说「API 不支持」
5. 历史参考：07-17 V4 调试会 + 07-21 session_id 修复，详见 `references/realtime-voice-debug.md` + `references/http-bridge.md`

**🚨 反模式：main.py 直接调 DeepSeek**（2026-07-21 三次踩坑后总结）：
- ❌ 在 main.py 里写 `_deepseek_chat()` 函数、自己拼 prompt、自己加天气/C360 查询——这是把 main.py 做成另一个独立 AI
- ❌ 用户反馈：「不行诶，我问他天气他也不知道，我问拓竹的合作金额他也不知道」——因为独立 DeepSeek 没有 Hermes 的工具链和上下文
- ✅ **唯一正确方案**：main.py 是耳朵和嘴巴，不是大脑。所有思考通过 bridge 交给 Hermes。Hermes 有完整的工具链（C360、天气、搜索、记忆）和上下文

详见 `references/feishu-official-voice-agent.md`。

```
用户说「旁听会议」
  └─ Agent: lark-cli 查活跃会议
      └─ 启动 meeting_transcribe.py (cron 10s 一轮，采字幕到 JSONL)
          └─ 会议结束 → 读 JSONL → 生成纪要 → Step 7 待办分发
```

**脚本**: `~/.hermes/scripts/meeting_transcribe.py`
**原理**: 用 lark-cli `+meeting-events --meeting-id <id> --page-all --page-size 100 --as user` 拉取事件，过滤 `transcript_received` 类型去重写入 JSONL。
**⚠️ 脚本是单次执行的（非循环）**，需用 `while true; do python3 meeting_transcribe.py; sleep 10; done` 包装持续运行。
**⚠️ 事件类型是 `transcript_received` 不是 `subtitle`**，`--type subtitle` 返回空。
**⚠️ meeting_id 必须用 `--meeting-id <id>` 标志传入**，不能写成位置参数。
**日志位置**: `~/.hermes/cache/meeting_logs/<meeting_id>.jsonl`（与 poll.sh 的 `~/meeting_logs/` 不同目录）

**轮询 cron `272cdc68a518` 已删除**（2026-07-17）。恢复方案归档 Obsidian: `feishu-meeting-listen/polling.md`。

## 核心需求（用户 2026-07-17 最终确认）

| 需求 | 实现 |
|---|---|
| **手动激活「入会」→ 官方方案** | ✅ 立即查活跃会议 + 启动 main.py（ByteView + 豆包） |
| 客户会议推 C360（商机+最近跟进） | ✅ Agent 处理：search all + follow_up |
| 会议结束产出纪要 | ✅ Agent 读 JSONL → 飞书卡片 |
| 自动轮询 | ❌ 已删除。用户偏好手动控制 |

**架构决策**（2026-07-17）：用户明确「手动发起更好，我能判断会议需不需要你加入」。轮询 cron 已删除，恢复方案归档 Obsidian。

## 🚨 版本教训：v3→v6 回归复盘

V4/V5/V6 三次升级均为「替换式重写」而非「增量增强」：

| 错误 | 后果 |
|------|------|
| 每次升级丢弃旧版全部代码 | V3 的纪要能力在 V5/V6 消失 |
| 过早自动化（launchd/cron） | 手动流程未稳就引入新复杂度 |
| 过度工程化（双 cron + LLM 轮询） | 凭空烧 token，碎片化 |
| 改动前不读历史版本 | 不知道 poll.sh 和 SKILL.md 还在 |
| 忽视用户反馈 | 用户说回退时还在修补错误架构 |

**升级铁律**（已写入 Obsidian `hermes-skills/index.md`）：
1. 新版 = 旧版全部功能 + 新功能（只叠加不删减）
2. 升级前在 Obsidian 存档旧版完整代码 + cron 配置
3. 手动流程跑稳至少 3 次再考虑自动化
4. 用户说「回退」立刻回退，不修补
5. 改动前先读 `versions/` 中的历史快照

**🚨 用户不满信号响应规则**：当用户说出以下任意话时，**立即停止当前改动的方向**，执行「回溯→确认→恢复」而非继续新增：
- 「大失败」「非常不满意」「乱七八糟」「改的什么」
- 「自从 XX 之后就没了」「没一次成功」
- 「我觉得现在改的乱七八糟的」

**正确响应流程**：
1. 停止当前所有改动（放弃刚写的代码/cron/架构，不要再修补）
2. 问用户：「之前哪个版本是稳定/可用的？我直接回退到那个版本」
3. 找到旧版 → 恢复 → 确认核心能力清单 → 再做增量改动
4. **禁止行为**：在用户表达不满后继续新增功能、创建新 cron、拆分架构——这些都会让用户更恼火

详见 `references/v3-v6-regression-playbook.md`。

> 📦 **版本归档**：`~/Documents/Obsidian Vault/hermes-skills/feishu-meeting-listen/` — 含完整复盘、当前快照、版本历史。

## ⛔ 已废弃方案（bash poll-v5 / LLM cron / launchd）

以下方案已全部停用，仅作历史参考：
- **poll-v5.sh + launchd**：bash 轮询 5 版迭代从未稳定（超时/竞争条件/多实例）
- **LLM cron `f64f153f96ec`**（会议大脑）：每 3 分钟 LLM 轮询，已删除。token 消耗高 + 碎片化
- **LLM cron `3701642ddd64`**（纪要生成）：每 5 分钟检查，已删除。与 Agent 手动模式冲突

---
|---|---|
| **手动激活旁听** | 用户说「监听会议」→ Agent 确认 poll.sh 状态 → 接管全流程 |
| **C360 客户情报** | 仅客户会议（标题匹配「客户名 x 飞书」）：`lark-c360 search all` + `follow_up +recent --account-id`。发送一次后继续旁听。 |
| **会议纪要** | poll.sh 退出 → Agent 收到 notify → 读 JSONL → 飞书卡片纪要 |
| **会后自动执行** | Step 7：AUTO 类立刻干 / DRAFT 备好 / USER 标注 / DEP 说明 |
| **🎙️ 实时音频 ASR** | DashScope Paraformer-v2（实验性），详见 `references/dashscope-realtime-asr.md` |

## 🚨 会议总结格式铁律

**所有会议总结必须用飞书卡片输出，禁止纯文本。** 卡片格式严格遵循 `feishu-card-send` skill（`<font>` 标签 + `column_set` 布局 + `note` 底注），参照以下骨架：

```bash
# 飞书卡片 JSON 骨架（lark-cli 发送）
lark-cli im +messages-send \
  --chat-id "<chat_id>" \
  --msg-type interactive \
  --as bot \
  --content '{
    "config": {"wide_screen_mode": true},
    "header": {
      "title": {"tag": "plain_text", "content": "📹 会议标题"},
      "template": "blue"
    },
    "elements": [
      { "tag": "markdown", "content": "<font size=16 weight=bold>参会信息</font>\n..." },
      { "tag": "hr" },
      { "tag": "markdown", "content": "<font size=16 weight=bold>核心内容</font>\n..." },
      { "tag": "hr" },
      { "tag": "note", "elements": [{ "tag": "plain_text", "content": "数据来源 + 时间戳" }] }
    ]
  }'
```
🚨 **飞书卡片 `tag: markdown` 不是标准 Markdown**：`##` 用 `<font size=24>` 代替，`**bold**` 用 `<font weight=bold>` 代替，表格用纯文本或 `column_set`。详见 `feishu-card-send` skill。

**分片规则**：
- 每张卡片 `elements` 数组不超过 10 个元素（含 `hr` 分隔线）
- 逻辑分段：第一张 = 会议概览 + 核心结论，后续 = 详细内容
- 每张末尾加 `note` 标注 "卡片 N/M"
- 按顺序依次发送（`for card in card1 card2 card3`）

### 告警发送目标

告警通过飞书 IM 发送到 `ALERT_CHAT` 环境变量指定的群或用户。不包含 Agent 协作群联动（纯会议场景 + C360）。

客户名单见 `~/.hermes/data/client_list.json`（可独立更新，自动同步）。

C360 字段速查见 `references/c360-fields.md` —— 含已验证的 field name、`search all` 返回结构、已知限制（多产品线 CSM 仅 `csm_owner`、商机类型未暴露、ISV 商机不可读）。

## 告警输出原则

> **只输出用户不知道的信息。** 会议中用户已知的基础信息（行业、CSM 姓名、客户类型、付费状态）一律不输出。告警聚焦于：
> 1. 商机产品 + 阶段（用户未必记得每个客户的最新商机细节）
> 2. 最近跟进笔记摘要（用户可能忘了上次聊了什么）
>
> 关键词告警照常（预算/价格/签约等），这些是实时提醒，不涉及已知信息。

---

## 其它参考

- `references/feishu-doc-reading.md` — 飞书 Wiki/Doc 文档读取流程
- `references/minutes-search-download.md` — 🆕 妙记搜索与下载（事后查历史会议转写，`+search` / `+detail`）
- `references/listen-subtitles-version-history.md` — 🆕 listen_subtitles.py V3→V4 修复记录（会议结束误判 + 120002 不可入会检测）
- `references/cross-session-memory.md` — 🆕 跨会话双向记忆（话题↔主频道互通，session_search 拉通）
- `references/ai-opportunity-review-framework.md` — 🆕 AI 商机盘点框架（跨行业标签体系 + 对比方法论 + 一箭双雕）
- `references/feishu-official-voice-agent.md` — 🆕 飞书官方智能体入会方案（ByteView + 豆包）
- `references/feishu-event-driven-join.md` — 事件驱动入会方案（`vc.meeting.participant_meeting_joined_v1`，配合 `scripts/auto_join_on_event.py`）
- `scripts/auto_join_on_event.py` — 🆕 自动入会脚本（监听 meeting_joined → 启动 main.py）
- 🆕 **官方 Wiki：智能体入会玩法 & Demo 汇总** — https://bytedance.larkoffice.com/wiki/EkwZwmBAuiK2qxkwWqRcMtfLnre。三种玩法：玩法1(监听+文字，已全量) / 玩法2(语音应答，灰度) / 玩法3(深思考+语音，探索)。灰度群 `oc_8a93e6271847efa53ced90301647ea66`。外部客户需提交申请表单。
- `references/industry-insight-supplement.md` — 行业文档 Insight 补充框架（从会议知识反哺文档）
- `references/hook-pipeline-optimization.md` — 🆕 Hook 机制：输出脱敏 + lark-cli 截断（零 token 确定性工作剥离到框架层）
- `references/meeting-insight-extraction.md` — 🆕 从历史会议字幕系统性提取客户洞察
- `references/fish-audio-tts.md` — Fish Audio TTS 接入记录（V4 已废弃，仅供历史参考）
- `references/feishu-official-voice-agent.md` — 🆕 飞书官方智能体入会方案（ByteView WebSocket + 豆包端到端实时语音）—— 真正的 Bot 入会，会里所有人都能听到
- `references/feishu-event-driven-join.md` — 🆕 事件驱动入会方案（vc.bot.meeting_invited_v1）—— 已订阅，无需自写监听。事件由飞书平台推送，配置就够。
- `references/warm-paper-design.md` — 🆕 暖纸风格设计令（来自 Zara 的 AI-native 组织页面，Albert Sans + 思源宋体）
- `references/design-skill-selection.md` — 🆕 设计 Skill 选用铁律（禁止混用 baoyu-design + apple-design，一次只用一个）
- `references/doubao-tts-research.md` — 豆包 WebSocket 双向流式 TTS 调研（✅ 已接入，小何 2.0，Key 在 config/.env）
- `references/blackhole-routing.md` — 🆕 BlackHole 音频路由排坑（多输出设备/LarkAudioDevice/当前 workaround）
- `references/realtime-voice-debug.md` — 🆕 实时语音对话全记录（ASR→LLM→TTS 排坑 + 豆包WebSocket协议要点 + 音频路由真值表）
- `references/version-management.md` — 版本管理铁律 + 归档/回退流程
- `references/hermes-bridge.md` — 🆕 Hermes ↔ 会议文件队列桥接（inbox/outbox）。大脑只有一个。
- `references/http-bridge.md` — 🆕 Hermes ↔ 会议 HTTP push bridge（localhost:19876）。替代文件轮询，零延迟。

---

## 核心原理

Agent 以**用户身份**旁听会议，通过飞书 VC API 轮询拉取会中事件（字幕、聊天、参会人进出），分析后通过飞书 IM 发给用户。**其他参会者感知不到 Agent 的存在**。

```
用户本人在飞书会议中
    ↓
Agent 调用 GetUserActiveMeeting → 拿到 meeting_id
    ↓
Agent 调用 ListMeetingEvents 轮询拉取事件（字幕、聊天等）
    ↓
Agent 分析内容，通过飞书 IM 将结果发给用户
```

## 能力边界

- ✅ 实时获取字幕（transcript）
- ✅ 实时获取会中聊天（chat）
- ✅ 参会人进出通知
- ✅ 多会议并行旁听（无硬上限，每会一个独立 bash 进程）
- ✅ **会中收发文字消息**：接收走 `vc +meeting-events` 的 `chat_received` 事件（标准+个人会议均支持）；发送走 `lark-cli vc +meeting-message-send --as bot --msg-type text`（需 `vc:meeting.message:write` app scope，2026-07-21 已申请并验证可用）
- ⚠️ **会中发语音**：由官方入会方案（豆包端到端实时语音）提供。V4 的 Fish Audio TTS 方案已废弃。
- ⛔ **V4 实时语音对话**：已废弃并封存 Obsidian（`v4-archive-20260717.md`）。
- ✅ **字幕采集 V3**（2026-07-17 — 「旁听会议」模式）：`meeting_transcribe.py` — lark-cli `+meeting-events --meeting-id <id> --page-all --page-size 100 --as user` 轮询，过滤 `transcript_received` 事件 → JSONL 持久化。**⚠️ 单次执行，需 `while true` 循环包装；`--type subtitle` 无效（正确类型是 `transcript_received`）**。静默模式，零 TTS，用于会后续要 + Agent 待办分发。
- ✅ **会中语音输出方法**（2026-07-17 验证通过）：飞书会议扬声器选**会议旁听**（非 BlackHole）、麦克风选**BlackHole 2ch**。TTS 通过 `afplay` 播到会议旁听 → 自动路由到 BlackHole → 飞书麦克风通道捕获。**关键发现**：直接往 BlackHole 输出不工作（PyAudio 写入成功但飞书无电平），必须走多输出设备的间接路由。
- ⚠️ **话筒路由冲突**：MacBook 麦克风持续往 BlackHole 写数据（让飞书收人声）会阻塞 TTS 音频混入。**修复**：`speak()` 播放 TTS 前暂停 `bh_stream`，播完恢复。详见 `references/blackhole-routing.md`。
- 🚨 **V4 去重跨会话**（已在 Obsidian 封存文档记录，不再维护）
- ❌ 实时推送（需轮询拉取，无 webhook）
- 🔄 双向语音打断/全双工（架构已明确：Paraformer ASR + TTS + BlackHole 音频路由。会议音频注入非 VC API 能力，而是系统音频路由问题。）

### 成本效率

v3 脚本的核心设计：**轮询归轮询，分析归分析，互不污染**。

- 后台轮询脚本是独立 bash 进程，**零 token 消耗**
- 仅在提取字幕 + 生成总结时才消费 LLM
- 实测：两场 1 小时会议 ≈ 34K tokens ≈ **¥0.09**（DeepSeek V4 Pro 定价）
- 每小时会议成本 ≈ ¥0.05，远低于飞书妙记企业版 ¥75/人/月

### 适合场景

会议纪要、议程追踪、实时问答助手、背后支援型 Agent

### 后台守护（meeting_detect.py）

`meeting_detect.py` 通过 Hermes cron（`272cdc68a518`，`every 1m`，`no_agent=true`，`deliver=local`）静默运行。**零 token、零推送**。

```bash
# 验证状态文件
cat ~/.hermes/cron/meeting_state.json | python3 -m json.tool
# 检查字幕日志
ls -la ~/meeting_logs/
```

工作流：
```
meeting_detect.py (cron, every 1min, no_agent, deliver=local)
  ├─ lark-cli vc +meeting-list-active → 获取活跃会议
  ├─ 新会议 → subprocess.Popen(poll.sh) 后台监听
  │   └─ poll.sh → 每 10s 轮询 meeting-events → ~/meeting_logs/<id>.jsonl
  ├─ 客户识别（标题匹配 client patterns）
  ├─ PID 追踪 → 检测退出 → 标记 completed
  └─ 状态持久化 → meeting_state.json
```

状态字段：`new` → `monitoring` → `completed`。`client` 字段标记是否为客户会议。

### 会议类型识别 → 分析框架匹配

根据会议标题和内容，自动匹配对应的分析框架：

| 会议类型 | 标题特征 | 使用框架 | 输出重点 |
|---------|---------|---------|---------|
| **客户交接** | 「交接」「新客转老客」 | `client-handover-checklist` skill | 七维度 + 三盲区，结构化表格 |
| **客户交流** | 「x飞书」「交流」「沟通」 | JTBD / BANT / Kano / Mom Test | 客户需求矩阵 + 产品匹配度 + 销售建议 |
| **安全/产品演示** | 「安全」「功能介绍」「方案」 | 功能逐条对应 + 能力边界标注 | 已支持 vs 不支持 vs 需升级，报价路径 |
| **内部对齐** | 「目标对齐」「指标」「专项」「讨论」 | 决策点提取 + 行动项 | 拍定了什么、没拍定什么、你的待办 |
| **围炉夜话/分享** | 「围炉」「分享」「研修」 | 知识提取 | 核心观点 + 启发点，不需要行动项 |
| **测试/实验** | 标题为「袁鑫杰的视频会议」或「xxx的视频会议」且内容为 Agent 功能测试 | 轻量卡片 | 测试目标 + 验证结果 + 发现的问题，不套分析框架 |
| **商机盘点** | 「商机盘点」「AI 盘点」 | `references/ai-opportunity-review-framework.md` | 跨行业商机全景 + 标签分层 + 后续动作 |

**使用原则**：先看标题判断类型，再套框架。不要让框架驱动内容——让数据选出最合适的框架。

**测试/实验会议**的特殊处理：
- 字幕 < 20 条且无客户关键词 → 判断为测试会议，用迷你卡片（仅 header + 1-2 个 elements + note）
- 不需要 Step 6（材料获取）和 Step 5.5（Grilling）
- 不需要 C360 客户查询

---

## 前提条件（一次性准备）

### ① 灰度资格

进入早鸟体验群获取灰度资格。

### ② 飞书应用 & 权限

1. 在飞书开放平台创建企业自建应用，获取 App ID / App Secret
2. 申请权限：`vc:meeting.meetingevent:read`（用户身份权限）
3. 数据权限范围选「按条件筛选」→ 会议的归属者 → 包含 → 与应用可用范围一致
4. 权限变更后重新发布应用

### ③ 客户端版本 & CLI 工具

- 飞书客户端 ≥ 7.68（飞书 → 头像 → 关于飞书 → 检查更新）
- lark-cli ≥ v1.0.55：`npm install -g @larksuite/cli@latest`
- **lark-c360**（C360 商机查询）：
  ```bash
  npm install -g https://lf-ldic360.feishucdn.com/obj/ldi-c360/cli/lark-c360/latest/customer360-lark-c360.tgz
  lark-c360 install-skills --force
  lark-c360 env use online
  lark-c360 auth login --no-wait --json   # 打开返回的 authorize_url 授权
  lark-c360 auth login --resume           # 授权后执行
  ```

> 也可运行 `bash scripts/setup.sh` 一键检查并安装上述工具。

### ④ 会议侧设置

每场会议的 owner 在会议安全设置里开启「**允许智能体入会**」。
（找不到该选项，先开 AI 总结。只有在灰度范围内才能打开。）

---

## 用户授权（首次使用）

Agent 独立使用时需要用户先授权 `vc:meeting.meetingevent:read` 权限。

### 第一阶段：生成授权链接

```bash
lark-cli auth login --scope "vc:meeting.meetingevent:read" --no-wait --json
```

从输出提取 `verification_url` 和 `device_code`，把 `verification_url` 发给用户点击完成授权。

### 第二阶段：用户授权后获取 token

```bash
lark-cli auth login --device-code <device_code_from_step1>
```

---

## 核心命令

**🚨 飞书文档读取铁律**（2026-07-22）：会议中用户分享飞书文档/Wiki 链接 → **必须用 lark-cli，禁止 browser**。
```bash
# 读文档：docs +fetch
lark-cli docs +fetch --doc <url或token> --doc-format markdown

# 读 Wiki：先取 obj_token 再 fetch
lark-cli wiki +node-get --node-token <url> --jq '.data.obj_token'
lark-cli docs +fetch --doc <obj_token> --doc-format markdown
```
lark-cli 覆盖 23 个域（docs/wiki/calendar/im/vc/base/task/mail/sheets/slides/markdown/mindnotes/minutes/okr/whiteboard/drive/contact/event/apps/approval/attendance）。browser 只用于外部网页。

### 查询用户当前所在会议

```bash
lark-cli vc +meeting-list-active --as user
```

**返回**：会议列表，每项含：
- `meeting_id` — 长会议 ID（用于拉事件，**不是 9 位会议号**）
- `meeting_no` — 9 位会议号（给用户看的）
- `meeting_title` — 会议标题

如果用户在多个会议中，列出所有会议让用户选择。

### 拉取会中事件（字幕、聊天等）

```bash
lark-cli vc +meeting-events --as user --meeting-id <meeting_id> --page-all --page-size 100
```

### 🆕 在会中发消息（2026-07-17）

**权限**：`vc:meeting.message:write`。首次使用需授权：
```bash
lark-cli auth login --scope "vc:meeting.message:write" --no-wait --json
# 生成 QR 码 → 用户扫码 → 执行：
lark-cli auth login --device-code <device_code>
```

**发文字消息**（bot 身份——需要在飞书开放平台控制台申请 app scope `vc:meeting.message:write`，然后 `--as bot` 即可用）：
```bash
lark-cli vc +meeting-message-send --meeting-id <meeting_id> --msg-type text --text "消息内容" --as bot
```
权限申请链接：`https://open.feishu.cn/page/scope-apply?clientID=cli_a964fd626078dcbc&scopes=vc%3Ameeting.message%3Awrite`
（仅 `--as user` 也立即可用，但回复者显示为用户本人而非 bot）

**发语音**（系统音频路由）：TTS 生成音频 → `afplay` 播放 → BlackHole → 会议麦克风。详见 `references/in-meeting-voice.md`。

**参数说明**：

| 参数 | 说明 |
|------|------|
| `--meeting-id` | 长会议 ID（来自 GetUserActiveMeeting，非 9 位会议号） |
| `--page-all` | 自动翻页获取所有事件 |
| `--page-size` | 单页条数（20-100） |
| `--start` / `--end` | 时间范围（ISO 8601 / YYYY-MM-DD / Unix 秒），可选 |

### 脚本架构（v3，已验证稳定）

**v1** 直接 `--page-all` → 日志爆炸（每 10 秒全量追加重复数据）。
**v2** 引入 `page_token` 增量拉取 → token 约 40 分钟过期后死循环丢数据。
**v3** 彻底砍掉 `page_token`，永远用 `--page-all` 全量拉，靠 Python 从日志文件读取已有 `sentence_id` 做内存 `set()` 去重，只追加真正新的事件。

核心优势：
- 无 token 过期风险——page_token 这个不稳定因素从架构上消除了
- Python `set()` 去重——不依赖 bash 变量拼接，大会议（1600+ 句）也可靠
- 独立 bash 进程——**轮询零 token 消耗**，不进 LLM 上下文
- 成本实测：两场 1 小时会议 ≈ 34K tokens ≈ ¥0.09（仅提取字幕 + 生成总结时消费 LLM）

**多会议支持**：无硬上限。每个会议一个独立 `bash poll.sh` 进程，10 秒一次 API 调用的开销可忽略。实际瓶颈是用户能同时挂几个飞书会议（常态两场，偶尔三场）。

---

## 事件数据结构

按 `activity_event_type` 区分事件类型。

### 字幕 `transcript_received_items`

```json
{
  "speaker": { "id": "xxx", "user_type": 1, "user_name": "张三" },
  "text": "今天来讨论一下这个方案",
  "language": "zh-CN",
  "start_time_ms": "1716699012000",
  "end_time_ms": "1716699014000",
  "sentence_id": "100001"
}
```

- `user_type` 可能为声纹检测类型（100/101/102），需兼容处理
- 同一句话可能多次推送（修正/补全），用 `sentence_id` 去重

### 聊天消息 `chat_received_items`

```json
{
  "operator": { "id": "xxx", "user_name": "张三" },
  "message_id": "om_xxx",
  "message_type": 1,
  "content": "大家好",
  "send_time": "1716699030000"
}
```

`message_type`：1=文本，2=系统，3=表情，4=加密

### 参会人进入 `participant_joined_items`

```json
{
  "participant": { "id": "xxx", "user_type": 1, "user_role": 1, "user_name": "张三" },
  "join_time": "1716699010000"
}
```

### 参会人离开 `participant_left_items`

```json
{
  "participant": { "id": "xxx", "user_name": "张三" },
  "leave_reason": 1,
  "leave_time": "1716700000000"
}
```

`leave_reason`：1=主动离会，2=会议结束，3=被踢出

---

## 实战工作流

### Step 1: 检查用户在会

```bash
lark-cli vc +meeting-list-active --as user
```

如果返回空 → 告知用户「你当前不在任何会议中」。如果在多个会议中 → 列出让用户选。

### Step 2: 第一次拉事件（获取当前状态）

```bash
lark-cli vc +meeting-events --as user --meeting-id <meeting_id> --page-all --page-size 100 --format json
```

解析返回的 events，按类型分类：
- 字幕 → 按 speaker 和 sentence_id 聚合为对话流
- 聊天 → 按时间排序展示
- 进出 → 统计当前参会人列表

### Step 3: 处理并交付分析

将字幕流构建为可读的对话/摘要，通过飞书 IM 发给用户。首次交付包含：
- 会议基本信息（标题、当前参会人）
- 已有对话摘要
- 会中聊天记录

### Step 4: 启动后台轮询（持久化脚本）

使用 skill 内置的 `scripts/poll.sh`，自动将字幕写入 `~/meeting_logs/<meeting_id>.jsonl`。

```bash
# ⚠️ 必须用 bash 前缀运行（首次部署需 chmod +x，避免 Permission denied）
chmod +x ~/.hermes/skills/feishu/feishu-meeting-listen/scripts/poll.sh
bash ~/.hermes/skills/feishu/feishu-meeting-listen/scripts/poll.sh <meeting_id> <meeting_title> &
```

**脚本特性（v3）：**
- **全量拉取 + 内存去重**：永远用 `--page-all`，Python 从日志文件读已有 `sentence_id` 做 `set()` 去重，不依赖 page_token
- 每 10 秒拉一次字幕/聊天/进出事件，去重后追加写入 JSONL
- 检测到「user is not in the meeting」自动退出
- 所有路径使用绝对路径，不依赖 session 上下文
- 输出位置：`~/meeting_logs/<meeting_id>.jsonl`

**JSONL 格式（每行一条）：**
```json
{"type": "transcript", "speaker": "蔡璐", "text": "今天主要是交接", "sentence_id": "100001", "time": "1716699012000"}
{"type": "chat", "speaker": "张三", "text": "收到", "message_id": "om_xxx"}
{"type": "join", "speaker": "李四", "text": "入会", "time": "1716699010000"}
{"type": "leave", "speaker": "李四", "text": "主动离会", "time": "1716700000000"}
{"type": "meta", "event": "meeting_ended", "time": "14:32:05"}
```

**启动后告知用户：** 通知用户脚本已启动 + 日志路径。

**🚨 同时启动聊天回复监控**：poll.sh 启动后，必须同时启动 `meeting_chat_reply.py`：

```bash
# 两个脚本并行运行
# 1. poll.sh — 字幕采集（已有）
bash ~/.hermes/skills/feishu/feishu-meeting-listen/scripts/poll.sh <meeting_id> <meeting_title>

# 2. meeting_chat_reply.py — 聊天 @浪子 监控（新增）
python3 ~/.hermes/skills/feishu/feishu-meeting-listen/scripts/meeting_chat_reply.py <meeting_id>
```

**chat_reply.py 功能（V2 — LLM 即时回复）**：
- 每 3 秒增量读取 JSONL，检测新聊天消息
- 发现含"浪子"的消息 → **DeepSeek API 即时生成内容相关回复**（~1-3 秒延迟）
- API 超时/失败 → **自动 fallback 模板回复**：`收到 @{speaker}，浪子正在处理中 🙋`
- 基于 message_id 去重，不会重复回复
- API Key 从 `~/.hermes/.env` 的 `DEEPSEEK_API_KEY` 读取
- 成本：每次 ~200 tokens ≈ ¥0.0004，一场会议 50 条 @浪子 ≈ ¥0.02

**回复示例**：
```
聊天框: 浪子，帮我总结一下刚才说的重点
→ 回复: @张三 刚才主要讨论了三个点：1. Q3 目标调整... 2. 新功能排期...
```

**Agent 不再需要二次处理 chat_queue**：LLM 即时回复后消息已处理完毕，无需 Agent 再走详回流程。

**🚨 铁律：启动 poll.sh 后绝不可放任不管。这是用户最恼火的模式。**

1. `terminal(background=true, notify_on_complete=true)` 启动，返回的 `session_id` 必须保存
2. 收到 `notify_on_complete` 通知后，**立刻走 Step 4.5 → Step 5 → Step 7**，不得延迟
3. **做其他任务时也不能忘记会议旁听进程**——跟 TRAE 交互、读文章、查资料时，如果 notify 到了，必须立刻切换回来处理会议纪要
4. 如果用户说「会议结束了你没监听到」，立刻检查 `~/meeting_logs/` 中最新修改的 JSONL，看是否有漏掉的会议内容可以补救

**❌ 已发生事故**：
- 7.10 高驰×分贝通 + 7.11 卿志聊 AI：脚本退出后 Agent 未主动检测
- **7.14 南区RM周会后第二场会议**：Agent 在跟 TRAE 交互/读文章时收到 notify 但未及时处理，导致漏听。此后加入铁律——notify 到达时，**无论正在做什么，立刻切换处理会议纪要**
- **7.17 连锁入会**（4 场测试会议 3 小时内）：会议 A 刚结束，Agent 还在写纪要卡片时，会议 B 的邀请已到。Agent 被中断 → 卡片未发 → 造成漏纪要。**解决方案**：新邀请到达时，优先入会 + 启动 poll.sh，然后**立刻补发上一场未完成的纪要**。不能因为新会议就跳过上一场的总结

**终止条件**（脚本自动处理）：
- 用户离会（`user is not in the meeting`）→ 自动退出
- 会议结束（`leave_reason=2`）→ 自动退出

### 🚨 收到会议邀请时的处理流程

飞书系统可能对同一会议重复发送邀请（实测每场测试会议至少触发 2 次邀请）。收到邀请时：

```
收到会议邀请（含 meeting_no）
  ├─ 检查是否有活跃的 poll.sh 进程
  │   ├─ 有活跃进程 → process(action='poll') 验证存活
  │   │   ├─ 进程存活且 meeting_no 匹配 → 告知用户「已在会中」，不重启
  │   │   └─ 进程已退出 → 走「新会议」分支
  │   └─ 无活跃进程 → 新会议
  │       ├─ lark-cli +meeting-list-active → 获取 meeting_id
  │       ├─ 启动 poll.sh（background=true, notify_on_complete=true）
  │       └─ 告知用户入会状态
  ```

  **关键原则**：
  - **不重复启动**：同 meeting_no 已有进程在跑就不要再起新进程

### Step 4.5: 检测脚本退出 → 恢复字幕

```bash
# 从日志文件读取全部字幕
cat ~/meeting_logs/<meeting_id>.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line.strip())
    t = d.get('type','')
    if t == 'transcript':
        print(f'[{d[\"speaker\"]}]: {d[\"text\"]}')
    elif t == 'chat':
        print(f'[聊天-{d[\"speaker\"]}]: {d[\"text\"]}')
    elif t in ('join','leave'):
        print(f'[{d[\"speaker\"]} {d[\"text\"]}]')
"
```

### Step 5: 会议结束后输出纪要

当检测到用户离会或会议结束，生成完整会议纪要。

**输出步骤**：
1. Python 提取唯一字幕（sentence_id 去重）
2. 根据会议标题判断类型（交接/交流/演示/对齐/分享）
3. 套用对应分析框架（见上方「会议类型识别 → 分析框架匹配」表）
4. 输出结构化纪要 + 用户待办

**分析框架速查**：

| 框架 | 适用场景 | 分析维度 |
|------|---------|---------|
| **七维度交接** | 客户交接会 | 金额/决策人/签约原因/决策过程/商机/风险/线下交接 + 服务断点/前任潜规则/组织变动三盲区 |
| **JTBD** | 客户交流 | 功能性/情感性/社会性三层需求 |
| **BANT** | 客户交流 | 预算/决策权/需求/时间线 → 成交优先级 |
| **Kano** | 产品演示后 | 基本型/期望型/兴奋型/反向需求 → 产品匹配度 |
| **Mom Test** | 客户交流 | 真痛点 vs 客套话 → 高/低信号标注 |
| **决策点提取** | 内部对齐 | 拍定了什么 + 没拍定什么 + 你的待办 |

**原则**：数据优先，框架适配在后。不要让框架驱动内容。

### Step 5.5: 需求 Grilling（自动触发）

当会议中出现模糊的客户需求（如"想做 AI 会议管理"、"想用 AI 提效"）时，不要直接输出一个含糊的总结。**自动启动 Grill 模式**：

**三个铁规则**：
1. **一次只问一个开放式问题** — 不用 clarify 的多选，让用户自由回答
2. **只问 Decisions，Facts 自己查** — 客户规模、行业、已用产品这些我通过 C360/公开信息/会议上下文自己补，不问
3. **问完等确认再动手** — 用户说"可以了"或需求边界清晰之后，再生成 spec / 录入多维表格

**Grill 方向**（根据需求类型自动选择切入角度）：
- 使用场景 → 谁用？触发条件是什么？输入输出是什么？
- 技术边界 → 必须用飞书原生？能接外部 API 吗？
- 规模 → 多少人用？每天多少次？峰值多少？
- 约束 → 预算上限？时间要求？合规/安全要求？
- 已有底座 → 客户现在用什么？哪些不能动？

**停止条件**：用户说「可以了」「差不多了」「先这样」或连续两轮追问已达到足够的边界清晰度。

### Step 6: 会后跟进（材料获取 + 情报补齐）

**6a. 材料获取**：会议中用户提到需要材料（ISV 产品、飞书案例、版本对比等）→ 会后去 Agent 协作群 @对应 Bot 获取。

**详见 `agent-group-collab` skill**——覆盖 Aime（业绩查询）、ISV 助手（产品材料）、样板间小管家（案例弹药库）、马斯克（客户名单）的完整交互流程 + 材料筛选规则（禁止搬运工，必须精选 1-3 条最匹配的交付）。

**6b. 客户交接情报补齐**：如果会议标题/内容含「交接」「新客转老客」「handover」关键词 → **自动触发 `post-handover-intelligence` skill**：

```
poll.sh 退出检测到会议类型=客户交接
    ↓
自动调用 post-handover-intelligence 五阶段流水线：
  Phase 1：从会议字幕提取客户名、KDM、待办
  Phase 2：C360 CLI 查帐号/订单/跟进记录
  Phase 3：公开搜索竞品对比、行业动态
  Phase 4：交叉验证 C360 vs 公开信息 vs 已有笔记
  Phase 5：飞书卡片交付 + Obsidian 客户笔记更新
```

**这个链路全自动。poll.sh 退出 = 触发。不需要用户说任何话。**

### Step 7: 会后待办自动执行（Universal Post-Meeting Action Executor）🚨

> **核心理念**：会议产生的待办，不是「用户看完了自己去干」——是我先分类，能干的立刻干，干完汇报。

**触发时机**：Step 5 会议总结产出后，立刻对总结中的「下一步」/「待办」表逐条执行。

#### 7a. 分类框架

对每条待办，四分类：

| 分类 | 含义 | 执行策略 |
|------|------|---------|
| **AUTO** | 我能用现有工具独立完成 | **立刻执行，不等待，不询问** |
| **DRAFT** | 我能准备内容，但发送/提交需用户确认 | 草拟好，标注「确认后发送」 |
| **USER** | 只能用户操作 | 清晰标注，不给假方案 |
| **DEP** | 缺少前置条件（API 权限、系统访问等） | 标注缺失什么 + 怎么补齐 |

#### 7b. AUTO 类判断标准

以下是我能独立完成的（非穷举，原则判断）：

- ✅ **发送文件/材料**：把本地文件通过飞书发给用户（用户自己转发）
- ✅ **@Agent 协作群 bot**：@ISV助手/@样板间小管家/@马斯克/@Aime 获取信息
- ✅ **信息搜索**：公开搜索、C360 查客户、飞书文档搜索
- ✅ **创建文档**：飞书文档、飞书卡片、飞书多维表格
- ✅ **写代码/脚本**：试跑 demo、写 MCP 集成脚本
- ✅ **读写本地文件**：笔记、配置、数据文件
- ✅ **查询 API**：lark-cli、feishu-cli、C360 CLI
- ✅ **启动后台任务**：cronjob、轮询脚本

#### 7c. 执行原则

1. **AUTO 不等待不询问**：能做的直接做完，汇报「已完成：X」
2. **DRAFT 备好待确认**：内容写好，用户一句话「发」即发
3. **诚实说做不到**：USER/DEP 类不说「我帮你」，而是说「这需要你 + 为什么」
4. **先做再说**：不要先问「要不要做」，先做完再汇报
5. **并行优先**：多条 AUTO 类待办同时推进

#### 7d. 交付格式

会后统一汇报：

```
🤖 已自动完成（N 项）：
✅ 已把 XX 材料发给你
✅ 已 @样板间小管家 获取消费电子案例
✅ 已查 C360：客户 9 月到期，商机阶段：方案沟通

📝 已备好待确认（M 项）：
📋 ISV 整改反馈草稿 → 确认后发
📋 客户方案大纲 → 确认后展开

👤 需要你操作（K 项）：
⚠️ 约感臻老板会议 — 需要你来定时间
⚠️ 找 ISV 负责人面谈 — 需要你当面沟通
```

**这是 Step 5（会议总结）的自然延伸。总结产出后不要停——立刻走 Step 7 把能干的都干了。**

#### 7e. AI 需求特殊分派路径 🆕

会议中如果识别到 AI 场景需求（关键词：AI、智能体、自动化、多维表格、妙搭、Aily、Agent），除标准四分类外，额外输出一条结构化 AI 需求记录。

**信号 vs 噪音过滤**：
- ✅ **信号**：客户明确提出需求（「我们想搞个…」「能不能用 AI 做…」）、已落地的具体场景（「用妙搭搭了 XX」）
- ❌ **噪音，不提取**：标准产品介绍（只说「飞书有这个功能」但不涉及客户需求）、客户只说「在用飞书」但无具体产出、买了包但没用起来
- 如果一场会议**全是噪音**，不强行提取 AI 需求。宁可空着别凑数。

**输出格式**（8 字段）：

> 🚨 **「已用 AI」质量铁律**：「买了 AI 包」「开了 AI 功能」不算落地场景。必须是客户用某个工具**搭了具体的东西**——能说出「用什么工具 + 做了什么」的才算。
> ✅ 正确：「用妙搭搭了读书打卡小程序」「用 Claude Code 写了个自动化脚本」
> ❌ 错误：「买了 3 个 AI 基础版」「开了知识问答功能」
> 判断标准：如果描述只能落到「买了/开了」而没有具体产出物，就不是已实现的 AI 场景，不应列在「已用 AI」中。

| 字段 | 说明 | 提取来源 |
|------|------|---------|
| 公司 | 客户公司名 | 会议标题 / 参会人身份 |
| 部门 | 哪个部门 | 会议中提到 |
| 提出人 | 具体谁 | 会议中提到 |
| 需求简述 | 一句话痛点 | 客户原话提炼 |
| 场景描述 | 使用上下文完整链路 | 会议对话流还原 |
| 实现路径 | Hermes 推理的技术方案 | 基于飞书能力矩阵匹配 |
| **已用 AI** | 🆕 客户当前的 AI 工具/路径 | 「我们在用…」「目前是…」等句式 |
| 匹配材料 | 参考案例/方案 | 样板间/ISV 查询结果 |

**分派规则**：

```
AI 需求识别
  ├─ 含 ISV/产品/方案/分贝通等 → @ISV助手 拿材料
  ├─ 含案例/行业/参考 → @样板间小管家 拿案例
  └─ 纯 AI 场景需求 → 结构化输出给用户 → 用户转交多维表格智能体落盘
```

当前 A2A 不可用，第三条路径是 **Hermes → 用户 → 智能体** 的人肉桥接模式。等 A2A 就绪后改为直连。

详见 `references/post-meeting-dispatch.md`。

---

## 排查清单

| 问题 | 原因 | 解决 |
|------|------|------|
| 拉事件报 120003 (无权限) | 用户不在会 | 确认用户在会中 |
| 拉事件报 120002 (开关未开) | 会议 owner 未开启「允许智能体入会」 | 让 owner 在会议安全设置中开启（不同于 120003，这是专门的开关校验） |
| meeting_id 用错 | 用了 9 位会议号 | 用 `+meeting-list-active` 查到的长 ID |
| 拿不到实时字幕 | 会议未开启字幕/转写功能 | 确认会议开启了字幕 |
| lark-cli 报 401 | 授权过期或 scope 不全 | 重新执行 `lark-cli auth login --scope "vc:meeting.meetingevent:read"` |
| `--as user` 报错 | 未完成用户授权 | 先执行授权流程（两个阶段） |
| 后台脚本 Permission denied | poll.sh 无执行权限 | chmod +x 并用 bash poll.sh 启动 |
| 🚨 **meeting_transcribe.py 采集 0 条**（2026-07-17） | ① `--meeting-id` 写成了位置参数 ② 缺 `--as user` ③ `--type subtitle` 无效（正确类型是 `transcript_received`） | 命令必须是 `+meeting-events --meeting-id <id> --page-all --page-size 100 --as user`。脚本已修复。 |
| 日志膨胀 / page_token 过期 | v1/v2 历史问题 | v3 已修复：砍掉 page_token，永远 --page-all + Python set() 去重 |
| 后台脚本被 kill，字幕丢失 | 进程无持久化 | v3 每轮追加写入 `~/meeting_logs/<id>.jsonl`；会后从此文件恢复 |
| 🚨 **脚本退出后没推送纪要** | Agent 启动脚本后放任不管，未主动检测进程状态。已发生多次：7.10 高驰×分贝通 + 7.11 卿志聊 AI + 7.14 南区RM周会 | 启动时记录 session_id，每 2-3 分钟 `process(action='poll')` 检查；status=`exited` 立刻走 Step 4.5→5→7。**铁律：notify 到达时，无论正在做什么，立刻切换处理会议纪要** |
| 🚨 **v5→v6 迁移丢失纪要能力**（2026-07-16） | v5 `meeting_detect.py` 只做 C360 推送，**完全没有启动 poll.sh 入会监听和产出纪要**。用户：「自从脚本更新到 V5 之后，好像都没有产出会议纪要了。」 | V3 已恢复：Agent 手动激活模式。`meeting_detect.py` 负责静默检测+启动 poll.sh，Agent 负责 C360+纪要+会后执行。**教训：任何迁移必须保留核心能力清单对照，缺一不可。** |
| 🚨 **v6 双轨 cron 过度工程化**（2026-07-16） | v6 拆成 2 个 cron + LLM 每 3 分钟轮询，凭空烧 token。用户：「我觉得用 Chrome 它的大模型消耗太多了。」 | 已删除 `f64f153f96ec`（会议大脑）和 `3701642ddd64`（纪要生成）。仅保留 `272cdc68a518`（零 token 检测）。回归 V3 手动激活。 |
| 🚨 **Agent 反问用户「帮我回忆」**（2026-07-17） | Agent 在需要回忆历史会议内容时，对用户说「你帮我回忆一下」「我不记得了」。用户：「我不要帮你回忆，这个不是我的工作。回忆本身是应该你要去做的，不要去问我。」 | **铁律：绝对不要让用户替你回忆任何事情。** 会议日志、客户信息、历史对话——全部自己去 `meeting_logs/`、`session_search`、C360 CLI 查。找不到就诚实说「我翻遍了但没找到」，不要反问用户。 |
| 🚨 **V4 相关所有 Bug**（2026-07-17） | V4 全套已废弃封存 Obsidian。含：去重跨会话、Paraformer sentence_end 遗漏、TTS asyncio 阻塞、豆包 Key 过期、stdout 污染等。 | 不再维护。详见 Obsidian `v4-archive-20260717.md`。 |
| 🚨 **.env 尾部注释污染 speaker 值**（2026-07-17） |
| 🚨 **豆包 TTS 信息错乱：前后结论矛盾**（2026-07-17） | Agent 在话题里用新版 API Key（`c3c35e49`）测试通过，回到主流程后用旧版凭据（AppId+AccessKey）复测，得出「豆包不通」的错误结论，切到 Fish Audio。用户：「为什么前面说通后面说不通？非常非常严重！」 | **根因**：凭据散落、复测时未复用原凭据。**杜绝**：① 凭据统一到 `config/.env` ② 验证结论写 Obsidian 快照 ③ 复测前 `read_file` 上次成功脚本确认凭据一致。铁律：下结论前先查「上次成功用的哪份」。 |
| 🚨 **.env 尾部注释污染 speaker 值**（2026-07-17） | `DOUBAO_TTS_SPEAKER=zh_female_xiaohe_uranus_bigtts  # 小何 2.0` → parser 读成 `"zh_female_xiaohe_uranus_bigtts  # 小何 2.0"` → 豆包 TTS 静默失败。手工 TTS 测试正常、脚本内失败——极难排查。 | `.env` 所有值的末尾**禁止行内 `# 注释`**。排查：`print()` `.env` 加载后值。**和 asyncio 子进程问题叠加时更难排查——先验 `.env` 值。** |
\n
\n| 🚨 **旁听脚本误判会议结束**（2026-07-22，已修复） | `listen_subtitles.py` 用连续 APII 空返回 > 4 轮判结束。API 超时/会议静默 → 假阳性。CodeM 培训 + CEO 对话均被误杀。 | 改为 `meeting_still_active()` 验证：空返回后先调 `+meeting-list-active` 确认会议是否真不在活跃列表。修复版已上线，验证通过（CEO 会议期间 4 次静默均未误杀）。教训：**API 空返回 ≠ 会议结束。必须交叉验证。** |
| 🚨 **旁听脚本 crash 丢字幕**（2026-07-22，已修复） | 会议结束 lark-cli 返回空 JSON → `JSONDecodeError` → 异常未捕获，字幕全程丢失。 | `get_events()` 加 try/except JSONDecodeError → 返回 []；`main` loop 外层加 broad except + `save_progress()` 兜底；每轮新字幕后增量写盘。 |
| 🚨 **旁听脚本 0 字幕 + 空转 376 轮**（2026-07-22，已修复） | 会议「允许智能体加入会议」开关关闭 → lark-cli 返回错误码 120002 → 旧版当空事件处理 → 持续空转。大湾区 Power Hour 实测 0 字幕。 | `get_events()` 检测 `ok: false` + code 120002 → 返回 error 元组 → 主循环立即 `print("[无法旁听] 智能体不可入会")` 并退出。详见 `references/listen-subtitles-version-history.md`。 |
| 🚨 **旁听脚本 crash 丢字幕**（2026-07-22，已修复） | 会议结束 lark-cli 返回空 JSON → `JSONDecodeError` → 异常未捕获，字幕全程丢失。 | `get_events()` 加 try/except JSONDecodeError → 返回 []；`main` loop 外层加 broad except + `save_progress()` 兜底；每轮新字幕后增量写盘。 |\n| 🚨 **Bot join/leave 循环**（2026-07-17/19/21 多会中观测） | Mark 42-浪子在会议中反复「入会→ 主动离会→ 入会…」循环。观测于会议 174219494、551743790、271641162 等多场。日志充斥 join/leave 事件，污染 JSONL。用户吐槽「他挂了，没有礼貌」「又加入一个，什么意思？」。 | 可能根因：豆包 WebSocket 断连重连逻辑、或 auto_join 多实例竞争。排查方向：检查 main.py 的 reconnect 逻辑是否每次重连都触发新的 `+meeting-join` 调用。|
| 🚨 **官方入会 Bot 说话没人听到**（2026-07-17） | `main.py` 中 `say_text()` 开场白在 forward tasks 启动前调用 → TTS 音频回来时没人监听 Doubao WebSocket → 丢失。 | **把 `say_text()` 移到 `asyncio.create_task` 之后**，加 `await asyncio.sleep(0.2)` 确保 forward 任务已开始监听。详见 `references/feishu-official-voice-agent.md`。 |
| 🚨 **官方入会豆包协议版本 V3 被拒**（2026-07-17） | `protocols.py` `Message.version` 用 `VersionBits.Version3` → 服务端返回 `unsupported protocol version 3`。 | 必须用 `VersionBits.Version1`。修改 `protocols.py` line 178。 |
| 🚨 **官方入会豆包 App Key 不匹配**（2026-07-17） | `config.yaml` 中 `doubao_app_key` 与服务端注册不一致 → `invalid X-Api-App-Key: ..., expected:[...]` | 服务端错误消息直接给出 `expected:[...]` 的正确值。更新 `config.yaml` 后重试。 |
| 🚨 **豆包收到音频但不回 ASR/TTS**（2026-07-21） | `send_audio` 的 `Message` 使用 `flag=NoSeq` 不含 `session_id` → 豆包收到音频但无法关联会话，静默丢弃 | 改 `flag=WithEvent`、加 `event=TaskRequest`、`session_id=self.session_id`。务必先加 raw msg 日志验证 ByteView 侧音频流速——不要只看 fwd 日志。 |\n\n| 🫧 **豆包语音卡顿**（2026-07-23 修复） | 用户反馈句子中间卡顿。排查路径：① 试改 sleep 采样率 48k→16k → 卡顿加剧（3 倍慢） ② 试改分片 4800→19200 → ByteView 静默丢弃，完全无声 ③ 试去掉 sleep 只分片 → ByteView 整帧丢弃，无声 ④ **正确修复**：保留 4800 分片 + **去掉 asyncio.sleep** → 分片快速连续发出，WebSocket 自管流控。修复后用户确认「顺畅很多」。豆包 TTS 参数：24kHz s16le mono。⚠️ **不要改采样率（48000 是正确值）和分片大小（4800 是 ByteView 协议上限）**。 | ✅ **已修复**。`voice_agent/byteview.py` `send_audio()` 保留 `split_pcm_s16le(audio)` 分片 + `await self.ws.send(frame)`，无 sleep。 |
| 🚨 **ByteView raw msg 日志引入**（2026-07-21 调试技术） | `fwd` 日志每 50 条才打印一次，会议前半段看不到任何音频流输出，误判为「无音」 | 在 `byteview.py` `receive_audio` 开头加 `log("bv", "raw msg", idx=msg_idx, raw_len=len(message))`。这是通用调试模式——任何时候怀疑 WebSocket 没数据，先加 raw 消息日志。 |

---

## 会议会前准备

当用户告知要去见某个客户或参加某场会议时，自动触发会前简报流程。详见 `references/meeting-pre-briefing.md`。

**三步流程**：
1. **C360 客户情报** — `search all` → 商机+ARR+阶段 → `follow_up +recent` → `contact list`
2. **行业/政策背景搜索** — 如适用（OPC 政策、竞品动态、官方媒体口径）
3. **延展话题准备** — 行业趋势、产品对标、AI 话题

**必须用飞书交互卡片输出**，格式参考 `output-style-xiaoguanjia` skill。

**实战案例**：2026-07-16 WeWork 社区负责人会议 — 非飞书客户，跳过 C360，搜索 OPC 政策 + WeWork 中国新闻 → 整理为话题清单卡片。

---

## 会后分析框架

会议结束后，从 JSONL 日志提取唯一字幕，套用以下框架生成结构化分析：

| 框架 | 分析维度 | 输出 |
|------|---------|------|
| **JTBD** | 客户"雇佣"飞书的底层任务（功能/情感/社会性） | 按三层分解需求 |
| **BANT** | 预算/决策权/需求紧迫度/时间线 | 成交可能性和优先级 |
| **Kano** | 基本型/期望型/兴奋型/反向需求 | 产品满足度评估 |
| **Mom Test** | 区分真痛点 vs 客套话 | 高/低信号标注 |

**使用原则**：数据优先，框架适配在后。不要用框架套数据，让数据选出最合适的框架。详见 `meeting-audit` skill 的「需求分析方法论」章节。

---

## 注意事项

1. **必须 `--as user`**：不能用 bot 身份，必须用户授权后以用户身份调用
2. **长 meeting_id ≠ 9 位会议号**：从 `+meeting-list-active` 拿的 `meeting_id` 才是正确的 API 参数
3. **无实时推送**：所有事件都靠轮询拉取，延迟 15-30 秒
4. **用户必须本人在会中**：Agent 不能替代用户入会，只能旁听用户已在的会议
5. **字幕需要去重**：同一 `sentence_id` 可能多次推送（修正/补全），保留最新版本
6. **旁听不可见**：会议里不会出现机器人，其他参会者感知不到
7. **发分析结果用 `--as bot`**：VC API 调用用 `--as user`，但飞书 IM 发消息用 `lark-cli im +messages-send --as bot`（当前无 `im:message.send_as_user` scope）
