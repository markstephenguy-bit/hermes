# Session Brief — none pending

The MCPHub→sidecar-only migration this file used to describe is done, but
not the way the brief proposed it. See git history (`ca4b06d`, `a2db305`,
and the commit that closed this out on 2026-11-20) and CLAUDE.md's "One
gateway for every harness" section for the actual end state: both MCPHub
and the old `mcp_proxy_sidecar.py` systemd service were replaced by a
single Docker container, `mcpserver` (port 8800 on `fileserver`), and —
once all four harnesses were verified working through it alone — MCPHub
(container + image) and the old sidecar (systemd unit) were removed
outright, no rollback window kept, per explicit instruction.

No open work is seeded here. Next session: pull from CLAUDE.md / Cognee
Cloud recall for context, don't assume this file is behind — if it
describes something as in-progress, treat that as suspect and verify
live state first, the way this cycle's version of this file turned out to
already be stale by the time it was written.
