# launchd 系统守护配置

## 问题

poll-v5 作为 bash 脚本运行在 Agent 的终端 session 中。当 Agent 重启、终端关闭、进程被清理时，守护随之死亡，且无自动恢复机制。用户多次遇到「会议结束没检测到」的问题。

## 解决方案：macOS launchd

将 poll-v5 注册为 macOS 用户级守护进程（LaunchAgent），由 launchd 管理生命周期：

- **开机自启**（RunAtLoad）
- **崩溃自动重启**（KeepAlive）
- **独立于任何终端 session**，Agent 重启不影响
- **日志统一输出**到 `~/.hermes/logs/meeting-monitor.log`

## plist 配置

文件路径：`~/Library/LaunchAgents/com.yuanxinjie.meeting-monitor.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yuanxinjie.meeting-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/bytedance/.hermes/skills/feishu/feishu-meeting-listen/scripts/poll-v5.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>/Users/bytedance/.hermes/logs/meeting-monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/bytedance/.hermes/logs/meeting-monitor.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/Users/bytedance/.npm-global/bin:/Users/bytedance/.local/bin</string>
        <key>HOME</key>
        <string>/Users/bytedance</string>
    </dict>
</dict>
</plist>
```

## 部署命令

```bash
# 1. 写入 plist（如不存在）
cat > ~/Library/LaunchAgents/com.yuanxinjie.meeting-monitor.plist << 'EOF'
# … 上面的 plist 内容 …
EOF

# 2. 创建日志目录
mkdir -p ~/.hermes/logs

# 3. 杀掉旧进程
kill $(pgrep -f poll-v5.sh) 2>/dev/null

# 4. 加载守护
launchctl bootout gui/501/com.yuanxinjie.meeting-monitor 2>/dev/null
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.yuanxinjie.meeting-monitor.plist

# 5. 验证
launchctl list | grep meeting-monitor
pgrep -fl poll-v5
tail -3 ~/.hermes/logs/meeting-monitor.log
```

## 常用管理命令

```bash
# 查看状态
launchctl list | grep meeting-monitor

# 重启
launchctl bootout gui/501/com.yuanxinjie.meeting-monitor
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.yuanxinjie.meeting-monitor.plist

# 停止
launchctl bootout gui/501/com.yuanxinjie.meeting-monitor

# 查看日志
tail -f ~/.hermes/logs/meeting-monitor.log
```

## 注意事项

- `gui/501` 是当前用户的 GUI domain ID（macOS 上通常是 501）
- 如果用 `$(id -u)` 动态获取 UID 更安全，但 plist 中已固定
- `KeepAlive` 确保崩溃后自动重启，`ThrottleInterval` 防止快速重启循环
- PATH 必须显式设置，launchd 环境不继承 shell 的 PATH
