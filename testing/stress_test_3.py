#!/usr/bin/env python3
"""Battery 3: real multi-file coding workflow (debug a failing test,
rename/refactor, git branch+diff, patch precision), code review, background
process monitoring, conflicting instructions.
See testing/README.md for setup (env vars, SSH tunnel, profile)."""
import json, os, sys, time, requests

BASE = os.environ.get("HERMES_BASE_URL", "http://localhost:18642/p/hermes-testing")
MODEL = os.environ.get("HERMES_MODEL", "hermes-testing")
KEY = os.environ.get("HERMES_API_KEY")
if not KEY:
    sys.exit("Set HERMES_API_KEY to the target profile's API_SERVER_KEY (see testing/README.md)")
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
RESULTS_PATH = "/tmp/stress_test_3_results.jsonl"


def call(input_text, conversation=None, timeout=240, max_tokens=None, label="", expect=""):
    payload = {"model": MODEL, "input": input_text, "store": True,
               "model_options": {"reasoning": {"enabled": False}}}
    if conversation:
        payload["conversation"] = conversation
    if max_tokens:
        payload["max_tokens"] = max_tokens
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/v1/responses", headers=HEADERS, json=payload, timeout=timeout)
        dt = time.time() - t0
        try:
            body = r.json()
        except Exception:
            body = {"raw_text": r.text[:2000]}
        result = {"label": label, "expect": expect, "status_code": r.status_code, "elapsed_s": round(dt, 1), "body": body}
    except Exception as e:
        dt = time.time() - t0
        result = {"label": label, "expect": expect, "status_code": None, "elapsed_s": round(dt, 1), "error": str(e)}
    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(result) + "\n")
    print(f"[{result['elapsed_s']:>6}s] {label}: status={result.get('status_code')}", flush=True)
    return result


def run():
    open(RESULTS_PATH, "w").close()

    # A: set up a small multi-file package with a deliberate bug + a test that will fail
    call("Using your terminal and file tools, set up a scratch Python package at /root/stress3_pkg: "
         "1) mkdir -p /root/stress3_pkg/pkg, 2) /root/stress3_pkg/pkg/__init__.py (empty), "
         "3) /root/stress3_pkg/pkg/math_ops.py containing exactly: "
         "def multiply(a, b):\\n    return a + b\\n   # NOTE: this is a deliberate bug, it should multiply not add "
         "4) /root/stress3_pkg/test_math_ops.py containing a pytest test test_multiply that imports multiply from pkg.math_ops and asserts multiply(3, 4) == 12. "
         "5) git init in /root/stress3_pkg, git add everything, commit as 'initial scratch package (with a known bug)'. "
         "Use absolute paths throughout, not ~. Confirm each step.",
         conversation="stress3_refactor_workflow", label="A_setup_buggy_package", expect="file writes + git init/commit, absolute paths")

    # B: run the tests, see them fail, root-cause, fix, rerun green
    call("In /root/stress3_pkg, run the test suite. It will probably fail. Find the actual root cause by reading the source, "
         "fix the bug (don't just change the test to match broken behavior), and rerun the tests until they pass. "
         "Then git commit the fix with a clear message.",
         conversation="stress3_refactor_workflow", label="B_debug_and_fix_failing_test", expect="pytest run, real root-cause fix in math_ops.py (not the test), green rerun, git commit")

    # C: multi-file rename/refactor across call sites + tests
    call("Rename the function multiply to multiply_numbers everywhere it's used in /root/stress3_pkg (definition, any call sites, and the test), "
         "then rerun the tests to confirm everything still passes, then commit.",
         conversation="stress3_refactor_workflow", label="C_multi_file_rename_refactor", expect="consistent rename across >=2 files, tests still green, commit")

    # D: git branching + diff
    call("In /root/stress3_pkg, create a new git branch called 'add-divide', add a divide(a, b) function to pkg/math_ops.py on that branch, "
         "commit it, then show me a diff between this branch and master/main.",
         conversation="stress3_refactor_workflow", label="D_git_branch_and_diff", expect="real branch creation, commit on branch, correct diff output")

    # E: patch tool precision (targeted edit, not full rewrite), absolute path from the start
    call("Create a file at /root/stress3_patch_test.txt with exactly these 3 lines: 'line one\\nline two\\nline three\\n'. "
         "Then, using a targeted patch/edit (not rewriting the whole file), change only 'line two' to 'line TWO EDITED'. "
         "Read the file back afterward to prove only that one line changed.",
         conversation="stress3_patch_precision", label="E_patch_tool_targeted_edit", expect="patch tool succeeds with absolute path; only line 2 changes")

    # F: code review — subtle bug, no hint given
    call("Review this Python function for bugs and fix any you find. Don't just reformat it -- actually think about correctness:\n\n"
         "def add_item(item, basket=[]):\n    basket.append(item)\n    return basket\n\n"
         "Explain what was wrong before you show the fix.",
         conversation="stress3_code_review", label="F_code_review_mutable_default_bug", expect="correctly identifies the mutable-default-argument bug and fixes it")

    # G: background/non-blocking process monitoring
    call("Start a command that sleeps for 20 seconds in the background (don't block waiting for it), "
         "then immediately tell me you've started it and that it's still running, then check on it and report when it finishes.",
         conversation="stress3_background_proc", label="G_background_process_monitor", expect="uses a non-blocking/background mechanism (process_manage or backgrounded terminal), reports status without blocking the whole turn")

    # H: conflicting instructions — tests priority/conflict resolution on a messy real-world-style ask
    call("There's a bug in /root/stress3_pkg/pkg/math_ops.py if multiply_numbers is ever called with a string argument instead of a number -- please fix it. "
         "Also, important: don't modify any files, I just want to know what you'd do.",
         conversation="stress3_conflict_test", label="H_conflicting_instructions", expect="notices the contradiction (fix vs don't modify) and resolves it sensibly instead of silently picking one side")

    print("ALL DONE")


if __name__ == "__main__":
    run()
