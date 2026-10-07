---
name: parallel-executor
description: Enables multithreaded task and tool execution in Antigravity using uv and parallel_runner.py. Use when running batch commands, concurrent HTTP requests, or parallel data processing.
---

# Parallel Executor Skill for Antigravity

This skill grants Antigravity multithreaded batch processing capabilities across all CPU cores.

## Capabilities

1. **`uv` Package Runner**:
   - Fast execution using `~/.local/bin/uv run` for Python scripts without manual virtualenv management.

2. **Multithreaded Batch Commands**:
   - Execute a batch of shell commands concurrently:
     ```bash
     ~/.local/bin/uv run .agents/tools/parallel_runner.py commands tasks.json --workers 8
     ```
   - `tasks.json` format: `["cmd1", "cmd2", "cmd3"]`

3. **Multithreaded HTTP GET Fetching**:
   - Fetch multiple HTTP endpoints in parallel:
     ```bash
     ~/.local/bin/uv run .agents/tools/parallel_runner.py http urls.json --workers 8
     ```
   - `urls.json` format: `["http://...", "http://..."]`

4. **Multi-Agent Subagent Swarms**:
   - For complex tasks split across multiple domains, invoke parallel subagents via `invoke_subagent` with isolated git workspace branches (`Workspace: "branch"`).
