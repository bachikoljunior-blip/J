"""Evaluator-controlled workspace arena primitives.

This module never executes candidate-authored code on the host. It materializes
candidate-visible workspaces, snapshots resulting artifacts without following
symlinks, and applies data-only private checks. Containerized semantic graders
can be layered on later without exposing their secrets to the candidate.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

DEFAULT_MAX_FILES = 10_000
DEFAULT_MAX_BYTES = 256 * 1024 * 1024


def safe_relative_path(name: str) -> Path:
    p = Path(name)
    if not name or p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe relative path: {name!r}")
    return p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def materialize_workspace(public: dict, input_dir: Path, work_dir: Path) -> None:
    """Create immutable input and mutable work copies from candidate-visible files."""
    files = public.get("workspace_files", {}) or {}
    if not isinstance(files, dict):
        raise ValueError("workspace_files must be a mapping")
    input_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        rel = safe_relative_path(str(name))
        if not isinstance(content, str):
            raise ValueError(f"workspace file {name} must be UTF-8 text")
        src = input_dir / rel
        dst = work_dir / rel
        src.parent.mkdir(parents=True, exist_ok=True)
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(content, encoding="utf-8")
        dst.write_text(content, encoding="utf-8")
    # Candidate may read the pristine copy, but host-side permission bits are
    # not relied upon for security; final Docker mounts must also be read-only.
    for root, dirs, files_ in os.walk(input_dir):
        for name in files_:
            os.chmod(Path(root) / name, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        for name in dirs:
            os.chmod(Path(root) / name, stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


def snapshot_workspace(
    work_dir: Path,
    *,
    max_files: int = DEFAULT_MAX_FILES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    """Return a bounded deterministic manifest without following symlinks."""
    entries: list[dict[str, Any]] = []
    total_bytes = 0
    for root, dirs, files in os.walk(work_dir, followlinks=False):
        rootp = Path(root)
        for name in list(dirs):
            p = rootp / name
            if p.is_symlink():
                raise ValueError(f"workspace contains symlink directory: {p.relative_to(work_dir)}")
        for name in files:
            p = rootp / name
            rel = p.relative_to(work_dir).as_posix()
            st = p.lstat()
            if stat.S_ISLNK(st.st_mode):
                raise ValueError(f"workspace contains symlink: {rel}")
            if not stat.S_ISREG(st.st_mode):
                raise ValueError(f"workspace contains non-regular file: {rel}")
            total_bytes += st.st_size
            if total_bytes > max_bytes:
                raise ValueError("workspace exceeds byte limit")
            entries.append({"path": rel, "size": st.st_size, "sha256": sha256_file(p)})
            if len(entries) > max_files:
                raise ValueError("workspace exceeds file-count limit")
    entries.sort(key=lambda x: x["path"])
    manifest_json = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return {
        "files": entries,
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "tree_sha256": hashlib.sha256(manifest_json.encode("utf-8")).hexdigest(),
    }


def validate_arena_grader(private_row: dict) -> list[str]:
    grader = private_row.get("arena_grader")
    if grader is None:
        return []
    if not isinstance(grader, dict):
        return ["arena_grader must be a mapping"]
    typ = grader.get("type")
    errors: list[str] = []
    if typ == "file_sha256":
        files = grader.get("files")
        if not isinstance(files, dict) or not files:
            errors.append("file_sha256 grader needs non-empty files mapping")
        else:
            for name, digest in files.items():
                try:
                    safe_relative_path(str(name))
                except ValueError as e:
                    errors.append(str(e))
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
                    errors.append(f"invalid sha256 for {name}")
    elif typ == "json_equal":
        try:
            safe_relative_path(str(grader.get("path", "")))
        except ValueError as e:
            errors.append(str(e))
        if "expected" not in grader:
            errors.append("json_equal grader needs expected value")
    elif typ == "tree_sha256":
        digest = grader.get("expected")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append("tree_sha256 grader needs 64-char expected digest")
    else:
        errors.append(f"unsupported arena_grader type: {typ}")
    return errors


def grade_workspace(private_row: dict, work_dir: Path, snapshot: dict | None = None) -> tuple[bool, dict]:
    """Apply a trusted, data-only grader to workspace artifacts."""
    grader = private_row.get("arena_grader")
    if grader is None:
        return True, {"type": None, "passed": True}
    errors = validate_arena_grader(private_row)
    if errors:
        return False, {"type": grader.get("type") if isinstance(grader, dict) else None, "passed": False, "errors": errors}
    snapshot = snapshot or snapshot_workspace(work_dir)
    typ = grader["type"]
    file_map = {row["path"]: row for row in snapshot["files"]}
    if typ == "file_sha256":
        checks = []
        for name, expected in sorted(grader["files"].items()):
            actual = file_map.get(name, {}).get("sha256")
            checks.append({"path": name, "expected_sha256": expected, "actual_sha256": actual, "passed": actual == expected})
        if grader.get("allow_extra_files") is False:
            expected_paths = set(grader["files"])
            extra = sorted(set(file_map) - expected_paths)
        else:
            extra = []
        passed = all(c["passed"] for c in checks) and not extra
        return passed, {"type": typ, "passed": passed, "checks": checks, "extra_files": extra}
    if typ == "json_equal":
        rel = safe_relative_path(str(grader["path"]))
        path = work_dir / rel
        try:
            actual = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            return False, {"type": typ, "passed": False, "error": f"{type(e).__name__}: {e}"}
        passed = actual == grader["expected"]
        return passed, {"type": typ, "passed": passed, "path": rel.as_posix(), "actual_sha256": sha256_file(path)}
    if typ == "tree_sha256":
        passed = snapshot["tree_sha256"] == grader["expected"]
        return passed, {"type": typ, "passed": passed, "actual": snapshot["tree_sha256"], "expected": grader["expected"]}
    return False, {"type": typ, "passed": False, "error": "unreachable unsupported grader"}


def candidate_mount_spec(input_dir: Path, work_dir: Path) -> list[str]:
    """Docker CLI mount arguments for final isolated workspace tasks."""
    return [
        "--mount", f"type=bind,src={input_dir.resolve()},dst=/input,readonly",
        "--mount", f"type=bind,src={work_dir.resolve()},dst=/work",
    ]
