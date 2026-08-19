"""Toy sealed-bank generator used only for container transport/qualification CI."""
import json
import os
import sys

req = json.load(sys.stdin)
if req.get("schema") != "agi-taskgen-request-v1":
    raise SystemExit("bad protocol")
lineage = os.environ.get("BANK_LINEAGE", "unknown")
domain = str(req.get("domain", ""))
family = str(req.get("family", ""))
seed = str(req.get("seed", ""))
nonce = str(req.get("nonce", ""))
if not domain or not family or not seed.startswith("__qualification__:") or len(nonce) < 8:
    raise SystemExit("bad qualification request")
marker = f"CI_SEALED_RAW::{lineage}::{domain}::{family}::{seed}"
json.dump(
    {
        "public": {
            "prompt": marker,
            "budget": {"wall_s": 5},
        },
        "private": {
            "grader": {"type": "boolean", "expected": True},
            "ci_private_marker": marker,
        },
    },
    sys.stdout,
)
