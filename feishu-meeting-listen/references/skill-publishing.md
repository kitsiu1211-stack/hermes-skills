# 技能发布到 GitHub 流程

> 将 Hermes 技能打包为 Agent 无关的公开仓库，供同事安装。

## 脱敏清单

发布前必须清除以下内容：

| 类型 | 需替换 | 示例 |
|---|---|---|
| 群 ID | `oc_xxx` | `ALERT_CHAT` 改为环境变量 |
| 用户 ID | `ou_xxx` | 从文档中删除 |
| C360 账号 ID | `005BBxxx` | 从文档中删除 |
| 客户 account ID | `001BBxxx` | 从文档中删除 |
| 内部域名 | `bytedance.xxx` | 替换为通用描述 |

## 改造要点

1. **去掉 Agent 绑定**：不要 `hermes skills install`，改为 `git clone && bash install.sh`
2. **硬编码 → 环境变量**：群 ID、路径等用 `${VAR:-default}` 模式
3. **添加 install.sh**：复制脚本到 `~/.local/bin/`，调用 `setup.sh` 检查环境
4. **添加 setup.sh**：检测 `lark-cli` / `lark-c360`，未安装自动装
5. **README 要短**：安装 + 使用 + 可选配置，3 段即可。不要长文

## 推送流程

```bash
cd /tmp/skill-package
git init && git add -A && git commit -m "feat: initial release"
gh repo create <repo-name> --public --source . --remote origin --push
```

> ⚠️ 如果 push 冲突（远程已有更新），`git pull --rebase` 优先于 `--force`。

## 文件结构

```
repo/
├── README.md          # 简短说明（Agent 无关）
├── install.sh         # 一键安装
├── scripts/
│   ├── poll-v5.sh     # 主脚本
│   └── setup.sh       # 环境检查 + C360 安装
```

> 删除 `SKILL.md`（Hermes 专有格式），用 README.md 替代。
