---
name: 双周Skill同步
description: 每双周周五检查新建Skill，上传到GitHub和妙搭SkillHub，输出飞书卡片报告
---

# 双周 Skill 同步

## 架构

1 Generator + 1 Evaluator

```
检测14天内新建Skill → Generator(汇总清单) → Evaluator(校验) → 上传GitHub+SkillHub → 报告卡片
```

---

## Phase 1: 检测新建 Skill

```bash
find ~/.hermes/skills -name 'SKILL.md' -newer <(date -v-14d +%Y-%m-%d) -exec dirname {} \; | sed 's|.*/||' | sort -u
```

如果没有新 Skill，输出"本周期无新建 Skill，跳过同步。"并结束。

---

## Phase 2: Generator — 生成同步清单

对每个新 Skill：
1. 读取 SKILL.md 获取 `name`、`description`
2. 获取所属 category（目录名）
3. 检查是否已有 GitHub 仓库（`git remote -v` 或搜索 `github.com`）
4. 生成上传计划

---

## Phase 3: Evaluator — 校验

| 维度 | 检查点 |
|------|--------|
| 完整性 | SKILL.md 是否存在？name/description 是否完整？ |
| 去重 | GitHub/SkillHub 上是否已存在同名 Skill？ |
| 合规 | 是否符合 Gen→Eval 架构要求？ |

不通过的 Skill 标注原因，不阻塞已通过的 Skill 上传。

---

## Phase 4: 上传

### GitHub
```bash
# 对每个 skill 目录
cd ~/.hermes/skills/<category>/<skill-name>
git init && git add . && git commit -m "Add skill: <name>"
# 推送到用户 GitHub
```

如果已存在 repo，用 `git add` + `git commit` + `git push` 更新。

### SkillHub
参考 `skill-hub` Skill 的流程：
1. 读取 `/tmp/skillhub/index.html`
2. 在对应分类添加卡片对象
3. 更新计数
4. 发布：`cd /tmp/skillhub && lark-cli apps +html-publish --app-id app_179xr3ds4q0 --path ./index.html --as user`

---

## Phase 5: 输出报告卡片

发送到飞书 Home 频道：

```json
{
  "header": {"title": "双周 Skill 同步报告", "template": "blue"},
  "elements": [
    {"tag": "div", "text": {"tag": "lark_md", "content": "周期：<开始> ~ 今天"}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "本次新增 N 个 Skill：\n✅ skill-a → GitHub + SkillHub\n✅ skill-b → GitHub + SkillHub\n⚠️ skill-c → 仅 SkillHub（GitHub 已存在）"}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "<font color=grey>SkillHub：https://bytedance.feishuapp.com/app/app_179xr3ds4q0</font>"}}
  ]
}
```

---

## Cron 配置

- 频率：每双周周五 10:00
- 不自动运行——cron 执行后，如果无新 Skill 直接结束，有则上传+报告
