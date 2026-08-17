"""One-time, integrity-checked installer for the verified J source bundle."""

from __future__ import annotations

import base64
import hashlib
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTS = ROOT / "bootstrap_parts"
EXPECTED_ARCHIVE_SHA256 = "4eb4db9ae731f0cbb926c70ad7e06a10c3b1bc1ac262f0471bce7be3919f3790"
PART_LAYOUT = (
    ("part0.txt", 6000, 512799, "b4497202a2b03c69d08993bbca2d7a0c063e571012eb7de8b59392153fa99034"),
    ("part1.txt", 6000, 511854, "322833909f3c3f7b459b84802fbd95a3ba66849c7e3296f27ee2e183cc95c498"),
    ("part2a.txt", 3000, 255896, "78ba12edfa5c599faca2808acaeec624c4d27894822c73c41d777cb41a8d15f4"),
    ("part2b.txt", 3000, 258018, "48d1963116ef3c5be74192888cc45b13932c575920a6c3c66ea3a34fef8d0c01"),
    ("part3.txt", 4536, 385007, "2ab78013c3b636ae42ddb11bae7c728d60851c0715adfd6d722ad26a27d5471b"),
)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def load_verified_part(name: str, expected_size: int, expected_sum: int, expected_hash: str) -> str:
    path = PARTS / name
    text = path.read_text(encoding="ascii").strip()

    # The connector transfer lost one base64 character in this single part.
    # Recover it deterministically, accepting a candidate only when its full
    # SHA-256 equals the independently computed source hash.
    if len(text) == expected_size - 1:
        missing_code = expected_sum - sum(map(ord, text))
        if not 0 <= missing_code < 128:
            raise RuntimeError(f"cannot recover {name}: invalid missing byte")
        missing = chr(missing_code)
        for position in range(expected_size):
            candidate = text[:position] + missing + text[position:]
            if digest(candidate) == expected_hash:
                text = candidate
                path.write_text(text, encoding="ascii")
                print(f"Recovered one verified byte in {name} at offset {position}")
                break

    if len(text) != expected_size or sum(map(ord, text)) != expected_sum or digest(text) != expected_hash:
        raise RuntimeError(f"payload verification failed for {name}")
    return text


def main() -> None:
    encoded = "".join(load_verified_part(*spec) for spec in PART_LAYOUT)
    archive = base64.b64decode(encoded, validate=True)
    actual = hashlib.sha256(archive).hexdigest()
    if actual != EXPECTED_ARCHIVE_SHA256:
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
