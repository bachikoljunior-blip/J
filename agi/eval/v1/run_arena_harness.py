"""Workspace-capable AGI evaluation runner.

Compared with run_harness.py, this runner gives the candidate a bounded writable
/work area while keeping pristine inputs read-only at /input. Private arena
checks run on the evaluator after candidate exit and are never mounted into the
candidate. Evaluator-owned autonomy telemetry is hash-chained into each record.

The current final transport deliberately supports network=none only. Tool-rich
or service-backed arenas require an evaluator-controlled network broker before
they are eligible for final AGI evidence.
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

from arena import candidate_mount_spec, grade_workspace, materialize_workspace, snapshot_workspace, validate_arena_grader
from autonomy import TelemetryLog, derive_autonomy_metrics
from eval_core import (
    append_hash_chain,
    load_jsonl,
    load_yaml,
    score_result,
    sha256_file,
    summarize_records,
    validate_manifest,
    validate_taskpacks,
)
from run_harness import load_lock, verify_lock

MAX_STREAM_BYTES = 2_000_000
MAX_MEMORY_MB = 64 * 1024
MAX_CPUS = 64.0


def _immutable_image_ref(image: str, candidate_digest: str) -> str:
    """Resolve to a local immutable image ID when possible, else an OCI digest ref."""
    try:
        inspected = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        local_id = inspected.stdout.strip() if inspected.returncode == 0 else ""
        if local_id and local_id == candidate_digest:
            return candidate_digest
    except Exception:
        pass
    if "@sha256:" in image:
        return image
    return f"{image}@{candidate_digest}"


def _resource_flags(public: dict) -> list[str]:
    budget = public.get("budget") or {}
    flags: list[str] = []
    if "memory_mb" in budget:
        memory_mb = int(budget["memory_mb"])
        if memory_mb <= 0 or memory_mb > MAX_MEMORY_MB:
            raise ValueError(f"memory_mb must be in [1,{MAX_MEMORY_MB}]")
        flags += ["--memory", f"{memory_mb}m"]
    if "cpus" in budget:
        cpus = float(budget["cpus"])
        if cpus <= 0 or cpus > MAX_CPUS:
            raise ValueError(f"cpus must be in (0,{MAX_CPUS}]")
        flags += ["--cpus", str(cpus)]
    return flags


def build_container_command(
    public: dict,
    adapter: list[str],
    candidate_digest: str,
    input_dir: Path,
    work_dir: Path,
) -> list[str]:
    if not adapter:
        raise ValueError("container adapter requires image name")
    network = str((public.get("arena") or {}).get("network", "none"))
    if network != "none":
        raise ValueError("v1 final arena permits only evaluator network policy 'none'")
    image_ref = _immutable_image_ref(adapter[0], candidate_digest)
    return [
        "docker",
        "run",
        "--rm",
        "-i",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        *_resource_flags(public),
        *candidate_mount_spec(input_dir, work_dir),
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        image_ref,
        *adapter[1:],
    ]


def _candidate_request(public: dict, *, final: bool) -> dict:
    request = {k: v for k, v in public.items() if k not in {"workspace_files"}}
    request["input_dir"] = "/input" if final else request.get("input_dir")
    request["work_dir"] = "/work" if final else request.get("work_dir")
    return request


def _run_candidate(public: dict, args, input_dir: Path, work_dir: Path) -> subprocess.CompletedProcess:
    timeout_s = min(max(int((public.get("budget") or {}).get("wall_s", args.timeout_s)), 1), args.timeout_s)
    final_transport = args.adapter_mode == "container"
    request = _candidate_request(public, final=final_transport)
    if final_transport:
        if shutil.which("docker") is None:
            raise RuntimeError("docker executable not available")
        cmd = build_container_command(public, args.adapter, args.candidate_digest, input_dir, work_dir)
        return subprocess.run(
            cmd,
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    env = {
        "PATH": os.environ.get("PATH", ""),
        "AGI_EVAL_MODE": "development",
        "AGI_INPUT_DIR": str(input_dir),
        "AGI_WORK_DIR": str(work_dir),
    }
    request["input_dir"] = str(input_dir)
    request["work_dir"] = str(work_dir)
    return subprocess.run(
        args.adapter,
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=work_dir,
        env=env,
        timeout=timeout_s,
        check=False,
    )


def run_one(public: dict, private: dict, args) -> dict:
    timeout_s = min(max(int((public.get("budget") or {}).get("wall_s", args.timeout_s)), 1), args.timeout_s)
    rec: dict[str, Any] = {
        "task_id": public["task_id"],
        "domain": public["domain"],
        "family": public["family"],
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "adapter_mode": args.adapter_mode,
        "timeout_s": timeout_s,
    }
    telemetry = TelemetryLog(str(public["task_id"]))
    telemetry.emit("episode_start")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="agi-arena-") as td:
        root = Path(td)
        input_dir, work_dir = root / "input", root / "work"
        try:
            materialize_workspace(public, input_dir, work_dir)
            grader_errors = validate_arena_grader(private)
            if grader_errors:
                raise ValueError("invalid private arena grader: " + "; ".join(grader_errors))
            telemetry.emit("candidate_start")
            proc = _run_candidate(public, args, input_dir, work_dir)
            telemetry.emit("candidate_exit", returncode=proc.returncode)
            stdout = proc.stdout[:MAX_STREAM_BYTES]
            stderr = proc.stderr[:MAX_STREAM_BYTES]
            rec.update({
                "returncode": proc.returncode,
                "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
                "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
                "stdout_truncated": len(proc.stdout) > MAX_STREAM_BYTES,
                "stderr_truncated": len(proc.stderr) > MAX_STREAM_BYTES,
                "isolation": ({
                    "network": "none",
                    "root": "read_only",
                    "input_mount": "read_only",
                    "work_mount": "read_write",
                    "capabilities": "dropped",
                    "no_new_privileges": True,
                } if args.adapter_mode == "container" else {"development_only": True}),
            })
            if proc.returncode != 0:
                raise RuntimeError(f"adapter return code {proc.returncode}")
            try:
                result = json.loads(stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError("adapter stdout is not valid JSON") from e
            snapshot = snapshot_workspace(work_dir)
            arena_pass, arena_evidence = grade_workspace(private, work_dir, snapshot)
            score, base_pass, grader_error = score_result(private, result)
            passed = base_pass and arena_pass and grader_error is None
            rec.update({
                "status": "ok" if grader_error is None else "grader_error",
                "score": score if arena_pass else 0.0,
                "passed": passed,
                "result": result,
                "workspace": snapshot,
                "arena_grader": arena_evidence,
            })
            if grader_error:
                rec["detail"] = grader_error
            telemetry.emit("episode_complete", success=passed)
        except subprocess.TimeoutExpired:
            telemetry.emit("candidate_exit", returncode=None, timeout=True)
            telemetry.emit("episode_complete", success=False)
            rec.update({"status": "timeout", "score": 0.0, "passed": False, "detail": "wall-clock timeout"})
        except Exception as e:
            telemetry.emit("episode_complete", success=False)
            rec.update({"status": "error", "score": 0.0, "passed": False, "detail": f"{type(e).__name__}: {e}"})
    rec["elapsed_s"] = time.monotonic() - started
    rec["autonomy_telemetry"] = telemetry.events
    rec["autonomy_telemetry_tip"] = telemetry.chain_tip
    rec["autonomy_metrics"] = derive_autonomy_metrics(telemetry.events)
    return rec


def aggregate_autonomy(records: list[dict]) -> dict:
    metrics = [r["autonomy_metrics"] for r in records]
    if not metrics:
        return {}
    total_faults = sum(m.get("fault_count", 0) for m in metrics)
    total_recoveries = sum(m.get("successful_recoveries", 0) for m in metrics)
    restore_attempts = sum(m.get("checkpoint_restore_attempts", 0) for m in metrics)
    restore_successes = sum(m.get("state_persistence_success", 1.0) * m.get("checkpoint_restore_attempts", 0) for m in metrics)
    return {
        "completion_rate": sum(m["completion_rate"] for m in metrics) / len(metrics),
        "intervention_count": sum(m["intervention_count"] for m in metrics),
        "recovery_rate": total_recoveries / total_faults if total_faults else 1.0,
        "elapsed_time": sum(m["elapsed_time"] for m in metrics),
        "resource_cost": sum(m["resource_cost"] for m in metrics),
        "policy_violations": sum(m["policy_violations"] for m in metrics),
        "state_persistence_success": restore_successes / restore_attempts if restore_attempts else 1.0,
        "fault_count": total_faults,
        "checkpoint_restore_attempts": restore_attempts,
        "autonomy_gate_assessed": False,
        "note": "Required metrics are evaluator-derived, but no autonomy pass is asserted until long-horizon fault/recovery tasks and thresholds are frozen.",
    }


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
    for row in private:
        errors += [f"private task {row.get('task_id')}: {e}" for e in validate_arena_grader(row)]
    try:
        lock = load_lock(args.lock)
        errors += verify_lock(lock, args)
    except Exception as e:
        errors.append(f"lock invalid: {e}")
    if final and args.adapter_mode != "container":
        errors.append("final evaluation requires isolated container adapter")
    if final and not args.candidate_digest.startswith("sha256:"):
        errors.append("final candidate digest must be immutable sha256 digest")
    if final and any(str((row.get("arena") or {}).get("network", "none")) != "none" for row in public):
        errors.append("v1 final arena permits only network=none until an evaluator-controlled broker is implemented")
    if errors:
        print(json.dumps({"started": False, "errors": errors}, ensure_ascii=False, sort_keys=True))
        return 3

    priv_by_id = {str(x["task_id"]): x for x in private}
    run = {
        "schema": "agi-eval-evidence-v1",
        "runner": "arena-v1",
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
    summary["autonomy_metrics"] = aggregate_autonomy(records)
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
