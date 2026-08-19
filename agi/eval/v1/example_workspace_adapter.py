"""Development-only adapter for the writable-workspace arena protocol."""
import json
import os
import sys
from pathlib import Path

req = json.loads(sys.stdin.read())
work = Path(os.environ.get("AGI_WORK_DIR") or req["work_dir"])
(work / "result.json").write_text(json.dumps({"status": "ok", "value": 7}, sort_keys=True), encoding="utf-8")
json.dump({"answer": "done"}, sys.stdout)
