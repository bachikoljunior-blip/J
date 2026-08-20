from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class SingleTestResourcePhaseCharge:
    name: str
    work_upper_bound: int
    admitted: bool
    executed: bool


@dataclass(frozen=True)
class SingleTestResourceEnvelope:
    status: str
    max_work: int
    charged_work: int
    remaining_work: int
    phases: Tuple[SingleTestResourcePhaseCharge, ...]
    admitted: bool
    reason: str


def single_test_resource_envelope(
    max_work: int,
    phases,
) -> SingleTestResourceEnvelope:
    """Freeze one execution-linked budget shared by every phase of one T.

    A phase contributes to ``charged_work`` exactly when it was admitted and
    actually executed.  A rejected phase is retained as evidence but is not
    charged because all rev224--rev227 gates reject before that phase starts.
    """
    cap = int(max_work)
    if cap <= 0:
        raise ValueError("max_single_test_schreier_work must be positive")
    frozen = tuple(phases)
    charged = sum(
        int(phase.work_upper_bound)
        for phase in frozen
        if phase.admitted and phase.executed
    )
    if charged > cap:
        raise AssertionError("single-test phase charges exceeded their shared cap")
    admitted = all(phase.admitted for phase in frozen)
    return SingleTestResourceEnvelope(
        "certified_single_test_work_bound" if admitted
        else "single_test_work_cap_exceeded",
        cap,
        charged,
        cap - charged,
        frozen,
        admitted,
        (
            "one finite budget covers every executed preimage, giant-action, quotient/kernel, and parent-reassembly phase for this test set"
            if admitted else
            "the next complete phase exceeded the shared remaining budget and was not executed"
        ),
    )


__all__ = [
    "SingleTestResourceEnvelope",
    "SingleTestResourcePhaseCharge",
    "single_test_resource_envelope",
]
