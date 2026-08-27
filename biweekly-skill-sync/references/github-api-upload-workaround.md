# GitHub API 文件上传（git push 无法连接时的替代方案）

## 场景

当 `git push` 因网络不通（防火墙/代理）失败时，`gh api` 仍可能通过 HTTPS API 正常工作。

## 方案：直接 PUT 文件内容

```bash
content=$(base64 -i <local_file> | tr -d '\n')
gh api repos/<owner>/<repo>/contents/<path> -X PUT \
  -f message="<commit message>" \
  -f content="$content" \
  -f branch=main
```

## 实测（2026-07-29）

- `git push` 超时（Failed to connect to github.com port 443）
- `gh repo create` 成功（API 443 端口可达）
- `gh api ...contents/<path> -X PUT` 成功上传单个文件
- GitHub Pages `gh api ...pages --input -` 成功启用
- GitHub Pages source path 仅支持 `/` 或 `/docs`，不支持 `/Projects` 等自定义路径

## 注意事项

- 大文件（>5MB）不适用 API 直接上传
- 需要 `gh auth login` 并确认 `repo` scope 已授权
