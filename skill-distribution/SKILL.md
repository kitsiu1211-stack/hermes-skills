---
name: skill-distribution
description: 对外分发 Hermes skill：独立仓库+脱敏+质检+GitHub发布。用户要发 skill 给别的团队时使用。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skill, distribution, github, desensitization, publish]
    related_skills: [deep-grill, github-repo-management, 双周Skill同步]
---

## When to Use

用户要把本地 skill 发给其他团队 clone 使用，或说「成立单独的仓库」「公开到 GitHub」「像 XX skill 一样发出去」时。含内部数据的 skill 对外公开前必须先脱敏。

# Skill 对外分发（独立仓库 + 脱敏）

把本地 skill 打包成可对外分发的独立 GitHub 仓库。用户 2026-08-27 定调：**对外分享的 skill 用「一 skill 一公开仓库」形态**（已在 customer-alert-skill、ai-win-opportunity-radar 落地），不是塞进 hermes-skills 集合仓库。

## 触发

- 用户说「把这个 skill 发给别的团队」「成立单独的仓库」「像客户动态监控一样发出去」
- 其他团队要 clone 使用某个 skill

## Step 0：必须先问的三个决策（一次一问，别猜）

1. **仓库公开还是私有**？含内部数据的 skill（真实客户名、内部打法、C360 字段、实测数据）公开 = 泄密风险。用户可接受「公开 + 脱敏」。
2. **脱敏程度**：公开必脱敏；私有可以保留原版。
3. **客户清单/配置是否参数化**：skill 里硬编码的名单/别名抽到 `config/*.json`，别的团队改配置即用，不用改代码。

## Step 1：发布前质检门禁（deep grill）

发布前必须跑一遍质量审查，别把「能跑但有坑」的版本发出去。检查清单：

- **实跑测试套件**：`cd tests && python3 -m pytest -q`。SKILL.md 声称「全部通过」不算数——本次实测声称 110+ 全过，实际 4 failed（今天改的代码没同步测试断言）。打包前必须真跑。
- **文档 vs 代码一致性**：评分表/权重/扣分规则/报告格式，SKILL.md 与代码常量对得上吗？（本次发现三处互相矛盾）
- **硬编码扫描**：密钥、个人姓名、user_id、chat_id、open_id、cron job id、绝对路径（`~/.aily`、`~/.hermes`）。
- **环境耦合**：`~/.aily` 硬编码 = Aily 专用；分发到 Hermes 会静默失效（如历史文件读不到 → 去重失效）。改环境探测（`~/.aily` → `~/.hermes` → 通用目录）或环境变量注入。
- **卡片模板方言**：`<text_tag>`、带引号 `<font color='grey'>` 是 Aily 方言，Hermes/lark-cli 标准卡片不认（颜色失效/可能发送失败）。改为加粗 + 无引号 `<font color=grey>`。
- **遗留脚本**：v1 时代旧实现标注 LEGACY 或删除，防止 Agent 误用绕过新规则。

## Step 2：脱敏（公开必做，本地原版不动）

**铁律：本地技能目录保持原样（cron/业务照常跑），复制一份副本到 /tmp 脱敏，只推副本。**

```bash
cp -r ~/.hermes/skills/<name> /tmp/<name>-release
cd /tmp/<name>-release
```

敏感词类别与处理（完整清单见 `references/desensitization-checklist.md`）：
- 姓名 → 环境变量（`C360_OWNER_NAME`）或「某+行业+企业」
- user_id / chat_id / open_id → 环境变量，缺失即退出
- 客户名 → 「某客户」「某+行业+企业」
- 内部代号（如「主题34」）、cron job id → 删除/通用化
- 实测数据（具体百分比、客户数、金额）→ 泛化（「数百个」「占多数」）
- 密钥 → 必须清零
- 邮箱 → 小老鼠代@ + 注明还原

## Step 3：补分发文档

- `README.md`：别的团队怎么装（依赖安装命令）、环境变量配置、首次使用步骤、常见问题
- `.gitignore`：`__pycache__/` `*.pyc` `.pytest_cache/` `.DS_Store` 基线档案 `*.zip`
- SKILL.md 顶部加「公开分发版」说明块：环境变量配置 + 前置依赖

## Step 4：发布 + 验证

```bash
cd /tmp/<name>-release
git init -q && git add -A
git -c user.name="kitsiu1211-stack" -c user.email="kitsiu1211-stack@users.noreply.github.com" commit -q -m "..."
gh repo create <repo-name> --public --source=. --remote=origin --push
```

**验证两步缺一不可**：
1. 本地副本敏感词扫描清零（`grep -rn "敏感词" . | grep -v .pyc`）
2. **从 GitHub 重新 clone 再扫一遍**——推送的和本地扫的不是同一份，必须验远端

## Pitfalls

- `lark-cli drive +download` 没有 `--output-dir` 参数；`--output` 只接受**当前目录内相对路径**（绝对路径报 unsafe output path）。先 `cd` 再 `--output ./file.zip`。
- 测试全绿 ≠ 无 bug：测试可能没覆盖新改动（断言过时、打桩缺属性）。发布前看 pytest 输出，别只看 SKILL.md 的声称。
- 客户数、别名表、默认值三处不一致（如 SKILL.md 说 27 家、列表 28 家、代码 25 家）——参数化到配置文件后自动归一。
- 参数化配置要带内置兜底（配置文件缺失回退默认值），别的团队拷走时漏配置文件也不崩。
- 分发的 skill 如果依赖其他 skill（如 article-analysis 依赖 ljg-*），要么整个集合仓库一起发，要么 README 写清楚依赖。独立仓库形态下尽量自包含。
