"""Workspace AGI evaluator with an evaluator-owned Unix broker and isolated providers.

This runner is an evaluation mechanism, not an AGI candidate. Candidate containers
retain IP network=none. A read-only bind mount exposes only an AF_UNIX broker
socket. Broker allowlists/budgets come from the public task, while optional
external-service provider image/network/credential configuration stays in the
sealed private task row. Providers run in separate evaluator-owned containers.
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
from broker import BUILTINS, BrokerPolicy, BrokerServer
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
from provider import load_container_providers
from run_arena_harness import aggregate_autonomy
from run_harness import load_lock, verify_lock

MAX_STREAM_BYTES = 2_000_000
MAX_MEMORY_MB = 64 * 1024
MAX_CPUS = 64.0


def _immutable_image_ref(image: str, candidate_digest: str) -> str:
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


def _broker_runtime(public: dict, private: dict) -> tuple[dict, BrokerPolicy]:
    providers = load_container_providers(private)
    policy = BrokerPolicy.from_public(public.get("arena") or {}, extra_tools=set(providers))
    if not policy.allowed_tools:
        raise ValueError("broker arena requires at least one allowlisted broker tool")
    provider_tools = policy.allowed_tools - set(BUILTINS)
    missing = provider_tools - set(providers)
    if missing:
        raise ValueError(f"broker provider handlers missing: {sorted(missing)}")
    return providers, policy


def build_container_command(
    public: dict,
    adapter: list[str],
    candidate_digest: str,
    input_dir: Path,
    work_dir: Path,
    broker_dir: Path,
) -> list[str]:
    if not adapter:
        raise ValueError("container adapter requires image name")
    network = str((public.get("arena") or {}).get("network", "none"))
    if network != "none":
        raise ValueError("broker arena candidate permits only evaluator network policy 'none'")
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
        "--mount",
        f"type=bind,src={broker_dir.resolve()},dst=/broker,readonly",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        image_ref,
        *adapter[1:],
    ]


def _candidate_request(public: dict, *, final: bool, broker_socket: Path) -> dict:
    request = {k: v for k, v in public.items() if k not in {"workspace_files"}}
    request["input_dir"] = "/input" if final else request.get("input_dir")
    request["work_dir"] = "/work" if final else request.get("work_dir")
    request["broker_socket"] = "/broker/broker.sock" if final else str(broker_socket)
    return request


def _run_candidate(public: dict, args, input_dir: Path, work_dir: Path, broker_dir: Path, broker_socket: Path) -> subprocess.CompletedProcess:
    timeout_s = min(max(int((public.get("budget") or {}).get("wall_s", args.timeout_s)), 1), args.timeout_s)
    final_transport = args.adapter_mode == "container"
    request = _candidate_request(public, final=final_transport, broker_socket=broker_socket)
    if final_transport:
        if shutil.which("docker") is None:
            raise RuntimeError("docker executable not available")
        cmd = build_container_command(public, args.adapter, args.candidate_digest, input_dir, work_dir, broker_dir)
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
        "AGI_BROKER_SOCKET": str(broker_socket),
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


def _broker_summary(events: list[dict], provider_count: int) -> dict[str, Any]:
    return {
        "transport": "AF_UNIX",
        "candidate_ip_network": "none",
        "provider_isolation": "separate_evaluator_owned_containers",
        "provider_count": provider_count,
        "requests": len(events),
        "policy_violations": sum(1 for e in events if e.get("violation") is True),
        "resource_cost": sum(float(e.get("cost", 0.0)) for e in events),
        "events": events,
    }


def _emit_broker_telemetry(telemetry: TelemetryLog, events: list[dict]) -> None:
    for event in events:
        if event.get("violation") is True:
            telemetry.emit(
                "policy_violation",
                source="broker",
                tool=event.get("tool"),
                request_id=event.get("request_id"),
                exchange_sha256=event.get("exchange_sha256"),
            )
        cost = float(event.get("cost", 0.0))
        if cost > 0:
            telemetry.emit(
                "resource_charge",
                source="broker",
                tool=event.get("tool"),
                amount=cost,
                exchange_sha256=event.get("exchange_sha256"),
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
    broker_events: list[dict] = []
    provider_count = 0
    with tempfile.TemporaryDirectory(prefix="agi-broker-arena-") as td:
        root = Path(td)
        input_dir, work_dir, broker_dir = root / "input", root / "work", root / "broker"
        broker_socket = broker_dir / "broker.sock"
        try:
            materialize_workspace(public, input_dir, work_dir)
            grader_errors = validate_arena_grader(private)
            if grader_errors:
                raise ValueError("invalid private arena grader: " + "; ".join(grader_errors))
            providers, policy = _broker_runtime(public, private)
            provider_count = len(providers)
            handlers = {name: provider.call for name, provider in providers.items()}
            with BrokerServer(broker_socket, policy, handlers=handlers) as broker:
                telemetry.emit("candidate_start")
                proc = _run_candidate(public, args, input_dir, work_dir, broker_dir, broker_socket)
                telemetry.emit("candidate_exit", returncode=proc.returncode)
                broker_events = [dict(e) for e in broker.events]
            _emit_broker_telemetry(telemetry, broker_events)
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
                    "broker_mount": "read_only",
                    "broker_transport": "AF_UNIX",
                    "capabilities": "dropped",
                    "no_new_privileges": True,
                } if args.adapter_mode == "container" else {"development_only": True}),
                "broker": _broker_summary(broker_events, provider_count),
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
            _emit_broker_telemetry(telemetry, broker_events)
            telemetry.emit("episode_complete", success=False)
            rec.update({
                "status": "timeout",
                "score": 0.0,
                "passed": False,
                "detail": "wall-clock timeout",
                "broker": _broker_summary(broker_events, provider_count),
            })
        except Exception as e:
            _emit_broker_telemetry(telemetry, broker_events)
            telemetry.emit("episode_complete", success=False)
            rec.update({
                "status": "error",
                "score": 0.0,
                "passed": False,
                "detail": f"{type(e).__name__}: {e}",
                "broker": _broker_summary(broker_events, provider_count),
            })
    rec["elapsed_s"] = time.monotonic() - started
    rec["autonomy_telemetry"] = telemetry.events
    rec["autonomy_telemetry_tip"] = telemetry.chain_tip
    rec["autonomy_metrics"] = derive_autonomy_metrics(telemetry.events)
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
    priv_by_id = {str(x.get("task_id")): x for x in private if "task_id" in x}
    for row in private:
        errors += [f"private task {row.get('task_id')}: {e}" for e in validate_arena_grader(row)]
    for pub in public:
        tid = str(pub.get("task_id"))
        priv = priv_by_id.get(tid)
        if priv is None:
            continue
        try:
            _broker_runtime(pub, priv)
        except Exception as e:
            errors.append(f"broker task {tid}: {type(e).__name__}: {e}")
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
        errors.append("broker arena final evaluation requires candidate network=none")
    if errors:
        print(json.dumps({"started": False, "errors": errors}, ensure_ascii=False, sort_keys=True))
        return 3

    run = {
        "schema": "agi-eval-evidence-v1",
        "runner": "arena-v1",
        "transport": "broker-provider-v1",
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
