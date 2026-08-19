"""Evaluator-owned provider fixture. It uses a credential but never returns it."""
import json
import os
import sys
import urllib.request

request = json.load(sys.stdin)
if request.get("tool") != "secret.check":
    raise SystemExit("unsupported tool")
args = request.get("args") or {}
token = os.environ.get("AGI_EVAL_FIXTURE_TOKEN")
if not token:
    raise SystemExit("missing evaluator credential")
payload = json.dumps({"probe": args.get("probe")}).encode()
req = urllib.request.Request(
    "http://fixture-service:8080/check",
    data=payload,
    method="POST",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },
)
with urllib.request.urlopen(req, timeout=5) as response:
    service = json.load(response)
json.dump(
    {
        "credential_present": True,
        "external_service": service,
    },
    sys.stdout,
)
