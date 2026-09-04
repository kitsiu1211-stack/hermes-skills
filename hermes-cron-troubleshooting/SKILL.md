---
name: hermes-cron-troubleshooting
description: "Use when a Hermes cron job fails; fix via fallback chain or sentinel watchdog."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, cron, troubleshooting, fallback, provider]
---

# Hermes Cron Job Troubleshooting

## When to Use

Diagnose and fix failed scheduled jobs (cron). Trigger: user forwards a cron failure delivery like "⚠️ Cron '每日认知对话' failed: provider timeout" or says 又出问题了 about a scheduled task.

## Diagnosis workflow

1. **List jobs** — `cronjob action='list'`. Note `job_id`, `last_status`, `last_run_at`, `next_run_at`.
2. **Read the REAL error** — cron run output is saved at `~/.hermes/cron/output/<job_id>/<YYYY-MM-DD_HH-MM-SS>.md`. Tail it; the actual exception is at the bottom (e.g. `RuntimeError: Non-streaming API call timed out after 600s with no response`). The delivery message only carries the error class, not the detail — always check the file.
3. **Classify**:
   - `provider timeout` / `Non-streaming API call timed out` → provider-side stall (slow/no response). Fix: fallback chain (below). The 600s threshold is the hard interrupt; a healthy provider answers in seconds.
   - `last_delivery_error` non-null / delivery failure → message-send problem (platform token, chat id), not the model.
   - skill-load errors → inspect the job's `skills` list and the skill file.
4. **Fix, then re-run**: `cronjob action='run' job_id=<id>` fires the job in the background immediately; its outcome re-enters the conversation when done. Do NOT pause/delete a job for a transient provider failure.

## Fix: provider timeout → fallback provider chain

Top-level config key in `~/.hermes/config.yaml`: `fallback_providers` — a LIST of dicts `{provider, model, base_url?, api_mode?, key_env?}`. Legacy single-dict `fallback_model` is also read (merged, list wins).

- Primary model untouched; fallback entries tried in order on rate-limit / overload / 5xx / connection / timeout errors.
- The chain is GLOBAL — one config covers all cron jobs AND main-agent calls. No gateway restart needed (read via `load_config_readonly()` at call time).
- Custom providers (defined under `custom_providers` in config.yaml) work as fallback entries; either reference by provider name or make the entry self-contained with inline `base_url` + `key_env` (robust even if custom-provider lookup path differs).

```yaml
fallback_providers:
  - provider: minimax-openai
    model: MiniMax-M3
    base_url: https://api.minimaxi.com/v1
    key_env: MINIMAX_API_KEY
```

## Layer 3: Sentinel watchdog (guarantee the job actually completes)

Fallback chain prevents most call-level failures, but if the primary provider stalls past the hard timeout the run still dies. To guarantee "this cron must succeed today", add a sentinel: a no_agent script job that checks shortly after the main job's schedule and auto-reruns it on failure. (Real case 2026-08: 每日认知对话 died at 9:05 on a 600s DeepSeek timeout; dual sentinels at 9:35/10:05 now catch and rerun it same-day.)

Design rules (user-approved):
- **Delayed check + early exit**: 1–2 checkpoints 30–60 min after the main job. NOT all-day polling — success means silent exit, so extra checkpoints cost nothing anyway.
- **Zero token, zero noise**: no_agent=True; script prints NOTHING when the main job succeeded — empty stdout = no message, no LLM, no delivery. Only a failure prints an alert + triggers rerun.
- **Success detection pitfall**: failed runs ALSO write an output file — file presence ≠ success. Check `~/.hermes/cron/output/<job_id>/<YYYY-MM-DD>_*.md` content for fail markers (`## Error`, `RuntimeError`, `timed out`); only a file WITHOUT them counts. Real example: 09:30 failure file + 11:26 success file on the same day.
- **Trigger**: script runs `hermes cron run <job_id>` (CLI; fires on next scheduler tick — gateway/scheduler must be running). The rerun's completion re-enters the conversation as a normal cron run.
- **Idempotency is the precondition**: only auto-rerun jobs that are safe to run twice (job itself checks "already produced today?" — e.g. ebbinghaus-review's anti-duplicate rule). Otherwise a rerun duplicates side effects (cards/files).
- **Layer math**: execution + sentinel + fallback chain is enough. If both models AND the script fail simultaneously that's machine-level; accept it, don't over-engineer.

Template: `templates/sentinel_watchdog.py` — copy to ~/.hermes/scripts/, set JOB_ID, install as no_agent cron with `script=<name>.py`. Verify the success-detection logic against real output files before trusting it.

## Verify

1. `hermes fallback list` → prints Primary + ordered chain.
2. Probe the fallback endpoint for real (never trust config alone): `python3 ~/.hermes/skills/devops/hermes-cron-troubleshooting/scripts/test_fallback_endpoint.py` — sends a 2-token chat completion to the MiniMax CN endpoint using MINIMAX_API_KEY from ~/.hermes/.env.

## Pitfalls

- **Backup config before editing**: `cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak-$(date +%Y%m%d%H%M%S)`. Edit with python `yaml.safe_load`/`safe_dump` (`sort_keys=False, allow_unicode=True`) to preserve formatting — never hand-edit the YAML structure.
- **curl with inline `$(grep ...)` key extraction is BLOCKED** by the command parser (hardline blocklist). Use `execute_code` + urllib, or the probe script, for API-key-bearing requests.
- **Never print secrets**: extract keys from ~/.hermes/.env in python, strip surrounding quotes, show only length/prefix if needed.
- Check `fallback_providers: []` in config.yaml when diagnosing — empty chain = no safety net (this user's original failure state).
- Provider stalls are transient infrastructure events — the durable lesson is the fallback chain, not "provider X is broken".
