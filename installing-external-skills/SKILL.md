---
name: installing-external-skills
description: Use when 用户让装外部 skill；装完必须实跑最小用例验证。
category: devops
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, install, onboarding, github, verification]
    related_skills: [skill-distribution, hermes-agent]
---

# 把外部 skill / 工具接进 Hermes

## When to Use（触发）

- 用户丢一个 GitHub 链接：「帮我安装一下这个 skill」「这个 skill 你能用吗？可以的话装上」
- 用户要装第三方 CLI / 工具链，之后要拿它干活（不只是装完就算）
- 装完后用户会说「那我们找个案例测试一下」——所以第 5 步的冒烟测试是必须的，不是可选项

## 步骤

### 1. 先看仓库，不下载

```bash
curl -s https://api.github.com/repos/<owner>/<repo> | python3 -c "import sys,json;d=json.load(sys.stdin);print({k:d.get(k) for k in ['full_name','description','stargazers_count','language','license','default_branch','pushed_at']})"
curl -s "https://api.github.com/repos/<owner>/<repo>/git/trees/<branch>?recursive=1" | python3 -c "
import sys,json
for t in json.load(sys.stdin)['tree'][:80]: print(t['type'][:4], t.get('size',''), t['path'])"
```

看三件事：有 `SKILL.md` 吗（是不是 agent skill）、有 `package.json` / requirements 吗（依赖多重）、有没有大体积 assets（决定落地体积）。

### 2. 取仓库

- 首选 `git clone --depth 1`
- **clone 到 github.com 超时就换 codeload tarball**（本机实测 `github.com:443` 不通而 codeload 通，`raw.githubusercontent.com` 也不通返回 000）：

```bash
curl -sL --max-time 60 -o /tmp/x.tgz "https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/<branch>"
mkdir -p <dir> && tar xzf /tmp/x.tgz -C <dir> --strip-components=1
```

需要单个文件时从 tarball 里取，别卡在 raw 域名上。**别用浏览器去抓**——本机 Chrome 远程调试要人工点授权，会白等一轮。

### 3. 读 frontmatter，实测依赖

看 `name / description / compatibility / metadata.requires`，然后**实测**（`node -v`、`python3 -V`、有没有 Chrome…），不要凭印象说「应该可以」。

### 4. 落地位置

`~/.hermes/skills/<name>/`（顶层，或带 category 子目录）。

- 标准布局（SKILL.md 加 supports 目录）→ 可以用 skill_manage
- **非标准布局（kit/ examples/ src/ agents/ evals/ 等）→ 一律 `rsync -a --delete --exclude '.git' <src>/ ~/.hermes/skills/<name>/`**。这类目录会被 skill_manage 的写入规则拦掉；rsync 不受限。
- 装完 `skill_view(name=...)` 确认 Hermes 真的能加载（frontmatter 解析正常、linked_files 列得出来）

### 5. 冒烟测试（必做）

**只跑 `--help` 不算「能用」。** 跑它自带的**最小可用示例**，并把真实输出贴给用户看。例：

```bash
node examples/<smallest>/build.mjs      # 构建类
node scripts/capture.mjs <输出> --out /tmp/shot.png   # 校验类
```

产物是图/文件/报表的，**自己用 `vision_analyze` 或 read_file 把产物读一遍**再下结论——「命令没报错」和「产物是对的」是两件事。

### 6. 回报格式（用户要的是判断，不是安装日志）

| 项 | 内容 |
|---|---|
| 位置 | `~/.hermes/skills/<name>/`（体积） |
| 依赖 | 实测结果（版本号，不是「应该满足」） |
| 实测 | 冒烟测试的真实输出摘要（console clean / 产物路径） |
| **成本** | 这个 skill 干一次活要花多少（token / 时间 / 几轮返工） |
| 建议节奏 | 先做最小档验证手感，再上大档 |

第 4 项最重要：**重型 skill 要提前说清成本再开跑**，让用户自己决定做到哪一档。用户对「装好了」无感，对「装好了 + 干一次要多久 / 值不值」有判断。

### 7. 把会话级细节写进 references/

装法、踩坑、可复制的成品模板路径、上游 quirk → `references/<skill>-<topic>.md`。SKILL.md 只留可复用的步骤与铁律。

## 铁律

1. **装完必须实跑一次最小用例**才算「能用」，并贴真实输出。
2. **如实报成本**：重型 skill（每份产出要写上千行代码 + 多轮自检返工）先说清，不要等用户催「卡住了么」。
3. **用户驱动安装的 skill 属于用户**：`created_by=None`，curator 不能事后改它（需 `hermes curator adopt <name>`）。所以**「怎么用」的经验不能只写在它目录里**——那是用户的地盘。要在自己能维护的地方另存一份，并在回复里提醒用户「上游更新覆盖安装时，写在它目录下的笔记会一起被冲掉」。
4. **别承诺只有它自己能做的事**：如果 skill 需要特定模型/显卡/浏览器能力，先说边界再动手。

## 相关

- `skill-distribution` — 反方向：把自己的 skill 脱敏后对外分发（独立仓库 + GitHub 发布）
- `hermes-agent`（bundled）— Hermes 自身配置与 `hermes skills install` hub 路径
- `references/anatomy-isometric-figures.md` — 实测案例：Anatomy（等距 SVG 原理图）的装法 + 构建/验收循环 + 第一张图的三处返工
