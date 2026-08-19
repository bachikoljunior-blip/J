from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from typing import Iterable, Optional, Tuple


@dataclass(frozen=True)
class OracleResult:
    status: str
    canonical_text: Optional[str]
    backend: Optional[str]
    reason: str


def graph6_text(n: int, edges: Iterable[Tuple[int, int]]) -> str:
    """Encode a simple undirected graph in graph6 for n <= 62.

    This intentionally has no dependency on the candidate canonical-labeling
    implementation. It is only an interchange encoder for an external oracle.
    """
    if not 0 <= n <= 62:
        raise ValueError("v1 graph6 encoder supports 0..62 vertices")
    es = {tuple(sorted((int(u), int(v)))) for u, v in edges if u != v}
    if any(u < 0 or v >= n for u, v in es):
        raise ValueError("edge endpoint outside graph")
    bits = []
    for j in range(1, n):
        for i in range(j):
            bits.append(1 if (i, j) in es else 0)
    while len(bits) % 6:
        bits.append(0)
    payload = ''.join(chr(63 + sum(bits[k+t] << (5-t) for t in range(6)))
                      for k in range(0, len(bits), 6))
    return chr(n + 63) + payload


def canonicalize_with_external_oracle(n: int, edges: Iterable[Tuple[int, int]], *, timeout: float = 10.0) -> OracleResult:
    """Return an independent canonical graph when a known backend is installed.

    Preferred backend is nauty's labelg.  Absence, timeout, nonzero exit, or
    malformed output is fail-closed: no canonical result is manufactured.
    """
    labelg = shutil.which("labelg")
    if labelg is None:
        return OracleResult("oracle_unavailable", None, None, "nauty labelg not installed")
    source = graph6_text(n, edges) + "\n"
    try:
        p = subprocess.run([labelg, "-q"], input=source, text=True,
                           capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return OracleResult("oracle_timeout", None, "nauty-labelg", "external oracle timed out")
    if p.returncode != 0:
        return OracleResult("oracle_failed", None, "nauty-labelg", p.stderr.strip() or "nonzero exit")
    lines = [x.strip() for x in p.stdout.splitlines() if x.strip()]
    if len(lines) != 1:
        return OracleResult("oracle_failed", None, "nauty-labelg", "expected one canonical graph6 line")
    return OracleResult("canonical", lines[0], "nauty-labelg", "independent external canonical labeling")
