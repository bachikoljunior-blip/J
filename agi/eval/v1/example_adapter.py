"""Development-only adapter used to exercise the harness protocol."""
import json, sys

req = json.loads(sys.stdin.read())
prompt = req.get("prompt", "")
if "19*23" in prompt:
    out = {"answer": "437"}
elif "blip(11)" in prompt:
    out = {"answer": "25"}
else:
    out = {"answer": None}
json.dump(out, sys.stdout)
