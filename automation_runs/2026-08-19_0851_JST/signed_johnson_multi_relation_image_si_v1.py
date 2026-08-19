from __future__ import annotations

from collections import Counter
from dataclasses import replace
from math import comb, floor, lgamma, log, log2

from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from paired_action_coset_preimage_v1 import paired_action_coset_preimage
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from recursive_point_image_coset_intersection import right_coset_intersection_recursive
from signed_johnson_complement_safe_image_si_v1 import (
    complement_safe_t_relation_signatures,
    complement_safe_t_subset_image_generators,
)
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from signed_johnson_relation_image_candidate_si_v1 import (
    signed_johnson_relation_image_candidate_string_isomorphism,
)
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


def _young_log2(signatures):
    counts = Counter(signatures)
    return sum(lgamma(int(c) + 1) / log(2.0) for c in counts.values())


def _block_diagonal_generators(component_generator_families):
    families = tuple(tuple(f) for f in component_generator_families)
    if not families:
        return (), 0
    generator_count = len(families[0])
    if any(len(f) != generator_count for f in families):
        raise ValueError("component action families must preserve generator pairing")
    degrees = tuple(len(f[0]) if f else 0 for f in families)
    if any(any(len(q) != d for q in f) for f, d in zip(families, degrees)):
        raise ValueError("component action generator has inconsistent degree")
    total = sum(degrees)
    out = []
    for i in range(generator_count):
        q = list(range(total))
        offset = 0
        for family, degree in zip(families, degrees):
            local = family[i]
            for x in range(degree):
                q[offset + x] = offset + local[x]
            offset += degree
        out.append(tuple(q))
    return tuple(out), total


def _absorb_filter_cost(exact_child, local_bound, selected_arities):
    if not exact_child.exact:
        raise ValueError("cost absorption requires an exact full-string child")
    extra = float(local_bound) + 8.0 * log2(max(2, exact_child.domain_size)) + 16.0
    accounting = replace(
        exact_child.accounting,
        local_log2_cost_bound=exact_child.accounting.local_log2_cost_bound + extra,
        reason=(
            exact_child.accounting.reason
            + "; preceded by one exact block-diagonal complement-safe relation-image SI on arities "
            + repr(tuple(selected_arities))
            + " and generic original-domain preimage filtering"
        ),
    )
    return ProofCarryingCoset(
        "exact_w1r_multi_relation_candidate_" + exact_child.status,
        exact_child.coset,
        exact_child.operation_kind,
        exact_child.root_n,
        exact_child.domain_size,
        exact_child.canonical,
        True,
        exact_child.local_cost_certified,
        exact_child.local_log2_cost_bound + extra,
        exact_child.terminal_certified,
        exact_child.children,
        accounting,
        exact_child.permutation_candidates_checked,
        "multiple strictly-smaller complement-safe relation images were solved jointly and the lifted candidate full-string SI then closed exactly",
    )


