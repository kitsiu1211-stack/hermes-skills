# auto_mode 竞争条件（v5 已修复）

## 问题

`poll-v5.sh` 的 `auto_mode` 循环与 `run_poll` 子进程之间存在竞争条件，导致会议结束不被检测。

## 时序

```
1. 会议正常进行中，run_poll 每 10s 轮询一次 +meeting-events
2. 用户离会 / 会议结束
3. auto_mode 的下一个 sleep 10 到期 → +meeting-list-active 返回空
4. auto_mode 发现 cur_id 为空 + last_id 非空 → 立刻 kill run_poll
5. run_poll 被 kill 时正在 sleep 10 等待下一次轮询
6. run_poll 从未有机会调用 +meeting-events 看到 "user is not in the meeting"
7. 结果：日志无 meeting_ended 标记，无结束通知
```

## 案例

2026-07-15，机智连接（PLAUD）会议（meeting_id 7662661477900569554）：
- 最后一条字幕时间：17:06:14
- 用户约 17:06 离会
- auto_mode 在 17:06+10s 左右发现无活跃会议 → kill run_poll
- run_poll 在 sleep(10) 中，来不及检测 meeting end
- 日志文件和告警都缺失 meeting_ended

## 修复（v5，2026-07-15）

```diff
-      log "AUTO: no active meeting, resetting (was $last_id)"
-      last_id=""
-      [ -n "$poll_pid" ] && kill "$poll_pid" 2>/dev/null || true
-      poll_pid=""
+      log "AUTO: no active meeting, waiting for run_poll to finish naturally..."
+      if [ -n "$poll_pid" ]; then
+        local waited=0
+        while kill -0 "$poll_pid" 2>/dev/null; do
+          sleep 2
+          waited=$((waited + 2))
+          if [ $waited -ge 120 ]; then
+            log "AUTO: run_poll stuck >120s, force killing"
+            kill "$poll_pid" 2>/dev/null || true
+            break
+          fi
+        done
+      fi
+      log "AUTO: run_poll exited, resetting (was $last_id)"
+      last_id=""
+      poll_pid=""
```

核心改动：auto_mode 不再主动 kill run_poll，改为等待它自然退出（run_poll 在轮询中遇到 `"user is not in the meeting"` 后正常 return），最多等 120s 后强制清理。

## run_poll 的退出逻辑（未变）

```bash
if echo "$events" | grep -q "user is not in the meeting"; then
  log "END: 用户离会"
  echo '{"type":"meta","event":"meeting_ended",...}' >> "$log_file"
  send_alert "【🔚 会议结束】..."
  return 0
fi
```

修复后，run_poll 有充足时间在下一个 sleep 10 到期后完成 API 调用 → 检测到离会 → 写 meeting_ended → 发结束告警 → 正常退出。
