#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script, payload):
    p = subprocess.run([sys.executable, str(ROOT / ".agents" / "scripts" / script)], input=json.dumps(payload), text=True, capture_output=True)
    if p.returncode != 0:
        raise AssertionError(f"{script} exited {p.returncode}: {p.stderr}")
    return json.loads(p.stdout)


def main():
    common = {"conversationId":"t", "workspacePaths":[str(ROOT)], "transcriptPath":"x", "artifactDirectoryPath":"x", "modelName":"gemini-3.8-flash-high"}
    # Safe file write.
    x = run("hook_pretool_guard.py", common | {"toolCall":{"name":"write_to_file","args":{"TargetFile":str(ROOT / "tmp-safe.txt")}}})
    assert x["decision"] == "allow", x
    # Secret read denied.
    x = run("hook_pretool_guard.py", common | {"toolCall":{"name":"view_file","args":{"AbsolutePath":str(ROOT / ".env")}}})
    assert x["decision"] == "deny", x
    # Destructive Git asks.
    x = run("hook_pretool_guard.py", common | {"toolCall":{"name":"run_command","args":{"CommandLine":"git reset --hard HEAD~1","Cwd":str(ROOT)}}})
    assert x["decision"] == "force_ask", x
    # Correct model accepted; downgrade terminated.
    x = run("hook_model_guard.py", common | {"invocationNum":0,"initialNumSteps":0})
    assert x.get("terminationBehavior", "") == "", x
    y = run("hook_model_guard.py", (common | {"modelName":"gemini-3.8-flash-medium", "invocationNum":0,"initialNumSteps":0}))
    assert y["terminationBehavior"] == "terminate", y
    # Stop guard continues active work once.
    x = run("hook_stop_guard.py", common | {"fullyIdle":False,"executionNum":0,"terminationReason":"model_stop"})
    assert x["decision"] == "continue", x
    y = run("hook_stop_guard.py", common | {"fullyIdle":True,"executionNum":0,"terminationReason":"model_stop"})
    assert y["decision"] == "allow", y
    print("PASS: hook self-tests")

if __name__ == "__main__":
    main()