def signed_johnson_multi_relation_candidate_si(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    min_arity: int = 2,
    max_arity: int | None = None,
    max_aux_fraction: float = 0.9,
    max_recognition_nodes: int = 500000,
    image_si_poly_power: int = 4,
    max_image_si_nodes: int = 200000,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 256,
    max_depth: int = 64,
):
    """W1R-H4: intersect several local-relation constraints in one smaller image.

    Each eligible arity t<k supplies a complement-safe colored t-subset relation.
    Rather than solving only one relation, we choose a deterministic set whose
    disjoint-union auxiliary degree remains at most `max_aux_fraction` of the
    original J(v,k) domain.  The score is symmetry broken per auxiliary point:
    log2(|S_d|) minus the log2 order of the full color-preserving Young subgroup,
    divided by d=C(v,t).  This is an invariant upper-bound heuristic, not a
    complexity theorem, and the hard remainder still fails closed.

    The selected actions are combined block-diagonally *with generator pairing
    intact*.  Exact SI of the concatenated relation string is therefore one image
    right coset of the original group homomorphism; rev179 lifts that right coset
    exactly.  The full colored k-subset string is then restricted inside the lifted
    candidate via existing U2/S1/V2 recursion.  A nonempty relation filter is never
    called a full SI result unless that final candidate recursion is exact.
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
    if not (0.0 < max_aux_fraction < 1.0):
        raise ValueError("max_aux_fraction must lie in (0,1)")

    lift = lift_primitive_johnson_to_ground_relation(
        group, source, target, max_recognition_nodes=max_recognition_nodes
    )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, min(root_n, v or n)),
            operation_kind="unresolved_signed_johnson_multi_relation",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="multi-relation image requires a certified Johnson ground lift",
        )
        return ProofCarryingCoset(
            "undetermined_signed_johnson_multi_relation_lift", None,
            "unresolved_signed_johnson_multi_relation", root_n, n,
            True, False, False, 0.0, False, (), accounting, 0, lift.reason,
        )

    complement = any(bool(g.complement) for g in lift.lifted_generators)
    src_tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    dst_tokens = tuple(_color_token(x) for x in lift.target_on_standard_subsets)
    hi = k - 1 if max_arity is None else min(k - 1, int(max_arity))
    lo = max(1, int(min_arity))
    budget = max(1, floor(max_aux_fraction * n))

    records = []
    mismatch = []
    for t in range(lo, hi + 1):
        d = comb(v, t)
        if d >= n or d > budget:
            continue
        src_sig = complement_safe_t_relation_signatures(
            v, k, src_tokens, t, complement_in_image=complement
        )
        dst_sig = complement_safe_t_relation_signatures(
            v, k, dst_tokens, t, complement_in_image=complement
        )
        if Counter(src_sig) != Counter(dst_sig):
            mismatch.append((d, t))
            continue
        rank = len(set(src_sig).union(dst_sig))
        if rank <= 1:
            continue
        young = _young_log2(src_sig)
        broken = max(0.0, lgamma(d + 1) / log(2.0) - young)
        score = broken / max(1, d)
        records.append((score, d, t, src_sig, dst_sig, rank))

    if mismatch:
        # A single smallest mismatching arity already gives exact original
        # emptiness; reuse the audited one-arity pipeline rather than duplicate it.
        _, t = min(mismatch)
        return signed_johnson_relation_image_candidate_string_isomorphism(
            group, source, target,
            relation_arity=t, root_n=root_n,
            max_recognition_nodes=max_recognition_nodes,
            image_si_poly_power=image_si_poly_power,
            max_image_si_nodes=max_image_si_nodes,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            candidate_group_order_poly_power=candidate_group_order_poly_power,
            max_candidate_group_order=max_candidate_group_order,
            max_depth=max_depth,
        )

    # Greedy invariant packing by symmetry broken per auxiliary coordinate.
    selected = []
    used = 0
    for record in sorted(records, key=lambda r: (-r[0], r[1], r[2])):
        _, d, t, src_sig, dst_sig, rank = record
        if used + d <= budget:
            selected.append(record)
            used += d
    if not selected:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, v),
            operation_kind="unresolved_signed_johnson_design_aggregation",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="no informative complement-safe relation family fits the configured constant-fraction auxiliary budget",
        )
        return ProofCarryingCoset(
            "undetermined_signed_johnson_design_aggregation_required", None,
            "unresolved_signed_johnson_design_aggregation", root_n, n,
            True, False, False, 0.0, False, (), accounting, len(records),
            accounting.reason,
        )

    component_families = []
    source_state = []
    target_state = []
    selected_arities = []
    scan_units = 1
    for _, d, t, src_sig, dst_sig, rank in sorted(selected, key=lambda r: r[2]):
        _, gens, _ = complement_safe_t_subset_image_generators(
            lift.lifted_generators, v, t
        )
        component_families.append(gens)
        selected_arities.append(t)
        source_state.extend((t, sig) for sig in src_sig)
        target_state.extend((t, sig) for sig in dst_sig)
        scan_units += d * max(1, n) * max(1, t + 1) * max(1, k)

    combined_gens, image_degree = _block_diagonal_generators(component_families)
    if image_degree != used or image_degree > budget or image_degree >= n:
        raise AssertionError("selected relation-image family violated its certified shrink budget")
    if not combined_gens:
        combined_gens = (identity(image_degree),)
    image = schreier_stabilizer_chain(combined_gens)

    value_coset = _all_value_preserving_maps(tuple(source_state), tuple(target_state))
    if value_coset is None:
        raise AssertionError("selected equal-multiplicity relation components lost joint multiplicity equality")
    allowed_nodes = min(max_image_si_nodes, max(1, int(root_n) ** int(image_si_poly_power)))
    intersection = right_coset_intersection_recursive(
        RightCoset(image, identity(image_degree)), value_coset,
        max_nodes=allowed_nodes,
    )
    if intersection.status == "undetermined_node_limit":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, image_degree),
            operation_kind="unresolved_signed_johnson_multi_relation",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="exact block-diagonal relation-image SI exhausted its polynomial node cap",
        )
        return ProofCarryingCoset(
            "undetermined_signed_johnson_multi_relation_node_limit", None,
            "unresolved_signed_johnson_multi_relation", root_n, n,
            True, False, False, 0.0, False, (), accounting,
            intersection.search_nodes, intersection.reason,
        )

    work_units = max(
        1,
        scan_units + intersection.search_nodes * max(2, image_degree + n + v) ** 6,
    )
    local_bound = log2(work_units) + 64.0 * log2(max(2, root_n)) + 96.0

    if intersection.status == "empty_intersection":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, image_degree),
            operation_kind="signed_johnson_multi_relation_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
            children=(), terminal_certified=True,
            reason="joint exact SI of the selected complement-safe relation images is empty",
        )
        return ProofCarryingCoset(
            "exact_empty_signed_johnson_multi_relation", None,
            "signed_johnson_multi_relation_terminal", root_n, n,
            True, True, True, local_bound, True, (), accounting,
            intersection.search_nodes,
            "no ambient signed-Johnson permutation preserves all selected local relations simultaneously",
        )
    if intersection.status != "exact_intersection_coset" or intersection.coset is None:
        raise AssertionError("unexpected exact joint relation-image SI status")

    preimage = paired_action_coset_preimage(group, combined_gens, intersection.coset)
    if preimage.status != "exact_paired_action_coset_preimage" or preimage.coset is None:
        raise AssertionError("joint image coset did not lift through the generator-paired action")

    candidate = candidate_coset_string_isomorphism_u2(
        preimage.coset,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=candidate_group_order_poly_power,
        max_group_order=max_candidate_group_order,
        max_depth=max_depth,
    )
    if candidate.exact:
        return _absorb_filter_cost(candidate, local_bound, selected_arities)

    accounting = RecurrenceAccountingNode(
        n=root_n, m=max(1, image_degree),
        operation_kind="unresolved_signed_johnson_design_aggregation",
        canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
        children=(), terminal_certified=False,
        reason="joint lower-arity relation filtering is exact and significantly smaller, but the full-string candidate remains structurally hard",
    )
    return ProofCarryingCoset(
        "undetermined_w1r_after_multi_relation_" + candidate.status,
        preimage.coset,
        "unresolved_signed_johnson_design_aggregation", root_n, n,
        True, False, False, 0.0, False, (candidate,), accounting,
        intersection.search_nodes + candidate.permutation_candidates_checked,
        accounting.reason + "; next step is logarithmic local-certificate / Design-Lemma-style aggregation inside this exact joint-relation candidate",
    )
