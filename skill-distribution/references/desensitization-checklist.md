# 脱敏检查清单（发布公开 skill 前逐类扫描）

扫描命令：`grep -rn "<敏感词>" <release目录> | grep -v ".pyc"`，全部清零才算过。

## 1. 身份类（必须环境变量化，缺失即退出）

| 敏感项 | 示例 | 处理 |
|--------|------|------|
| 个人姓名 | 袁鑫杰 | `C360_OWNER_NAME` 环境变量 |
| C360 user id | `005BB000000Hg80YAC` | `C360_OWNER_ID` 环境变量 |
| chat_id | `oc_e2f79ec1614a1efe1ebcd7c679bb45a8` | `RADAR_HOME_CHAT` 等环境变量 |
| open_id | `ou_dc055b0b5b0b5db2b1af5e79c0536db6` | 环境变量或删除默认值 |
| cron job id | `755f8ece681d` | 删除（别的团队没有这个 job） |
| 同事姓名 | 陈柳均Lilo、张东琪 | 删除/泛化为「其他 RM」 |

处理模板（Python）：
```python
MY_OWNER = os.environ.get("C360_OWNER_NAME", "")
if not MY_OWNER:
    print("错误：请先设置环境变量 C360_OWNER_NAME", file=sys.stderr)
    sys.exit(1)
```

## 2. 业务数据类（匿名化或泛化）

| 敏感项 | 示例 | 处理 |
|--------|------|------|
| 真实客户名 | 汉阳/雷鸟/疆海/高驰/零壹/唯迹/凯迪仕/机智连接/拓竹 | 「某客户」「某+行业+企业」（某庭院机器人企业） |
| 客户归属转移 | 吉比特→陈柳均Lilo | 「某游戏客户已转给其他 RM」 |
| 实测数据 | predict 567%、mom+138.5%、DAU 467、301→38 客户 | 泛化：「数百个」「占多数」「某客户 mom+138%」 |
| 内部代号 | 主题34 | 通用化：「AI 赢单升级信号清单」 |
| 内部路径 | `~/.hermes/radar_baseline.json` | 环境变量 `RADAR_BASELINE_PATH` |
| 金额档位 | 9.9万/29.7万/99万 | 保留（产品对外定价，是 skill 核心价值） |

## 3. 密钥类（必须清零，零容忍）

- `sk-`、`api_key`、`api-key`、`token`、`secret`、`Bearer`、`Authorization`、密码
- 注意区分「真实密钥」与「文档示例占位符」（`sk-*`、`API_KEY=***` 字面量）——示例可保留

## 4. 环境适配检查（脱敏之外的迁移问题）

- `~/.aily` 硬编码 → 环境探测（`~/.aily` → `~/.hermes` → 通用目录）
- `<text_tag>`、带引号 `<font color='grey'>` → 标准 lark_md（加粗 + 无引号 font）
- 卡片发送目标 chat_id 硬编码 → 环境变量

## 5. 验证双保险

1. 本地副本扫描清零
2. **从 GitHub 重新 clone 再扫一遍**（推送的内容可能和本地扫的不是同一份）
   ```bash
   rm -rf /tmp/verify && git clone -q <repo-url> /tmp/verify
   grep -rn "<敏感词>" /tmp/verify | grep -v ".git/" || echo "✅ 远端无敏感词"
   ```
