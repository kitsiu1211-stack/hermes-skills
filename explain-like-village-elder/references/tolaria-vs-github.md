# 示例：Tolaria vs GitHub 作为 Skill 管理中心

## 场景

8 个 Skill，Agent 每周每个 Skill 更新一次状态、记一条日志。

## Token 消耗

| 操作 | GitHub 方式 | Tolaria 方式 |
|------|------------|-------------|
| 找到要改的文件 | 先 ls 再读 8 个文件（≈4000 token） | 打开就知道结构（≈200 token） |
| 了解关联 | 读每个 Skill 的 Related 段落（≈3000 token） | belong_to 自动注入（≈500 token） |
| 改一个字段 | 全文改 → commit → push（≈2000 token/次） | MCP 一次调用（≈300 token/次） |
| 避免写冲突 | Agent 自己检查（≈1000 token） | expectedMtime 自动拒绝（0 token） |
| **每周 8 次合计** | **≈56,000 token** | **≈8,000 token** |

## 效率

| | GitHub | Tolaria |
|---|--------|---------|
| 第一次打开 | 爬目录 → 读文件 → 建索引 | 打开就干 |
| 找"所有已发布 Skill" | 逐个读 status 字段 | 一次语义查询 |
| 多人多 Agent 协作 | 后 push 覆盖先 push | mtime 锁拒绝后写 |
| Agent 开箱即懂 | 每次 prompt 解释 | AGENTS.md 一次说明 |

## 情景推荐

| 场景 | GitHub | Tolaria |
|------|--------|---------|
| 一次性发布，半年不动 | ✅ | 大材小用 |
| Agent 持续维护，每周改动 | ❌ 每次重爬 | ✅ 省 7 倍 Token |
| 多 Agent 协作同一知识库 | ❌ 覆盖风险 | ✅ 锁保护 |

## 一句话

"以前 Agent 干活像进图书馆，每次都要先找书架、翻目录、一页页找；现在 Agent 干活像进自己家，灯一开就知道东西在哪。"
