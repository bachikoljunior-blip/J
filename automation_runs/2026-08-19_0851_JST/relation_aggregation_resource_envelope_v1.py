from __future__ import annotations

from dataclasses import dataclass, replace
from math import comb


@dataclass(frozen=True)
class RelationAggregationResourceEnvelope:
    status: str
    quotient_size: int
    test_size: int
    test_count: int
    round_upper_bound: int
    per_round_work_upper_bound: int
    work_upper_bound: int
    max_work: int
    admitted: bool
    executed_rounds: int
    charged_work_upper_bound: int
    complete: bool
    reason: str


def relation_aggregation_resource_envelope(
    quotient_size: int,
    test_size: int,
    test_count: int,
    max_work: int,
) -> RelationAggregationResourceEnvelope:
    """Preflight the existing canonical incidence-refinement implementation."""
    m, t, count, cap = map(int, (
        quotient_size, test_size, test_count, max_work,
    ))
    if m <= 0 or t <= 0 or t > m or cap <= 0:
        raise ValueError("invalid relation aggregation resource parameters")
    if count != comb(m, t):
        raise ValueError("test_count is not the complete t-subset multiplicity")
    items = m + count
    rounds = items + 2
    # The current implementation scans every test for every point, scans every
    # test incidence, and canonically labels at most ``items`` signatures.  The
    # quadratic comparison allowance is deliberately conservative.
    per_round = (
        m * count * (t + 1)
        + count * t
        + items * items * (t + 2)
        + items
    )
    upper = rounds * per_round
    admitted = upper <= cap
    return RelationAggregationResourceEnvelope(
        "certified_relation_aggregation_work_bound" if admitted
        else "relation_aggregation_work_cap_exceeded",
        m, t, count, rounds, per_round, upper, cap, admitted, 0, 0, False,
        (
            "the complete canonical incidence refinement fits the finite budget"
            if admitted else
            "the conservative complete-refinement bound exceeds the cap before aggregation"
        ),
    )


def record_relation_aggregation_execution(
    envelope: RelationAggregationResourceEnvelope,
    executed_rounds: int,
) -> RelationAggregationResourceEnvelope:
    rounds = int(executed_rounds)
    if not envelope.admitted:
        raise ValueError("cannot record execution for a rejected envelope")
    if not 0 <= rounds <= envelope.round_upper_bound:
        raise ValueError("executed refinement rounds exceed the proven bound")
    charged = rounds * envelope.per_round_work_upper_bound
    return replace(
        envelope,
        executed_rounds=rounds,
        charged_work_upper_bound=charged,
        complete=True,
    )


__all__ = [
    "RelationAggregationResourceEnvelope",
    "relation_aggregation_resource_envelope",
    "record_relation_aggregation_execution",
]
