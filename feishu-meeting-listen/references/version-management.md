# 版本管理规范

## 铁律

1. **新版 = 旧版全部功能 + 新功能**（只叠加不删减）
2. **升级前 Obsidian 存档**旧版完整代码 + cron 配置
3. **手动流程跑稳 3 次**再考虑自动化
4. **用户说回退立刻回退**，不修补
5. **改动前先读历史版本**（`versions/` 目录）

## 归档结构

```
~/Documents/Obsidian Vault/hermes-skills/feishu-meeting-listen/
├── retrospective.md          # 版本演进复盘
├── SKILL.md                  # 当前 SKILL.md 快照
├── meeting_detect.py         # 当前脚本快照
├── poll.sh                   # 当前旁听脚本快照
└── versions/
    └── V3-restored-20260716.md  # 版本快照（含完整代码+cron配置）
```

## 升级操作

1. 将当前 SKILL.md、脚本、cron 列表写入 `versions/V<新版号>-<日期>.md`
2. 更新 Obsidian `hermes-skills/feishu-meeting-listen/` 下的快照文件
3. 确认旧版全部功能在新版中仍可用
4. 再开始写新功能代码

## 回退操作

1. 从 `versions/` 找到目标版本快照
2. 复制代码回 `~/.hermes/scripts/` 和 `~/.hermes/skills/feishu/feishu-meeting-listen/`
3. 恢复 cron 配置
4. 清理当前 `meeting_state.json` 状态
