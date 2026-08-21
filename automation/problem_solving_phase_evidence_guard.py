#!/usr/bin/env python3
"""Require and replay phase-admission evidence for problem-state changes."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    from automation.parallel_claims import (
        ClaimFormatError,
        load_registry,
        parse_jst_timestamp,
        repo_path_is_within,
    )
    from automation.problem_solving_parallel_admission import (
        admit_problem_phase,
        validate_evidence_payload,
    )
except ModuleNotFoundError:  # Direct ``python automation/<script>.py`` invocation.
    from parallel_claims import (  # type: ignore[no-redef]
        ClaimFormatError,
        load_registry,
        parse_jst_timestamp,
        repo_path_is_within,
    )
    from problem_solving_parallel_admission import (  # type: ignore[no-redef]
        admit_problem_phase,
        validate_evidence_payload,
    )


EVIDENCE_PREFIX = "agi/run-history/phase-admissions/"


def is_problem_state_path(path: str) -> bool:
    if path == "MAIN.md" or path.startswith("automation_runs/"):
        return True
    if path.startswith("automation/"):
        return True
    if path.startswith("agi/") and not path.startswith("agi/run-history/"):
        return True
    if path.startswith(".github/workflows/rev") or path.startswith(
        ".github/workflows/agi-gi"
    ):
        return True
    return False


def path_is_covered(path: str, admitted_paths: list[str]) -> bool:
    try:
        return any(
            repo_path_is_within(path, admitted_path)
            for admitted_path in admitted_paths
        )
    except ClaimFormatError:
        return False


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _registry_at(repo: Path, commit_sha: str):
    paths = _git(
        repo,
        "ls-tree",
        "-r",
        "--name-only",
        commit_sha,
        "--",
        "agi/run-history/active",
    ).splitlines()
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        claim_dir = root / "agi" / "run-history" / "active"
        claim_dir.mkdir(parents=True)
        for source_path in paths:
            if source_path.endswith(".json"):
                (claim_dir / Path(source_path).name).write_text(
                    _git(repo, "show", f"{commit_sha}:{source_path}"),
                    encoding="utf-8",
                )
        return load_registry(root)


def replay_evidence(repo: Path, path: Path, head_ref: str) -> tuple[str, ...]:
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (f"{path}: invalid evidence JSON: {exc}",)

    errors = list(validate_evidence_payload(payload))
    source_sha = payload.get("registry_source_sha")
    if not isinstance(source_sha, str) or len(source_sha) != 40:
        return tuple(errors)
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_sha, head_ref], cwd=repo
    )
    if ancestor.returncode != 0:
        errors.append("registry_source_sha is not an ancestor of the proposed head")
        return tuple(errors)

    claims, registry_errors = _registry_at(repo, source_sha)
    errors.extend(registry_errors)
    owner = payload.get("own_claim")
    if registry_errors or not isinstance(owner, dict):
        return tuple(errors)
    recorded = parse_jst_timestamp(payload.get("recorded_at_jst"), "recorded_at_jst", path)
    replay = admit_problem_phase(
        claims,
        claim_id=str(owner.get("claim_id", "")),
        phase=str(payload.get("phase", "")),
        scope=str(payload.get("scope", "")),
        target_revision=payload.get("target_revision"),
        now=recorded,
        registry_source_sha=source_sha,
        paths=payload.get("paths", []),
    )
    for field in (
        "admitted",
        "mode",
        "scope",
        "target_revision",
        "paths",
        "registry_source_sha",
        "registry_digest",
        "own_claim",
        "parallel_active_claims",
        "conflicts",
        "reasons",
    ):
        if payload.get(field) != replay.get(field):
            errors.append(f"replayed {field} differs from persisted evidence")
    return tuple(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--changed-files", type=Path, required=True)
    parser.add_argument("--head-ref", default="HEAD")
    args = parser.parse_args()

    repo = args.repo.resolve()
    changed = [
        line.strip()
        for line in args.changed_files.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    relevant = [path for path in changed if is_problem_state_path(path)]
    evidence_paths = [
        repo / path
        for path in changed
        if path.startswith(EVIDENCE_PREFIX) and path.endswith(".json")
    ]
    errors: list[str] = []
    if relevant and not evidence_paths:
        errors.append("problem-state changes require a changed phase-admission evidence file")
    for evidence_path in evidence_paths:
        errors.extend(replay_evidence(repo, evidence_path, args.head_ref))
    admitted_paths: list[str] = []
    for evidence_path in evidence_paths:
        try:
            payload = json.loads(evidence_path.read_text(encoding="utf-8"))
            paths = payload.get("paths", [])
            if isinstance(paths, list):
                admitted_paths.extend(item for item in paths if isinstance(item, str))
        except (OSError, json.JSONDecodeError):
            continue
    for changed_path in relevant:
        if not path_is_covered(changed_path, admitted_paths):
            errors.append(f"changed problem-state path lacks admission coverage: {changed_path}")

    result = {
        "valid": not errors,
        "relevant_changed_files": relevant,
        "evidence_files": [path.relative_to(repo).as_posix() for path in evidence_paths],
        "admitted_paths": sorted(set(admitted_paths)),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
