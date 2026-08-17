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
PART_LAYOUT = (
    ("part0.txt", 6000),
    ("part1.txt", 6000),
    ("part2a.txt", 3000),
    ("part2b.txt", 3000),
    ("part3.txt", 4536),
)


def main() -> None:
    encoded_parts: list[str] = []
    for name, expected_size in PART_LAYOUT:
        path = PARTS / name
        text = path.read_text(encoding="ascii").strip()
        if len(text) != expected_size:
            raise RuntimeError(f"invalid payload size for {name}: {len(text)}")
        encoded_parts.append(text)

    archive = base64.b64decode("".join(encoded_parts), validate=True)
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
