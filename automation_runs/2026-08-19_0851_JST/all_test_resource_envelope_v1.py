from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class AllTestResourceEnvelope:
    status: str
    test_count: int
    per_test_work_cap: int
    work_upper_bound: int
    max_work: int
    admitted: bool
    executed_test_count: int
    charged_work: int
    unexecuted_test_count: int
    complete: bool
    reason: str


def all_test_resource_envelope(
    test_count: int,
    per_test_work_cap: int,
    max_work: int,
) -> AllTestResourceEnvelope:
    """Reserve the complete canonical all-T schedule before its first T."""
    count = int(test_count)
    per_test = int(per_test_work_cap)
    cap = int(max_work)
    if count < 0 or per_test <= 0 or cap <= 0:
        raise ValueError("all-test count and resource caps must be positive")
    upper = count * per_test
    admitted = upper <= cap
    return AllTestResourceEnvelope(
        "certified_all_test_work_bound" if admitted
        else "all_test_work_cap_exceeded",
        count,
        per_test,
        upper,
        cap,
        admitted,
        0,
        0,
        count,
        False,
        (
            "the complete canonical test-set multiplicity fits the finite all-test budget"
            if admitted else
            "test_count times the per-test bound exceeds the all-test cap; no test set was executed"
        ),
    )


def record_all_test_execution(
    envelope: AllTestResourceEnvelope,
    executed_test_count: int,
    charged_work: int,
    *,
    complete: bool,
) -> AllTestResourceEnvelope:
    executed = int(executed_test_count)
    charged = int(charged_work)
    if not 0 <= executed <= envelope.test_count:
        raise ValueError("executed test count outside reserved schedule")
    if charged < 0 or charged > envelope.work_upper_bound or charged > envelope.max_work:
        raise ValueError("all-test execution charge outside reserved envelope")
    if complete and executed != envelope.test_count:
        raise ValueError("complete all-test evidence omitted a test set")
    return replace(
        envelope,
        executed_test_count=executed,
        charged_work=charged,
        unexecuted_test_count=envelope.test_count - executed,
        complete=bool(complete),
    )


__all__ = [
    "AllTestResourceEnvelope",
    "all_test_resource_envelope",
    "record_all_test_execution",
]
