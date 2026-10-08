# Hermes capability test battery

Four scripts built during the 2026-10-07 capability-testing session, covering
file ops, memory, delegation, cron, multi-file coding workflows, concurrency
limits, prompt-injection resilience, and the Runs API. Findings from running
these are logged in the catalog (tag `hermes`) and summarized in
[BACKLOG.md](../BACKLOG.md).

Intended use: re-run against a rebuilt/reinstalled Hermes to confirm nothing
regressed and that any patched bugs now pass (see the VPS reimage plan).

## Setup

1. Open an SSH local port-forward to the Hermes API server (port 8642 by
   default):
   ```bash
   ssh -L 18642:127.0.0.1:8642 root@<hermes-vps-ip>
   ```
2. Create (or reuse) a dedicated `hermes-testing` profile so these probes
   never touch the real default profile's memory/state:
   ```bash
   ssh root@<hermes-vps-ip> "su - hermes -c 'hermes profile create hermes-testing --clone'"
   ```
   Then overwrite that profile's `SOUL.md`/`memories/USER.md`/`memories/MEMORY.md`
   with fresh, testing-specific content (see catalog entity
   `hermes-testing-profile-created-2026-10-07` for the content used last time),
   and add a fresh `API_SERVER_KEY` to its `.env`.
3. Export the required environment variables:
   ```bash
   export HERMES_API_KEY="<the hermes-testing profile's API_SERVER_KEY>"
   # optional overrides, defaults shown:
   export HERMES_BASE_URL="http://localhost:18642/p/hermes-testing"
   export HERMES_MODEL="hermes-testing"
   ```

## Running

Run in order — later scripts assume the ones before them haven't crashed the
model server:

```bash
python3 testing/stress_test_1.py   # file ops, memory, delegation, cron, multi-tool chaining, long-context, destructive-instruction judgment, multilingual, structured output
python3 testing/stress_test_2.py   # tool selection/discrimination, parallel calls, instruction-following, honesty checks, a basic multi-turn coding workflow
python3 testing/stress_test_3.py   # real multi-file coding workflow: debug a failing test, rename/refactor, git branch+diff, patch precision, code review, background process monitoring, conflicting instructions
python3 testing/stress_test_4.py   # prompt-injection resilience, same-session concurrency, 8-way subagent fan-out
```

**Caution on `stress_test_4.py`**: the concurrency/fan-out tests in this
script (test B and C) sent ~10 simultaneous model-requiring requests and
crashed the local ik_llama.cpp model server outright in the original run
(it has exactly one inference slot). If you only want the injection-resilience
test (A), comment out the concurrency and fan-out calls before running, or be
ready to restart the model server (and possibly the Hermes gateway itself —
zombie retries from the crash kept re-occupying the single slot even after
the model server came back) if it happens again.

Each script writes line-delimited JSON results to `/tmp/stress_test_N_results.jsonl`
and prints a one-line timing/status summary per call as it runs.
