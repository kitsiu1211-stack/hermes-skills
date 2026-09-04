# Kimi Code 委派

## 何时用 Kimi Code

用户说「让 kimi code 搭一个」「kimi code 在群里」时，用 `<at>` 标签 @mention 把需求发到 Agent协作群。

## 命令

```bash
lark-cli im +messages-send \
  --chat-id oc_219a613c13292855c2dc4b80e59dfd6e \
  --as bot \
  --msg-type text \
  --text '<at user_id="ou_75e812630b3c51fc879295c78424898c">Kimi Code</at> <需求描述>'
```

## 关键注意事项

1. **必须 @mention** — lark-cli API 不自动转换 plain text `@Name` 为 `<at>` 标签，Kimi Code 只监听 `<at>` 触发。2026-07-25 实证：发 plain text 两次都没收到，加 `<at>` 标签立即生效。
2. **用 `--as bot`** — user identity 缺少 `im:message.send_as_user` scope
3. **需求要完整自包含** — Kimi Code 没有上下文，题目、选项、技术要求全写进消息
4. **回复在主聊天** — 用 `lark-cli im +chat-messages-list` 轮询获取
5. **回复不稳定** — webhook 偶尔死，如果 2 分钟内没回复，重新发一次
6. **对外表述先确认再下发** — 任务书里涉及「免费/价格/收费性质/承诺/上线时间」等对外文案，必须先与用户确认口径再发给 Kimi Code。2026-08-18 实证：任务书写「免费」被用户当场纠正「不要写免费，也不写价格，体现这项服务就行」，导致任务书重发

## 验证 Kimi Code 的交付物

Kimi Code 报告「已完成」后，需验证。**关键认知**：Kimi Code 在独立环境运行（独立 VM/workspace），编译产物和源码通常不在本机磁盘上。不要花大量时间搜索本地文件——这些文件大概率不存在。

### 高效验证清单（按优先级）

1. **API 数据验证**（1 次 terminal 调用，最可靠）
   - 直接调上游 API 核对数值（如 `curl DeepSeek /user/balance`）
   - Kimi Code 报告的数值 vs 你查到的实时值 → 确认数据管道准确

2. **进程验证**（`ps aux | grep`）
   - 部分交付物（如 menubar app）以进程运行，可查进程是否存在
   - ⚠️ 但进程名可能与项目名不同（如 NotchBar 可能不以 "NotchBar" 进程名出现）

3. **共享数据文件验证**（如 `~/.local/share/kaboo/` 下的 JSON）
   - 部分项目会写数据到共享位置，可读文件确认状态

4. **视觉验证**（最后手段）
   - 需要 `computer_use` (cua-driver)。如果未安装 → 直接告知用户，让用户在屏幕上确认
   - 不要为了视觉验证去尝试安装 cua-driver（除非用户要求）

### 反模式：不要做的事

- ❌ 用 `find` 搜索全盘找 NotchBar.swift / token_bar.py 等源码 → 这些文件在本机不存在
- ❌ 反复搜索不同路径期望找到 Kimi Code 的编译产物
- ❌ 在无法验证视觉时编造「看起来正确」的结论

### 汇报模板

验证完后给用户的汇报遵循三件事原则：
```
1. API/数据验证结果（能确认的）
2. 什么没法验证 + 原因（cua-driver 未安装 / 进程未找到 / 文件不在本机）
3. 问用户：屏幕上能看到吗？
```

## 需求模板

```
Kimi Code，帮我搭一个 <用途>：

<技术要求>（单HTML文件、移动端适配等）

<具体内容>（题目、选项、正确答案）

<特殊要求>（管理后台、分页等）
```

## 回复轮询与私聊回报（2026-07-25）

发完任务后，等待 30s-2min，用 `chat-messages-list` 查最新消息。如果 sender=Kimi Code，提取回复核心内容，精简摘要发回用户私聊（用户不需自己去群里翻）。

## 实际案例

### RunCat 桌面 widget 关掉（2026-07-25）
需求：导航栏已有小猫显示，桌面 floating widget 重复 → 关掉 desktop overlay。Kimi Code 执行：停 FloatBar 进程、改 menubar.swift，验证完毕。

### DeepSeek 余额刘海屏插件（2026-07-25）
需求：余额从桌面迁移到刘海右侧，可点击查看消费明细。
- 根因：`token_bar.py` 无后台定时刷新 → status.json 卡在旧值 ¥37.15，实际 ¥88.56。修复：加 30min 后台刷新线程。
- 位置：用 NSPanel（statusBar+1 层级）钉在刘海右缘。
- 后续迭代：改 logo（去掉电池图标）、加点击交互展示充值明细。
- 关键约束：macOS 无官方刘海 API，用 Boring.Notch 方案的 NSPanel 逼近。
