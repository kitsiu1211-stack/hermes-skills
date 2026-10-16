# weread CLI 排障参考

## IPv6 双栈连接失败（2026-07-05 实测）

**环境**：macOS 26.5.1, Node v24.13.0, weread-agent-cli v0.1.2

**症状**：`weread doctor` 显示 Ready，但所有命令超时（60s+），最终返回 `network_error: fetch failed`。

**根因**：`i.weread.qq.com` 解析到两个 IPv6 地址（`2402:4e00:1430:1501::` 和 `2402:4e00:1430:1502::`），Node.js `fetch()` 默认优先 IPv6，连接卡死。curl（IPv4，`43.159.234.125`）正常。

**排查路径**：

```bash
# 1. 确认 auth 正常
weread doctor

# 2. 确认 gateway 可达（curl IPv4）
curl -s --max-time 5 "https://i.weread.qq.com/api/agent/gateway" \
  -H "Authorization: Bearer $(python3 -c "import json;print(json.load(open('$HOME/.weread-cli/config.json'))['apiKey'])")" \
  -d '{"api_name":"/_list"}'

# 3. 确认是 Node.js IPv6 问题
node -e "https.get('https://i.weread.qq.com/api/agent/gateway',{family:4,timeout:5000},r=>{r.on('data',()=>{});r.on('end',()=>console.log('IPv4 OK:',r.statusCode))}).on('error',e=>console.log('ERR:',e.message))"
# 对比不加 family:4 的情况（会超时）
```

**修复**：patch `dist/client.js`，将 `fetch()` 替换为 `https.request()` + `family: 4`：

```javascript
import https from "node:https";

function httpsFetch(url, options = {}) {
    const { body, headers = {}, signal, method = "GET" } = options;
    const parsedUrl = new URL(url);
    const opts = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || 443,
        path: parsedUrl.pathname + parsedUrl.search,
        method,
        headers: { ...headers, "Accept-Encoding": "identity" },
        family: 4,
        timeout: 30000,
    };
    // ... promise wrapper around https.request(opts, ...)
}
```

然后在 `fetchWithRetry` 方法中将 `await fetch(this.baseUrl, ...)` 替换为 `await httpsFetch(this.baseUrl, ...)`。

**风险**：`npm update weread-agent-cli` 会覆盖 patch。建议向 CLI 维护方提 issue 请求在代码中加入 `family: 4` 支持。

## SKILL_VERSION 过期

**症状**：返回 `upgrade_required` 错误，`current_version` 低于 `latest_version`。

**修复**：
```bash
# 1. 下载最新 skill 引用文件
curl -sL "https://cdn.weread.qq.com/skills/weread-skills.zip" -o /tmp/weread.zip
unzip -o /tmp/weread.zip -d /tmp/weread-update
cp /tmp/weread-update/weread-skills/*.md ~/.hermes/skills/weread/references/

# 2. 更新 SKILL_VERSION
# dist/client.js 中: export const SKILL_VERSION = "1.0.4";  → "1.0.5"
```

### 2026-10-11 实测（1.0.4 → 1.0.5）

- 触发场景：`weread doctor` 报 Ready 且 skill_version 1.0.4，但 `shelf list` / `search` 全部返回
  `upgrade_required`（`ok:false`），**注意回包里仍带 `response` 原始数据**，别误判成成功。
- `current_version` 取自 **CLI 常量** `dist/client.js` 的 `SKILL_VERSION`（随请求发给服务端），
  **不是**读本地 SKILL.md —— 所以只覆盖 references/ 文件不生效，必须改这个常量。
- ⚠️ **不要 `npm i -g weread-agent-cli` 升到 0.1.4**：实测 0.1.4 仍写死
  `SKILL_VERSION = "1.0.4"`，且 **不含** 上面那个 IPv6 `family:4` patch（`grep -c "family: 4"` = 0）。
  升级会同时打破 IPv6 连接并让 upgrade_required 复发。当前正确姿势 = 保留 0.1.2 + 手改常量。
- 顺手确认：zip 内 10 个文件（SKILL.md / SERVICE_PROFILE.md / search,shelf,book,notes,readdata,review,discover,profile）
  对应 `~/.hermes/skills/weread/references/`；`domain-rules.md`、`first-use.md` 是本地自建文件，**不在 zip 里，别删**。
