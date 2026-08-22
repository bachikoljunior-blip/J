#!/usr/bin/env python3
"""Replay and validate append-only AGI-GI run-start history.

Each start is checked against the canonical integration ancestry reachable
from its immutable starting SHA. A mismatch is accepted only when a single
explicit correction event binds the same run, SHA, timestamp, old revision,
derived revision, and evidence commit.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Callable, Iterable

try:
    from automation.agi_gi_run_start_record import (
        highest_integrated_revision,
        parse_jst,
    )
except ModuleNotFoundError:
    from agi_gi_run_start_record import highest_integrated_revision, parse_jst


class HistoryError(ValueError):
    pass


def parse_jsonl(lines: Iterable[str]) -> list[tuple[int, dict[str, object]]]:
    records = []
    for number, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HistoryError(f"line {number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise HistoryError(f"line {number}: record must be an object")
        records.append((number, value))
    return records


def validate_history(
    lines: Iterable[str],
    revision_resolver: Callable[[str], tuple[int, str] | None],
) -> dict[str, int]:
    records = parse_jsonl(lines)
    starts: dict[str, tuple[int, dict[str, object]]] = {}
    corrections: dict[str, tuple[int, dict[str, object]]] = {}

    for number, record in records:
        event = record.get("event_type")
        if event in ("automation_run_start_correction", "start_record_correction"):
            run_id = (
                record.get("correction_of_automation_run_id")
                if event == "automation_run_start_correction"
                else record.get("corrects_automation_run_id")
            )
            if not isinstance(run_id, str) or not run_id:
                raise HistoryError(f"line {number}: correction run id missing")
            if run_id in corrections:
                raise HistoryError(f"line {number}: duplicate correction for {run_id}")
            corrections[run_id] = (number, record)
            continue
        if event not in (None, "automation_run_start"):
            raise HistoryError(f"line {number}: unsupported event_type {event!r}")
        run_id = record.get("automation_run_id")
        if not isinstance(run_id, str) or not run_id:
            raise HistoryError(f"line {number}: automation_run_id missing")
        if run_id in starts:
            raise HistoryError(f"line {number}: duplicate start for {run_id}")
        starts[run_id] = (number, record)

    unknown = sorted(set(corrections) - set(starts))
    if unknown:
        raise HistoryError(f"correction references unknown run: {unknown[0]}")

    corrected = 0
    legacy_unverifiable = 0
    enforcement_seen = False
    for run_id, (number, start) in starts.items():
        sha = start.get("starting_main_sha")
        recorded_rev = start.get("starting_agi_gi_rev")
        timestamp = start.get("started_at_jst")
        if not isinstance(sha, str) or not isinstance(recorded_rev, int):
            raise HistoryError(f"line {number}: invalid SHA or revision")
        if not isinstance(timestamp, str):
            raise HistoryError(f"line {number}: started_at_jst missing")
        parse_jst(timestamp)
        source = start.get("start_rev_source")
        marker = (
            isinstance(start.get("integrated_revision_commit_sha"), str)
            or isinstance(source, str)
            and (
                "canonical_main_ancestry" in source
                or "derived_from_starting_main_ancestry" in source
            )
        )
        correction_item = corrections.get(run_id)
        if not (enforcement_seen or marker or correction_item is not None):
            legacy_unverifiable += 1
            continue
        enforcement_seen = enforcement_seen or marker
        resolution = revision_resolver(sha)
        if resolution is None:
            raise HistoryError(f"line {number}: no canonical revision after enforcement")
        derived_rev, evidence_sha = resolution
        if recorded_rev == derived_rev:
            if correction_item is not None:
                raise HistoryError(f"line {correction_item[0]}: unnecessary correction")
            continue
        if correction_item is None:
            raise HistoryError(
                f"line {number}: recorded rev{recorded_rev} != canonical rev{derived_rev}"
            )
        correction_number, correction = correction_item
        if correction.get("event_type") == "start_record_correction":
            checks = {
                "corrected_starting_agi_gi_rev": derived_rev,
                "evidence_commit_sha": evidence_sha,
                "evidence_relation": "ancestor_of_starting_main_sha",
                "preserves_original_record": True,
            }
        else:
            checks = {
                "starting_main_sha": sha,
                "started_at_jst": timestamp,
                "supersedes_starting_agi_gi_rev": recorded_rev,
                "starting_agi_gi_rev": derived_rev,
                "evidence_commit_sha": evidence_sha,
            }
        for key, expected in checks.items():
            if correction.get(key) != expected:
                raise HistoryError(
                    f"line {correction_number}: correction {key} does not bind start"
                )
        corrected += 1

    return {
        "records": len(records),
        "starts": len(starts),
        "corrections": len(corrections),
        "corrected_starts": corrected,
        "legacy_unverifiable_starts": legacy_unverifiable,
    }


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def git_revision_resolver(repo: Path) -> Callable[[str], tuple[int, str] | None]:
    def resolve(sha: str) -> tuple[int, str] | None:
        exact = _git(repo, "rev-parse", "--verify", f"{sha}^{{commit}}")
        if exact != sha:
            raise HistoryError(f"starting SHA did not resolve exactly: {sha}")
        lines = _git(repo, "log", "--format=%H%x09%s", exact).splitlines()
        try:
            item = highest_integrated_revision(lines)
        except ValueError as exc:
            if "no canonical AGI-GI integration" not in str(exc):
                raise
            return None
        return item.revision, item.commit_sha

    return resolve


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument(
        "--history", type=Path, default=Path("agi/run-history/STARTS.jsonl")
    )
    args = parser.parse_args()
    repo = args.repo.resolve()
    history = args.history if args.history.is_absolute() else repo / args.history
    summary = validate_history(
        history.read_text(encoding="utf-8").splitlines(),
        git_revision_resolver(repo),
    )
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
