"""Fail-closed AGI evaluation harness v1.

Final mode accepts only an isolated container adapter and a matching cryptographic
lock. Development command mode exists solely to test the protocol; it is never
eligible for an AGI claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval_core import (
    append_hash_chain,
    canonical_json,
    load_jsonl,
    load_yaml,
    score_result,
    sha256_bytes,
    sha256_file,
    summarize_records,
    validate_manifest,
    validate_taskpacks,
)

MAX_STREAM_BYTES = 2_000_000


def load_lock(path: str) -> dict:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("schema") != "agi-eval-lock-v1":
        raise ValueError("invalid lock schema")
    return obj


def verify_lock(lock: dict, args) -> list[str]:
    errors = []
    expected = {
        "manifest_sha256": sha256_file(args.manifest),
        "public_pack_sha256": sha256_file(args.public),
        "private_pack_sha256": sha256_file(args.private),
        "candidate_id": args.candidate_id,
        "candidate_digest": args.candidate_digest,
    }
    for k, v in expected.items():
        if lock.get(k) != v:
            errors.append(f"lock mismatch: {k}")
    payload = {k: v for k, v in lock.items() if k != "payload_sha256"}
    digest = sha256_bytes(canonical_json(payload).encode("utf-8"))
    if lock.get("payload_sha256") != digest:
        errors.append("lock payload hash invalid")
    if args.mode == "final" and lock.get("mode") != "final":
        errors.append("final run requires final lock")
    return errors


def _safe_rel_path(name: str) -> Path:
    p = Path(name)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe public file path: {name}")
    return p


def materialize_task(public: dict, task_dir: Path) -> None:
    files = public.get("public_files", {}) or {}
    if not isinstance(files, dict):
        raise ValueError("public_files must be a mapping")
    for name, content in files.items():
        rel = _safe_rel_path(str(name))
        dest = task_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not isinstance(content, str):
            raise ValueError(f"public file {name} content must be UTF-8 text")
        dest.write_text(content, encoding="utf-8")
    request = {k: v for k, v in public.items() if k != "public_files"}
    request["task_dir"] = "/task"
    (task_dir / "request.json").write_text(json.dumps(request, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _run_command(adapter: list[str], request: dict, task_dir: Path, timeout_s: int) -> subprocess.CompletedProcess:
    env = {"PATH": os.environ.get("PATH", ""), "AGI_EVAL_MODE": "development", "AGI_TASK_DIR": str(task_dir)}
    return subprocess.run(
        adapter,
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=task_dir,
        env=env,
        timeout=timeout_s,
        check=False,
    )


def _run_container(adapter: list[str], candidate_digest: str, request: dict, task_dir: Path, timeout_s: int) -> subprocess.CompletedProcess:
    if not adapter:
        raise ValueError("container adapter requires image name")
    if shutil.which("docker") is None:
        raise RuntimeError("docker executable not available")
    image = adapter[0]
    rest = adapter[1:]
    # Prefer a locally verified immutable image ID when available so air-gapped
    # final evaluation does not require a registry. Otherwise use an OCI digest.
    image_ref = None
    try:
        inspected = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image],
            text=True, capture_output=True, timeout=30, check=False,
        )
        local_id = inspected.stdout.strip() if inspected.returncode == 0 else ""
        if local_id and local_id == candidate_digest:
            image_ref = candidate_digest
    except Exception:
        image_ref = None
    if image_ref is None:
        if "@sha256:" in image:
            image_ref = image
        else:
            image_ref = f"{image}@{candidate_digest}"
    cmd = [
        "docker", "run", "--rm", "-i", "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "256",
        "--mount", f"type=bind,src={task_dir},dst=/task,readonly", image_ref, *rest,
    ]
    return subprocess.run(
        cmd,
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )


def run_one(public: dict, private: dict, args) -> dict:
    timeout_s = int((public.get("budget") or {}).get("wall_s", args.timeout_s))
    timeout_s = min(max(timeout_s, 1), args.timeout_s)
    request = {k: v for k, v in public.items() if k != "public_files"}
    started = time.monotonic()
    rec: dict[str, Any] = {
        "task_id": public["task_id"],
        "domain": public["domain"],
        "family": public["family"],
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "adapter_mode": args.adapter_mode,
        "timeout_s": timeout_s,
    }
    with tempfile.TemporaryDirectory(prefix="agi-eval-task-") as td:
        task_dir = Path(td)
        try:
            materialize_task(public, task_dir)
            if args.adapter_mode == "container":
                proc = _run_container(args.adapter, args.candidate_digest, request, task_dir, timeout_s)
                rec["isolation"] = {"network": "none", "root": "read_only", "task_mount": "read_only", "capabilities": "dropped"}
            else:
                proc = _run_command(args.adapter, request, task_dir, timeout_s)
                rec["isolation"] = {"development_only": True}
            stdout = proc.stdout[:MAX_STREAM_BYTES]
            stderr = proc.stderr[:MAX_STREAM_BYTES]
            rec.update({
                "returncode": proc.returncode,
                "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
                "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
                "stdout_truncated": len(proc.stdout) > MAX_STREAM_BYTES,
                "stderr_truncated": len(proc.stderr) > MAX_STREAM_BYTES,
            })
            if proc.returncode != 0:
                raise RuntimeError(f"adapter return code {proc.returncode}")
            try:
                result = json.loads(stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError("adapter stdout is not valid JSON") from e
            score, passed, grader_error = score_result(private, result)
            rec.update({"status": "ok" if grader_error is None else "grader_error", "score": score, "passed": passed, "result": result})
            if grader_error:
                rec["detail"] = grader_error
        except subprocess.TimeoutExpired:
            rec.update({"status": "timeout", "score": 0.0, "passed": False, "detail": "wall-clock timeout"})
        except Exception as e:
            rec.update({"status": "error", "score": 0.0, "passed": False, "detail": f"{type(e).__name__}: {e}"})
    rec["elapsed_s"] = time.monotonic() - started
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--public", required=True)
    p.add_argument("--private", required=True)
    p.add_argument("--lock", required=True)
    p.add_argument("--candidate-id", required=True)
    p.add_argument("--candidate-digest", required=True)
    p.add_argument("--adapter-mode", choices=["command", "container"], required=True)
    p.add_argument("--adapter", nargs="+", required=True)
    p.add_argument("--mode", choices=["development", "final"], default="development")
    p.add_argument("--timeout-s", type=int, default=300)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    manifest = load_yaml(args.manifest)
    public = load_jsonl(args.public)
    private = load_jsonl(args.private)
    final = args.mode == "final"
    errors = validate_manifest(manifest, final=final)
    errors += validate_taskpacks(public, private, manifest, final=final)
    try:
        lock = load_lock(args.lock)
        errors += verify_lock(lock, args)
    except Exception as e:
        errors.append(f"lock invalid: {e}")
    if final and args.adapter_mode != "container":
        errors.append("final evaluation requires isolated container adapter")
    if final and not args.candidate_digest.startswith("sha256:"):
        errors.append("final candidate digest must be immutable sha256 digest")
    if errors:
        print(json.dumps({"started": False, "errors": errors}, ensure_ascii=False, sort_keys=True))
        return 3

    priv_by_id = {str(x["task_id"]): x for x in private}
    run = {
        "schema": "agi-eval-evidence-v1",
        "mode": args.mode,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_id": args.candidate_id,
        "candidate_digest": args.candidate_digest,
        "manifest_sha256": sha256_file(args.manifest),
        "public_pack_sha256": sha256_file(args.public),
        "private_pack_sha256": sha256_file(args.private),
        "lock_sha256": sha256_file(args.lock),
        "harness_version": 1,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "adapter_mode": args.adapter_mode,
    }
    records = [run_one(pub, priv_by_id[str(pub["task_id"])], args) for pub in public]
    chain_tip = append_hash_chain(records)
    summary = summarize_records(records, private, manifest)
    summary["total_tasks"] = len(records)
    summary["passed_tasks"] = sum(1 for r in records if r.get("passed") is True)
    summary["failed_tasks"] = len(records) - summary["passed_tasks"]
    artifact = {"run": run, "records": records, "record_hash_chain_tip": chain_tip, "summary": summary}
    artifact["run"]["finished_utc"] = datetime.now(timezone.utc).isoformat()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact_sha = sha256_file(out)
    Path(str(out) + ".sha256").write_text(artifact_sha + "  " + out.name + "\n", encoding="utf-8")
    print(json.dumps({"completed": True, "tasks": len(records), "passed": summary["passed_tasks"], "artifact_sha256": artifact_sha}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
