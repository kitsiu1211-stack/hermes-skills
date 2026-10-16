# PLM / Windchill 材料库与转录对照表

来源：2026-10-13「飞书 & PLM对接」客户会（54 分钟，773 句字幕）+ 会中 `docs +search` 检索结果。
复用场景：任何 PLM / 研发数据管理方向的客户会（PTC Windchill、西门子 Teamcenter、达索 ENOVIA）。

---

## 1. 转录对照表（字幕会转错，先查这里）

| 字幕里出现的 | 实际是 |
|---|---|
| `Winch` / `温琼` / `window` | **Windchill**（PTC 的 PLM 产品） |
| `PC公司` / `PC` | **PTC**（Windchill 原厂） |
| `参数李航` / `参数领航` | **参数领航**（Windchill 的国内 ISV / 实施伙伴） |
| `PM系统` / `POM` / `PMM` / `PRM` | 均指客户的 **PLM 系统**（口语简称被转歪） |
| `飘的MCP` / `OS2` / `OSO` | OAuth / MCP 的口语转写 |
| `Measure` / `云图` / `inso` / `inspire` | 客户内部系统名的口语转写（不确定就写「客户内部系统」） |
| `aily` | Aily → 2026-08 起更名 **豆包工作伙伴**，不要写 Aily |

## 2. PLM 厂商格局（内部文档口径）

- 西门子 **Teamcenter**：汽车、轨道交通为主
- 达索 **ENOVIA / 3DE**：航空航天为主
- PTC **Windchill**：高科技电子为主
- 三家绝对领先，软件 + 实施成本百万级以上

飞书可售卖内容（参数领航）：Windchill PLM 产品 + 与飞书高度集成的 PLM 实施（office 集成 + meego 集成插件）。

## 3. 材料库（已检索验证，可直接复用）

| 材料 | 链接 | 用途 |
|---|---|---|
| 飞书 × AI PLM 协同解决方案｜消费电子行业 | https://et9ut9lwf8.feishu.cn/docx/GKBJdtks9oJpFaxzdkDcff8Wnyh | **含 Windchill MCP 段落**：飞书里自然语言查 BOM / 物料状态 / 变更进度 / 产品规格，对话发起流程。对客首选 |
| 飞书 × AI PLM 协同解决方案｜机器人行业 | https://et9ut9lwf8.feishu.cn/docx/W7KIdQcmdoG0lnxGecBcKHtNnMd | 同上，机器人行业版本；含 Windchill 产品主页链接 |
| 飞书项目协同 PLM 提效解决方案（对客） | https://bytedance.larkoffice.com/docx/MFs9dKIFhoLppcxziAoclayUnSd | 飞书项目 + PLM 数据管理，讲「1+1>2」的路径 |
| 飞书 PLM 提效系列解决方案（for 客户） | https://bytedance.larkoffice.com/docx/Y4LUdFakYoR0JMxWrUJcdbTInVf | 系列方案入口 |
| 参数领航-WindChill PLM｜销售一指禅 | https://bytedance.larkoffice.com/wiki/KWElwEFJeiYiiPkALZccbTEEnOd | **内部**，对齐卖点用 |
| 协作客户一览表 - 飞书 × 清晰软件/参数领航 | https://et9ut9lwf8.feishu.cn/base/XewZbP78XaUAzSsPnCscsMVjnPb | 存量/在谈客户 Base，看同 ISV 还有哪些客户 |
| 区域南区 ISV 专项宣贯 | https://bytedance.larkoffice.com/wiki/BNMLwCpEAil27wkuotncWtfmnLa | meego × Windchill PLM 集成方案 |
| 2026 飞书生态伙伴清单（对内版） | https://bytedance.larkoffice.com/wiki/S6aiw1ozTiAu3LklhClcTzgHnL7 | 伙伴与联合方案索引 |

检索关键词（已验证有效）：`Windchill PLM`、`参数领航 Windchill`、`飞书项目 PLM`。
（单搜 `PLM` → 1000+ 条噪音，别用。）

## 4. 系统对接类会议的技术要点（飞书侧口径，可复用）

把客户 PLM 的 OpenAPI 封装成 MCP → 在豆包工作伙伴里自然语言调用。三条路径：

| 路径 | 优点 | 代价 |
|---|---|---|
| 集成平台快速封装 | 最快，用现成配置产出 MCP 地址 | key 共用、权限区分弱，只算初步打通 |
| OAuth 2.0 | 飞书天然支持整套 OAuth 2.0，填飞书授权地址即可；请求带飞书 Token，可反查用户身份做**人权限隔离** | 纯内网场景不合适 |
| **OAuth 2.1（内网场景飞书更推荐）** | 去掉 2.0 的不安全点，最新协议 | 授权链接 + 标准接口都要自己实现，开发量大 |

关键澄清（客户常问）：**MCP 是标准协议，不是只能在飞书里调**——其他平台/系统也能调；只要与飞书账号体系打通，就能按飞书用户做权限匹配隔离。

## 5. 老 PLM 系统的典型卡点（判断客户为什么推不动）

1. API 只有**租户级**——不分权限，「你用我用权限一样」，做不到个人级；客户要的是用户级 API + 账号映射
2. 认证太原始——**HTTP Basic 账密**，没有免密 / OAuth，封装 MCP 接不进去
3. **文档缺失、质量差**——「死 bug 多、标记不清，不像飞书文档看一眼就会」；客户内部原计划用 n8n 做插件也因此搁置
4. 原厂 MCP 常在调试中、未交付、非标准——**不能只等它**
5. **页面抓取 / 类爬虫路线一定要判死**：非开放 API 不稳定（系统一更新就废）、拿不到结构化 BOM、不能按料号查图纸/下载，只够做统计
6. 保密顾虑（图纸等）的标准回答：走个人账号则「手动能干的事它才能干」，系统权限即边界，不可下载的仍下载不了

## 6. 客户已有的 skill 方向（可直接复述给下一个客户）

个人提效线（用豆包工作伙伴 / Aily 写 skill）：
- 查询 skill：各项目硬件原理图 / PCB / 结构 BOM / 图纸的上传情况 → 出报表（以前要挨个目录点）
- 导入 skill：把硬件产品 BOM 导入 PLM
- 校验 skill：与 ERP 交叉比对，验证导入准确性

工作台线（Cursor 写好 → 发布到妙搭）：
- 接飞书项目 MCP，展示项目总览 + 每个项目的交付线
- 在飞书项目 / BOM / CRM / ERP 之上搭工作流、agent、skill，数据最终落回 PLM

飞书 CSM 侧给客户的 4 类 skill 方向：① 查询类（报文/项目进展） ② 通知 + 风险预警（规则包成 skill） ③ 决策分析建议（评审、交付情况） ④ 结合其他系统做组合场景（MES/ERP/订单/客户打通）。
口径：**公开市场暂时没有现成 PLM skill**——每家企业 PLM 用法不同，属于企业自身资产。
