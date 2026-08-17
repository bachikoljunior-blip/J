"""One-time, integrity-checked installer for the verified J source bundle."""

from __future__ import annotations

import base64
import hashlib
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTS = ROOT / "bootstrap_parts"
EXPECTED_SHA256 = "4eb4db9ae731f0cbb926c70ad7e06a10c3b1bc1ac262f0471bce7be3919f3790"


def main() -> None:
    part_paths = sorted(PARTS.glob("part*.txt"))
    if [path.name for path in part_paths] != [f"part{i}.txt" for i in range(4)]:
        raise RuntimeError("bootstrap payload is incomplete")

    encoded = "".join(path.read_text(encoding="ascii").strip() for path in part_paths)
    archive = base64.b64decode(encoded, validate=True)
    actual = hashlib.sha256(archive).hexdigest()
    if actual != EXPECTED_SHA256:
        raise RuntimeError(f"bootstrap checksum mismatch: {actual}")

    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        members = bundle.getmembers()
        for member in members:
            if not member.isfile() or member.issym() or member.islnk():
                raise RuntimeError(f"unsupported archive entry: {member.name}")
            destination = (ROOT / member.name).resolve()
            if destination != ROOT and ROOT not in destination.parents:
                raise RuntimeError(f"archive path escapes repository: {member.name}")

        for member in members:
            destination = (ROOT / member.name).resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise RuntimeError(f"cannot read archive entry: {member.name}")
            destination.write_bytes(source.read())

    print(f"Installed {len(members)} verified source files; sha256={actual}")


if __name__ == "__main__":
    main()
