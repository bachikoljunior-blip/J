"""Evaluator-owned provider fixture. It uses a credential but never returns it."""
import json
import os
import sys
import time
import urllib.error
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
service = None
last_error = None
for attempt in range(10):
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            service = json.load(response)
        break
    except (urllib.error.URLError, ConnectionError) as e:
        last_error = e
        if attempt == 9:
            raise
        time.sleep(0.2)
if service is None:
    raise RuntimeError(f"service unavailable: {type(last_error).__name__}")
json.dump(
    {
        "credential_present": True,
        "external_service": service,
    },
    sys.stdout,
)
