#!/usr/bin/env python3
"""Fail closed when MAIN.md lags a canonically integrated AGI-GI revision.

Parallel AGI-GI branches may merge out of numeric order.  This guard derives
the continuation point only from commits reachable from the requested ref and
whose subjects use the integration-only ``AGI-GI revN:`` prefix.  Incidental
branch commits, claims, PR descriptions, and unmerged refs cannot advance it.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


INTEGRATION_SUBJECT = re.compile(r"^AGI-GI rev(?P<revision>[1-9][0-9]*):(?:\s|$)")
MAIN_CONTINUATION = re.compile(
    r"^現在の統合済み継続点は \*\*AGI-GI rev(?P<revision>[1-9][0-9]*)\*\*。",
    re.MULTILINE,
)


@dataclass(frozen=True)
class IntegratedRevision:
    revision: int
    commit_sha: str
    subject: str


@dataclass(frozen=True)
class RevisionAudit:
    valid: bool
    declared_revision: int | None
    latest_integrated_revision: int | None
    latest_integrated_commit: str | None
    errors: tuple[str, ...]


def parse_integrated_revisions(lines: Iterable[str]) -> tuple[IntegratedRevision, ...]:
    """Parse ``<sha> TAB <subject>`` records from a reachable git log."""

    parsed: list[IntegratedRevision] = []
    for raw in lines:
        line = raw.rstrip("\n")
        if "\t" not in line:
            continue
        sha, subject = line.split("\t", 1)
        match = INTEGRATION_SUBJECT.match(subject)
        if match is None:
            continue
        parsed.append(
            IntegratedRevision(
                revision=int(match.group("revision")),
                commit_sha=sha,
                subject=subject,
            )
        )
    return tuple(parsed)


def parse_main_continuation(main_text: str) -> int | None:
    match = MAIN_CONTINUATION.search(main_text)
    return None if match is None else int(match.group("revision"))


def audit_revision_state(log_lines: Iterable[str], main_text: str) -> RevisionAudit:
    integrated = parse_integrated_revisions(log_lines)
    declared = parse_main_continuation(main_text)
    errors: list[str] = []

    latest = max(integrated, key=lambda item: item.revision, default=None)
    if latest is None:
        errors.append("no canonical AGI-GI integration commit is reachable")
    if declared is None:
        errors.append("MAIN.md has no canonical integrated-continuation declaration")
    if latest is not None and declared is not None and declared != latest.revision:
        errors.append(
            "MAIN.md declares rev"
            f"{declared}, but the highest canonically integrated revision is "
            f"rev{latest.revision} at {latest.commit_sha}"
        )

    return RevisionAudit(
        valid=not errors,
        declared_revision=declared,
        latest_integrated_revision=None if latest is None else latest.revision,
        latest_integrated_commit=None if latest is None else latest.commit_sha,
        errors=tuple(errors),
    )


def _reachable_log(repo: Path, ref: str) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "log", "--format=%H%x09%s", ref],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(completed.stdout.splitlines())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--main-file", default="MAIN.md")
    args = parser.parse_args()

    repo = args.repo.resolve()
    audit = audit_revision_state(
        _reachable_log(repo, args.ref),
        (repo / args.main_file).read_text(encoding="utf-8"),
    )
    print(json.dumps(asdict(audit), ensure_ascii=False, indent=2))
    return 0 if audit.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
