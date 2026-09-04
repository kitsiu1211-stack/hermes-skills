# lark-cli 授权 Scope 补充流程

当 lark-cli 报 `missing required scope(s)` 时，按此流程补齐。

## 标准流程

```bash
# 1. 无阻塞版——获取 device_code
lark-cli auth login --scope "<missing_scope>" --no-wait --json

# 2. 从返回中提取 verification_url + device_code
# 3. 生成 QR 码给用户扫
cd /tmp && lark-cli auth qrcode "<verification_url>" --output auth_qr.png

# 4. 展示 QR 图 → 用户扫码授权 → 用户确认

# 5. 续上轮询
lark-cli auth login --device-code "<device_code>"
```

## 关键 pitfall

- **不要在同一 turn 里展示 URL 后立刻阻塞执行 `--device-code`**
- device_code 有效期 600 秒，超时后需重新 `--no-wait --json`
- `--no-wait` + `--json` 返回三字段：`device_code`、`verification_url`、`expires_in`
- QR 码生成后**必须在回复中展示图片**，仅生成文件不算完成

## 已补齐的 Scope

| scope | 用途 |
|-------|------|
| `vc:meeting.meetingevent:read` | 旁听会议字幕 |
| `vc:meeting.message:write` | 在会中发弹幕 |
| `im:message.send_as_user` | 以用户身份发群消息 |
