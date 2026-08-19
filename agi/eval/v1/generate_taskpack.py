"""Generate fresh, sealed task packs from deterministic generator adapters.

Each trusted generator receives one JSON request on stdin and returns
{"public": {...}, "private": {"grader": {...}}}. The orchestrator injects
identity/domain/family and preregistered human thresholds, then writes physically
separate public/private packs plus provenance hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

import yaml

from eval_core import canonical_json, load_yaml, sha256_file, validate_taskpacks


def _command_file_hashes(command: list[str]) -> dict[str, str]:
    hashes = {}
    for token in command:
        p = Path(token)
        if p.is_file():
            hashes[str(p.resolve())] = sha256_file(p)
    return hashes


def _task_id(name: str, seed: str, public: dict) -> str:
    digest = hashlib.sha256((name + "\0" + seed + "\0" + canonical_json(public)).encode()).hexdigest()[:20]
    return f"{name}-{digest}"


def generate(spec: dict, timeout_s: int) -> tuple[list[dict], list[dict], dict]:
    if spec.get("schema") != "agi-taskgen-v1":
        raise ValueError("generator spec schema must be agi-taskgen-v1")
    public_rows = []
    private_rows = []
    invocations = []
    seen = set()
    for gen in spec.get("generators", []):
        name = str(gen["name"])
        domain = str(gen["domain"])
        family = str(gen["family"])
        threshold = float(gen["human_reference_lower_bound"])
        command = [str(x) for x in gen["command"]]
        if not command:
            raise ValueError(f"generator {name} has empty command")
        for raw_seed in gen.get("seeds", []):
            seed = str(raw_seed)
            request = {"schema": "agi-taskgen-request-v1", "name": name, "domain": domain, "family": family, "seed": seed}
            proc = subprocess.run(
                command,
                input=json.dumps(request),
                text=True,
                capture_output=True,
                timeout=timeout_s,
                check=False,
                env={"PATH": os.environ.get("PATH", "")},
            )
            if proc.returncode != 0:
                raise RuntimeError(f"generator {name}/{seed} failed rc={proc.returncode}: {proc.stderr[-1000:]}")
            try:
                out = json.loads(proc.stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"generator {name}/{seed} emitted invalid JSON") from e
            if not isinstance(out, dict) or not isinstance(out.get("public"), dict) or not isinstance(out.get("private"), dict):
                raise RuntimeError(f"generator {name}/{seed} must return public/private objects")
            pub = dict(out["public"])
            priv = dict(out["private"])
            tid = str(pub.pop("task_id", "") or _task_id(name, seed, pub))
            if tid in seen:
                raise ValueError(f"duplicate generated task_id {tid}")
            seen.add(tid)
            pub.update({"task_id": tid, "domain": domain, "family": family})
            priv.update({"task_id": tid, "human_reference_lower_bound": threshold, "seed": seed, "generator": name})
            public_rows.append(pub)
            private_rows.append(priv)
            invocations.append({"generator": name, "seed": seed, "task_id": tid})
    if not public_rows:
        raise ValueError("generator spec produced no tasks")
    provenance = {
        "schema": "agi-taskgen-provenance-v1",
        "spec_sha256": hashlib.sha256(canonical_json(spec).encode()).hexdigest(),
        "generators": [
            {
                "name": str(g["name"]),
                "command": [str(x) for x in g["command"]],
                "command_file_sha256": _command_file_hashes([str(x) for x in g["command"]]),
                "seeds_sha256": hashlib.sha256(canonical_json([str(s) for s in g.get("seeds", [])]).encode()).hexdigest(),
            }
            for g in spec.get("generators", [])
        ],
        "invocations": invocations,
    }
    return public_rows, private_rows, provenance


def _write_jsonl(path: str, rows: list[dict]) -> None:
    Path(path).write_text("".join(canonical_json(r) + "\n" for r in rows), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--spec", required=True)
    p.add_argument("--manifest")
    p.add_argument("--public-out", required=True)
    p.add_argument("--private-out", required=True)
    p.add_argument("--provenance-out", required=True)
    p.add_argument("--timeout-s", type=int, default=60)
    args = p.parse_args()
    spec = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8"))
    try:
        pub, priv, prov = generate(spec, args.timeout_s)
        if args.manifest:
            manifest = load_yaml(args.manifest)
            errors = validate_taskpacks(pub, priv, manifest, final=False)
            if errors:
                raise ValueError("generated pack invalid: " + "; ".join(errors))
        _write_jsonl(args.public_out, pub)
        _write_jsonl(args.private_out, priv)
        prov["public_pack_sha256"] = sha256_file(args.public_out)
        prov["private_pack_sha256"] = sha256_file(args.private_out)
        Path(args.provenance_out).write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"GENERATION FAILED: {e}")
        return 2
    print(json.dumps({"generated": len(pub), "public_sha256": prov["public_pack_sha256"], "private_sha256": prov["private_pack_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
