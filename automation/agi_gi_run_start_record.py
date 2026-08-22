#!/usr/bin/env python3
"""Build an append-only AGI-GI run-start record from Git ancestry.

``MAIN.md`` is intentionally not an input. It can briefly lag a merge.
The record binds the exact starting ref and derives its revision only from
reachable subjects using the integration-only ``AGI-GI revN:`` prefix.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

try:
    from automation.agi_gi_main_revision_guard import parse_integrated_revisions
except ModuleNotFoundError:
    from agi_gi_main_revision_guard import parse_integrated_revisions

JST = timezone(timedelta(hours=9))
SHA = re.compile(r"^[0-9a-f]{40}$")


def parse_jst(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() != JST.utcoffset(None):
        raise ValueError("started_at_jst must carry the +09:00 JST offset")
    return parsed.isoformat()


def highest_integrated_revision(log_lines: Iterable[str]):
    integrated = parse_integrated_revisions(log_lines)
    if not integrated:
        raise ValueError("starting main has no canonical AGI-GI integration commit")
    return max(integrated, key=lambda item: item.revision)


def build_run_start_record(
    *,
    started_at_jst: str,
    starting_main_sha: str,
    log_lines: Iterable[str],
    automation_run_id: str,
    invocation_kind: str = "scheduled_automation",
    automation_turn: int = 1,
    execution_surface: str = "chatgpt_work_mode_same_conversation",
    session_schedule_title: str = "AGI-GI実装継続",
) -> dict[str, object]:
    if SHA.fullmatch(starting_main_sha) is None:
        raise ValueError("starting_main_sha must be 40 lowercase hexadecimal characters")
    if not automation_run_id.strip():
        raise ValueError("automation_run_id must be non-empty")
    if isinstance(automation_turn, bool) or automation_turn < 1:
        raise ValueError("automation_turn must be a positive integer")
    integrated = highest_integrated_revision(log_lines)
    return {
        "started_at_jst": parse_jst(started_at_jst),
        "starting_main_sha": starting_main_sha,
        "starting_agi_gi_rev": integrated.revision,
        "automation_run_id": automation_run_id,
        "invocation_kind": invocation_kind,
        "automation_turn": automation_turn,
        "execution_surface": execution_surface,
        "start_rev_source": (
            f"main_commit_{integrated.commit_sha}_rev{integrated.revision};"
            "derived_from_starting_main_ancestry;MAIN.md_not_used"
        ),
        "integrated_revision_commit_sha": integrated.commit_sha,
        "session_schedule_title": session_schedule_title,
        "agi_state": "NOT_AGI",
    }


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--started-at-jst", required=True)
    parser.add_argument("--automation-run-id", required=True)
    parser.add_argument("--automation-turn", type=int, default=1)
    args = parser.parse_args()
    repo = args.repo.resolve()
    starting_main_sha = _git(repo, "rev-parse", "--verify", f"{args.ref}^{{commit}}")
    log_lines = _git(repo, "log", "--format=%H%x09%s", starting_main_sha).splitlines()
    record = build_run_start_record(
        started_at_jst=args.started_at_jst,
        starting_main_sha=starting_main_sha,
        log_lines=log_lines,
        automation_run_id=args.automation_run_id,
        automation_turn=args.automation_turn,
    )
    print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
