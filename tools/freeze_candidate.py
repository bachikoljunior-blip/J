from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def candidate_files(root: Path) -> tuple[Path, ...]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        files.append(path)
    return tuple(sorted(files, key=lambda p: p.relative_to(root).as_posix()))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bundle_sha256(entries: Iterable[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda item: item["path"]):
        digest.update(entry["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(entry["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def build_manifest(root: Path, frozen_at: str | None = None) -> dict:
    root = root.resolve()
    entries = [
        {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)}
        for path in candidate_files(root)
    ]
    if not entries:
        raise ValueError("candidate directory contains no source files")
    if frozen_at is None:
        frozen_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": 1,
        "candidate_boundary": "src/jagi",
        "frozen_at": frozen_at,
        "bundle_sha256": bundle_sha256(entries),
        "files": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--frozen-at")
    args = parser.parse_args()
    manifest = build_manifest(args.candidate_root, args.frozen_at)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest["bundle_sha256"])


if __name__ == "__main__":
    main()
