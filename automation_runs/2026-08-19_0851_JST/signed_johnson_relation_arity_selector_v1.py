from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import comb, lgamma, log, log2

from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from signed_johnson_complement_safe_image_si_v1 import (
    complement_safe_t_relation_signatures,
)
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from signed_johnson_relation_image_candidate_si_v1 import (
    signed_johnson_relation_image_candidate_string_isomorphism,
)


@dataclass(frozen=True)
class RelationArityChoice:
    status: str
    arity: int | None
    image_degree: int
    relation_rank: int
    young_log2_order_upper_bound: float
    considered_arities: tuple[int, ...]
    reason: str


def _young_log2_from_state(state):
    counts = Counter(state)
    return sum(lgamma(int(c) + 1) / log(2.0) for c in counts.values())


def choose_complement_safe_relation_arity(
    v: int,
    k: int,
    source_tokens,
    target_tokens,
    *,
    complement_in_image: bool,
    min_arity: int = 2,
    max_arity: int | None = None,
):
    """Choose the strongest strictly-smaller canonical local relation arity.

    Every eligible t produces a canonical colored string on the t-subsets of the
    Johnson ground.  We only consider C(v,t) < C(v,k), so the image is strictly
    smaller than the current Johnson domain.  If one arity already has different
    source/target signature multiplicities, the smallest such image is selected
    because it gives an exact emptiness certificate.

    Otherwise we score informative arities by the order of the *full* Young group
    preserving the source relation colors: product_c |cell_c|!.  The true action
    image stabilizer is a subgroup of this Young group, so minimizing this exact,
    label-invariant quantity is a deterministic upper-bound proxy for minimizing
    the candidate symmetry before invoking expensive SI.  This is stronger than
    choosing an arity only by its number of colors, while remaining independent of
    arbitrary ground labels.
    """
    v = int(v)
    k = int(k)
    if not (1 <= k < v):
        raise ValueError("invalid Johnson parameters")
    source_tokens = tuple(source_tokens)
    target_tokens = tuple(target_tokens)
    domain_degree = comb(v, k)
    if len(source_tokens) != domain_degree or len(target_tokens) != domain_degree:
        raise ValueError("token count does not match J(v,k)")
    lo = max(1, int(min_arity))
    hi = k - 1 if max_arity is None else min(k - 1, int(max_arity))
    if hi < lo:
        return RelationArityChoice(
            "no_strictly_smaller_relation_arity", None, 0, 0, 0.0, (),
            "no configured local-relation arity lies below k",
        )

    candidates = []
    mismatches = []
    considered = []
    for t in range(lo, hi + 1):
        image_degree = comb(v, t)
        if image_degree >= domain_degree:
            continue
        considered.append(t)
        src = complement_safe_t_relation_signatures(
            v, k, source_tokens, t,
            complement_in_image=complement_in_image,
        )
        dst = complement_safe_t_relation_signatures(
            v, k, target_tokens, t,
            complement_in_image=complement_in_image,
        )
        src_counter = Counter(src)
        dst_counter = Counter(dst)
        rank = len(set(src).union(dst))
        labels = {
            sig: i
            for i, sig in enumerate(sorted(set(src).union(dst), key=repr))
        }
        source_state = tuple(labels[sig] for sig in src)
        young_log2 = _young_log2_from_state(source_state)
        item = (image_degree, t, rank, young_log2)
        if src_counter != dst_counter:
            mismatches.append(item)
        elif rank > 1:
            # Smaller Young upper bound is the primary symmetry-breaking score;
            # then prefer the smaller image and smaller arity deterministically.
            candidates.append((young_log2, image_degree, t, rank))

    considered = tuple(considered)
    if mismatches:
        image_degree, t, rank, young_log2 = min(mismatches)
        return RelationArityChoice(
            "relation_arity_invariant_mismatch", t, image_degree, rank,
            young_log2, considered,
            "this strictly smaller complement-safe local relation already has different canonical color multiplicities",
        )
    if candidates:
        young_log2, image_degree, t, rank = min(candidates)
        return RelationArityChoice(
            "selected_informative_relation_arity", t, image_degree, rank,
            young_log2, considered,
            "selected the informative strictly smaller arity with the minimum full-Young color-stabilizer order upper bound",
        )
    return RelationArityChoice(
        "no_informative_strict_relation_arity", None, 0, 1 if considered else 0,
        0.0, considered,
        "all tested strictly smaller complement-safe local relations are homogeneous; pair/higher-arity image filtering is exhausted at this configured arity range",
    )


def adaptive_signed_johnson_relation_candidate_si(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    max_relation_arity: int | None = None,
    max_recognition_nodes: int = 500000,
    image_si_poly_power: int = 4,
    max_image_si_nodes: int = 200000,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 256,
    max_depth: int = 64,
):
    """W1R-H3 adaptive local-relation entrypoint before Design-Lemma escalation.

    A single certified Johnson lift is used only to choose a label-invariant arity.
    The selected arity is then executed by rev180/rev181, which independently
    re-certifies the lift, solves the exact smaller relation image, lifts its coset
    to the original domain, and restricts the full colored k-subset string inside
    that candidate via existing U2/S1/V2 machinery.

    If every strictly smaller tested arity is homogeneous, this returns a typed
    fail-closed leaf.  That is precisely the remaining case for logarithmic local
    certificates / Design-Lemma-style aggregation; it is not reinterpreted as a
    successful SI or quasipolynomial terminal.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n
    if root_n < n:
        raise ValueError("root_n must dominate the current domain")

    lift = lift_primitive_johnson_to_ground_relation(
        group, source, target, max_recognition_nodes=max_recognition_nodes
    )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, min(root_n, v or n)),
            operation_kind="unresolved_signed_johnson_arity_selector",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="adaptive arity selection requires a certified strictly smaller Johnson ground lift",
        )
        return ProofCarryingCoset(
            "undetermined_signed_johnson_arity_selector_lift", None,
            "unresolved_signed_johnson_arity_selector", root_n, n,
            True, False, False, 0.0, False, (), accounting, 0, lift.reason,
        )

    complement = any(bool(g.complement) for g in lift.lifted_generators)
    source_tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    target_tokens = tuple(_color_token(x) for x in lift.target_on_standard_subsets)
    choice = choose_complement_safe_relation_arity(
        v, k, source_tokens, target_tokens,
        complement_in_image=complement,
        max_arity=max_relation_arity,
    )
    if choice.arity is None:
        scan_bound = (
            log2(max(1, n * max(1, len(choice.considered_arities))))
            + 48.0 * log2(max(2, root_n)) + 64.0
        )
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, v),
            operation_kind="unresolved_signed_johnson_design_aggregation",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason=choice.reason,
        )
        return ProofCarryingCoset(
            "undetermined_signed_johnson_design_aggregation_required", None,
            "unresolved_signed_johnson_design_aggregation", root_n, n,
            True, False, False, 0.0, False, (), accounting,
            len(choice.considered_arities),
            choice.reason + f"; selector scan upper-bound witness log2(work) <= {scan_bound:.6f}",
        )

    return signed_johnson_relation_image_candidate_string_isomorphism(
        group, source, target,
        relation_arity=choice.arity,
        root_n=root_n,
        max_recognition_nodes=max_recognition_nodes,
        image_si_poly_power=image_si_poly_power,
        max_image_si_nodes=max_image_si_nodes,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        candidate_group_order_poly_power=candidate_group_order_poly_power,
        max_candidate_group_order=max_candidate_group_order,
        max_depth=max_depth,
    )
