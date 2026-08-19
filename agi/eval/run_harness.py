"""Versioned evaluation harness for frozen AGI candidates.

This runner does not assert AGI. It executes held-out tasks through an external
candidate adapter, records immutable evidence, and fails closed on malformed
results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

REQUIRED_TASK_FIELDS = {"task_id", "domain", "prompt", "metric", "threshold"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_tasks(path: Path) -> list[dict]:
    tasks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not tasks:
        raise ValueError("task set is empty")
    seen = set()
    for i, task in enumerate(tasks):
        missing = REQUIRED_TASK_FIELDS - task.keys()
        if missing:
            raise ValueError(f"task[{i}] missing fields: {sorted(missing)}")
        if task["task_id"] in seen:
            raise ValueError(f"duplicate task_id: {task['task_id']}")
        seen.add(task["task_id"])
    return tasks


def score(task: dict, result: dict) -> tuple[float, bool]:
    metric = task["metric"]
    threshold = float(task["threshold"])
    if metric == "exact_match":
        value = 1.0 if result.get("answer") == task.get("expected_answer") else 0.0
    elif metric == "numeric":
        value = float(result.get("score", float("nan")))
    else:
        raise ValueError(f"unsupported metric: {metric}")
    return value, value >= threshold


def run_task(adapter_cmd: list[str], task: dict, timeout_s: int) -> dict:
    payload = json.dumps({"task_id": task["task_id"], "prompt": task["prompt"]})
    started = time.time()
    proc = subprocess.run(
        adapter_cmd,
        input=payload,
        text=True,
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )
    elapsed = time.time() - started
    if proc.returncode != 0:
        raise RuntimeError(f"adapter failed rc={proc.returncode}: {proc.stderr[-1000:]}")
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError("adapter output is not valid JSON") from e
    if not isinstance(result, dict):
        raise RuntimeError("adapter output must be a JSON object")
    result["elapsed_s"] = elapsed
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tasks", required=True)
    p.add_argument("--candidate-id", required=True)
    p.add_argument("--adapter", nargs="+", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--timeout-s", type=int, default=300)
    args = p.parse_args()

    task_path = Path(args.tasks)
    out_path = Path(args.out)
    tasks = load_tasks(task_path)
    run_meta = {
        "candidate_id": args.candidate_id,
        "task_set": str(task_path),
        "task_set_sha256": sha256_file(task_path),
        "started_unix": time.time(),
        "harness_version": 0,
    }

    records = []
    for task in tasks:
        record = {"task_id": task["task_id"], "domain": task["domain"]}
        try:
            result = run_task(args.adapter, task, args.timeout_s)
            value, passed = score(task, result)
            record.update({"status": "ok", "score": value, "passed": passed, "result": result})
        except Exception as e:
            record.update({"status": "error", "passed": False, "error": type(e).__name__, "detail": str(e)})
        records.append(record)

    summary = {
        "total": len(records),
        "passed": sum(1 for r in records if r["passed"]),
        "failed": sum(1 for r in records if not r["passed"]),
        "all_passed": all(r["passed"] for r in records),
    }
    artifact = {"run": run_meta, "records": records, "summary": summary}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["all_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
