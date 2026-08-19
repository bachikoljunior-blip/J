from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
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
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


@dataclass(frozen=True)
class JointRelationChoice:
    status: str
    arities: tuple[int, ...]
    image_degree: int
    image_degree_budget: int
    relation_ranks: tuple[int, ...]
    considered_arities: tuple[int, ...]
    reason: str


@dataclass(frozen=True)
class SignedJohnsonJointRelationProof(ProofCarryingCoset):
    ground_size: int = 0
    subset_size: int = 0
    relation_arities: tuple[int, ...] = ()
    joint_image_degree: int = 0
    joint_image_order: int = 0
    kernel_order: int = 0
    preimage_filter_order: int = 0
    relation_ranks: tuple[int, ...] = ()
    image_search_nodes: int = 0


def _young_log2(signatures):
    counts = Counter(signatures)
    return sum(lgamma(int(c) + 1) / log(2.0) for c in counts.values())


def choose_joint_complement_safe_relation_arities(
    v: int,
    k: int,
    source_tokens,
    target_tokens,
    *,
    complement_in_image: bool,
    shrink_fraction: float = 0.9,
    min_arity: int = 2,
    max_arity: int | None = None,
):
    """Choose several informative lower-arity relations under one strict shrink budget.

    Each eligible t gives a canonical colored string on C(v,t) coordinates.  The
    joint action is their generator-paired disjoint union, so its kernel is the
    intersection of the individual action kernels and the complete original-domain
    preimage of a joint image coset is exact.  We keep the total auxiliary degree
    at most ``floor(shrink_fraction * C(v,k))``; with the default 0.9 this matches
    the constant-factor auxiliary-shrink rule used by the proof-tree verifier.

    Informative arities are ordered by the full Young color-stabilizer order of
    their source relation (smaller is stronger), then by image degree and arity.
    The strongest relation is retained first and further independent constraints
    are added while the joint disjoint-union degree remains within budget.  The
    selection depends only on canonical relation statistics and numerical sizes.
    """
    v = int(v)
    k = int(k)
    if not (1 <= k < v):
        raise ValueError("invalid Johnson parameters")
    if not (0.0 < float(shrink_fraction) < 1.0):
        raise ValueError("shrink_fraction must lie in (0,1)")
    source_tokens = tuple(source_tokens)
    target_tokens = tuple(target_tokens)
    domain_degree = comb(v, k)
    if len(source_tokens) != domain_degree or len(target_tokens) != domain_degree:
        raise ValueError("token count does not match J(v,k)")

    budget = max(1, min(domain_degree - 1, floor(float(shrink_fraction) * domain_degree)))
    lo = max(1, int(min_arity))
    hi = k - 1 if max_arity is None else min(k - 1, int(max_arity))
    if hi < lo:
        return JointRelationChoice(
            "no_joint_relation_arity", (), 0, budget, (), (),
            "no configured lower relation arity exists",
        )

    informative = []
    mismatches = []
    considered = []
    ranks = {}
    for t in range(lo, hi + 1):
        degree = comb(v, t)
        if degree >= domain_degree:
            continue
        considered.append(t)
        src = complement_safe_t_relation_signatures(
            v, k, source_tokens, t, complement_in_image=complement_in_image
        )
        dst = complement_safe_t_relation_signatures(
            v, k, target_tokens, t, complement_in_image=complement_in_image
        )
        rank = len(set(src).union(dst))
        ranks[t] = rank
        if Counter(src) != Counter(dst):
            mismatches.append((degree, t, rank))
        elif rank > 1:
            informative.append((_young_log2(src), degree, t, rank))

    considered = tuple(considered)
    if mismatches:
        degree, t, rank = min(mismatches)
        return JointRelationChoice(
            "joint_relation_invariant_mismatch", (t,), degree, budget, (rank,), considered,
            "one strictly smaller canonical relation already has different source/target color multiplicities",
        )

    selected = []
    used = 0
    for _young, degree, t, _rank in sorted(informative):
        if used + degree <= budget:
            selected.append(t)
            used += degree
    selected = tuple(sorted(selected))
    selected_ranks = tuple(ranks[t] for t in selected)
    if len(selected) < 2:
        return JointRelationChoice(
            "insufficient_joint_relation_budget", selected, used, budget,
            selected_ranks, considered,
            "fewer than two informative strictly smaller relation images fit the configured constant-factor auxiliary budget",
        )
    return JointRelationChoice(
        "selected_joint_informative_relations", selected, used, budget,
        selected_ranks, considered,
        "selected several canonical informative relation images whose generator-paired disjoint union remains a constant-factor smaller auxiliary action",
    )


def _joint_relation_data(lifted_generators, v, k, source_tokens, target_tokens, arities, *, complement):
    block_images = []
    source_tagged = []
    target_tagged = []
    ranks = []
    total = 0
    for t in arities:
        coords, image_gens, _ = complement_safe_t_subset_image_generators(
            lifted_generators, v, t
        )
        src = complement_safe_t_relation_signatures(
            v, k, source_tokens, t, complement_in_image=complement
        )
        dst = complement_safe_t_relation_signatures(
            v, k, target_tokens, t, complement_in_image=complement
        )
        if len(coords) != len(src) or len(src) != len(dst):
            raise AssertionError("relation coordinate/signature length mismatch")
        block_images.append((total, tuple(image_gens), len(coords)))
        source_tagged.extend((t, sig) for sig in src)
        target_tagged.extend((t, sig) for sig in dst)
        ranks.append(len(set(src).union(dst)))
        total += len(coords)

    ngen = len(tuple(lifted_generators))
    if any(len(gens) != ngen for _, gens, _ in block_images):
        raise AssertionError("one image generator is required for each lifted generator in every relation block")
    joint_gens = []
    for i in range(ngen):
        q = []
        for offset, gens, degree in block_images:
            g = gens[i]
            if len(g) != degree:
                raise AssertionError("relation image generator degree mismatch")
            q.extend(offset + x for x in g)
        joint_gens.append(tuple(q))

    labels = {
        token: i
        for i, token in enumerate(sorted(set(source_tagged).union(target_tagged), key=repr))
    }
    source_state = tuple(labels[x] for x in source_tagged)
    target_state = tuple(labels[x] for x in target_tagged)
    return tuple(joint_gens), source_state, target_state, tuple(ranks)


def _proof(
    status,
    coset,
    *,
    root_n,
    domain_size,
    operation_kind,
    exact,
    cost,
    bound,
    terminal,
    accounting,
    checked,
    reason,
    v,
    k,
    arities=(),
    image_degree=0,
    image_order=0,
    kernel_order=0,
    preimage_order=0,
    ranks=(),
    nodes=0,
):
    return SignedJohnsonJointRelationProof(
        status,
        coset,
        operation_kind,
        root_n,
        domain_size,
        True,
        exact,
        cost,
        bound,
        terminal,
        (),
        accounting,
        checked,
        reason,
        ground_size=v,
        subset_size=k,
        relation_arities=tuple(arities),
        joint_image_degree=image_degree,
        joint_image_order=image_order,
        kernel_order=kernel_order,
        preimage_filter_order=preimage_order,
        relation_ranks=tuple(ranks),
        image_search_nodes=nodes,
    )


def signed_johnson_joint_relation_image_filter(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    shrink_fraction: float = 0.9,
    max_relation_arity: int | None = None,
    max_recognition_nodes: int = 500000,
    image_si_poly_power: int = 4,
    max_image_si_nodes: int = 200000,
):
    """W1R-H4 exact joint relation-image filter with a complete original preimage.

    Several informative complement-safe lower-arity relation actions are combined
    as one disjoint-union action.  This is the diagonal homomorphism of the same
    original group into the product of the selected permutation images, represented
    on a disjoint union so the existing paired Schreier preimage machinery applies
    unchanged.  Exact joint image SI therefore computes the intersection of all
    selected relation constraints before the full k-subset string is revisited.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n
    if root_n < n or image_si_poly_power < 1 or max_image_si_nodes < 1:
        raise ValueError("invalid root/image-search parameters")

    lift = lift_primitive_johnson_to_ground_relation(
        group, source, target, max_recognition_nodes=max_recognition_nodes
    )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, min(root_n, v or n)),
            operation_kind="unresolved_signed_johnson_joint_relation",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="joint relation filtering requires a certified strictly smaller Johnson ground lift",
        )
        return _proof(
            "undetermined_signed_johnson_joint_relation_lift", None,
            root_n=root_n, domain_size=n,
            operation_kind="unresolved_signed_johnson_joint_relation",
            exact=False, cost=False, bound=0.0, terminal=False,
            accounting=accounting, checked=0, reason=lift.reason,
            v=v, k=k,
        )

    complement = any(bool(g.complement) for g in lift.lifted_generators)
    source_tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    target_tokens = tuple(_color_token(x) for x in lift.target_on_standard_subsets)
    choice = choose_joint_complement_safe_relation_arities(
        v, k, source_tokens, target_tokens,
        complement_in_image=complement,
        shrink_fraction=shrink_fraction,
        max_arity=max_relation_arity,
    )
    if choice.status == "joint_relation_invariant_mismatch":
        t = choice.arities[0]
        scan_bound = (
            log2(max(1, 2 * choice.image_degree * n * max(1, t + 1) * max(1, k)))
            + 48.0 * log2(max(2, root_n)) + 64.0
        )
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, choice.image_degree),
            operation_kind="signed_johnson_joint_relation_invariant_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=scan_bound,
            children=(), terminal_certified=True, reason=choice.reason,
        )
        return _proof(
            "exact_empty_signed_johnson_joint_relation_invariant", None,
            root_n=root_n, domain_size=n,
            operation_kind="signed_johnson_joint_relation_invariant_terminal",
            exact=True, cost=True, bound=scan_bound, terminal=True,
            accounting=accounting, checked=0,
            reason="every original isomorphism preserves each selected canonical lower-arity relation",
            v=v, k=k, arities=choice.arities,
            image_degree=choice.image_degree, ranks=choice.relation_ranks,
        )
    if choice.status != "selected_joint_informative_relations":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, min(root_n, choice.image_degree or v or n)),
            operation_kind="unresolved_signed_johnson_joint_relation",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False, reason=choice.reason,
        )
        return _proof(
            "undetermined_signed_johnson_joint_relation_selection", None,
            root_n=root_n, domain_size=n,
            operation_kind="unresolved_signed_johnson_joint_relation",
            exact=False, cost=False, bound=0.0, terminal=False,
            accounting=accounting, checked=0, reason=choice.reason,
            v=v, k=k, arities=choice.arities,
            image_degree=choice.image_degree, ranks=choice.relation_ranks,
        )

    joint_gens, source_state, target_state, ranks = _joint_relation_data(
        lift.lifted_generators,
        v, k, source_tokens, target_tokens, choice.arities,
        complement=complement,
    )
    image_degree = len(source_state)
    if image_degree != choice.image_degree or image_degree > choice.image_degree_budget:
        raise AssertionError("joint image violates the certified selection budget")
    if not joint_gens:
        joint_gens = (identity(image_degree),)
    image = schreier_stabilizer_chain(joint_gens)

    value_coset = _all_value_preserving_maps(source_state, target_state)
    if value_coset is None:
        raise AssertionError("per-arity equal multiplicities failed to produce a joint value coset")
    allowed_nodes = min(max_image_si_nodes, max(1, int(root_n) ** int(image_si_poly_power)))
    intersection = right_coset_intersection_recursive(
        RightCoset(image, identity(image_degree)),
        value_coset,
        max_nodes=allowed_nodes,
    )

    max_t = max(choice.arities)
    scan_units = max(1, 2 * image_degree * n * max(1, max_t + 1) * max(1, k))
    if intersection.status == "undetermined_node_limit":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, image_degree),
            operation_kind="unresolved_signed_johnson_joint_relation",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="exact joint relation-image intersection exhausted its configured polynomial node cap",
        )
        return _proof(
            "undetermined_signed_johnson_joint_relation_node_limit", None,
            root_n=root_n, domain_size=n,
            operation_kind="unresolved_signed_johnson_joint_relation",
            exact=False, cost=False, bound=0.0, terminal=False,
            accounting=accounting, checked=intersection.search_nodes,
            reason=intersection.reason,
            v=v, k=k, arities=choice.arities, image_degree=image_degree,
            image_order=image.order, ranks=ranks, nodes=intersection.search_nodes,
        )

    work_units = max(
        1,
        scan_units + intersection.search_nodes * max(2, image_degree + n + v) ** 6,
    )
    local_bound = log2(work_units) + 64.0 * log2(max(2, root_n)) + 96.0
    if intersection.status == "empty_intersection":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, image_degree),
            operation_kind="signed_johnson_joint_relation_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
            children=(), terminal_certified=True,
            reason="exact generator-paired joint relation image SI is empty",
        )
        return _proof(
            "exact_empty_signed_johnson_joint_relation_image", None,
            root_n=root_n, domain_size=n,
            operation_kind="signed_johnson_joint_relation_terminal",
            exact=True, cost=True, bound=local_bound, terminal=True,
            accounting=accounting, checked=intersection.search_nodes,
            reason="no group element simultaneously preserves all selected canonical lower-arity relations",
            v=v, k=k, arities=choice.arities, image_degree=image_degree,
            image_order=image.order, ranks=ranks, nodes=intersection.search_nodes,
        )
    if intersection.status != "exact_intersection_coset" or intersection.coset is None:
        raise AssertionError("unexpected exact joint image intersection status")

    preimage = paired_action_coset_preimage(group, joint_gens, intersection.coset)
    if preimage.status != "exact_paired_action_coset_preimage" or preimage.coset is None:
        raise AssertionError("joint image coset failed exact paired-action preimage reconstruction")

    accounting = RecurrenceAccountingNode(
        n=root_n, m=max(1, image_degree),
        operation_kind="signed_johnson_joint_relation_filter",
        canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
        children=(), terminal_certified=False,
        reason=(
            "several strictly-smaller canonical relation actions were solved simultaneously on one generator-paired disjoint-union image; "
            "the complete joint image coset was lifted back to the original Johnson domain"
        ),
    )
    return _proof(
        "verified_signed_johnson_joint_relation_image_filter", preimage.coset,
        root_n=root_n, domain_size=n,
        operation_kind="signed_johnson_joint_relation_filter",
        exact=False, cost=True, bound=local_bound, terminal=False,
        accounting=accounting, checked=intersection.search_nodes,
        reason=(
            "the returned candidate is the complete original-domain preimage of the exact simultaneous relation-image coset; "
            "every full-string isomorphism remains inside it"
        ),
        v=v, k=k, arities=choice.arities, image_degree=image_degree,
        image_order=image.order, kernel_order=preimage.kernel_order,
        preimage_order=preimage.preimage_subgroup_order, ranks=ranks,
        nodes=intersection.search_nodes,
    )


def _absorb_joint_filter_cost(exact_child: ProofCarryingCoset, relation_filter: ProofCarryingCoset):
    if not exact_child.exact or not relation_filter.local_cost_certified:
        raise ValueError("joint composition requires an exact child and certified relation filter cost")
    extra = relation_filter.local_log2_cost_bound + 8.0 * log2(max(2, exact_child.domain_size)) + 16.0
    accounting = replace(
        exact_child.accounting,
        local_log2_cost_bound=exact_child.accounting.local_log2_cost_bound + extra,
        reason=(
            exact_child.accounting.reason
            + "; preceded by exact simultaneous lower-arity relation-image SI and complete generator-paired original-domain preimage filtering"
        ),
    )
    return ProofCarryingCoset(
        "exact_w1r_joint_relation_candidate_" + exact_child.status,
        exact_child.coset,
        exact_child.operation_kind,
        exact_child.root_n,
        exact_child.domain_size,
        exact_child.canonical,
        True,
        bool(exact_child.local_cost_certified),
        exact_child.local_log2_cost_bound + extra,
        exact_child.terminal_certified,
        exact_child.children,
        accounting,
        exact_child.permutation_candidates_checked + relation_filter.permutation_candidates_checked,
        (
            "W1R-H4 composition: several canonical lower-arity relations were solved together on a constant-factor smaller image, "
            "their complete original-domain preimage restricted the candidate, and existing U2/S1/V2 machinery solved the full colored k-subset string inside it"
        ),
    )


def signed_johnson_joint_relation_candidate_string_isomorphism(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    shrink_fraction: float = 0.9,
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
    """W1R-H4 joint relation filter followed by exact full-string candidate recursion."""
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n

    relation = signed_johnson_joint_relation_image_filter(
        group, source, target,
        root_n=root_n,
        shrink_fraction=shrink_fraction,
        max_relation_arity=max_relation_arity,
        max_recognition_nodes=max_recognition_nodes,
        image_si_poly_power=image_si_poly_power,
        max_image_si_nodes=max_image_si_nodes,
    )
    if relation.exact or relation.coset is None:
        return relation

    candidate = candidate_coset_string_isomorphism_u2(
        relation.coset,
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
        return _absorb_joint_filter_cost(candidate, relation)

    accounting = RecurrenceAccountingNode(
        n=root_n, m=max(1, n),
        operation_kind="unresolved_signed_johnson_joint_relation_candidate",
        canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
        children=(), terminal_certified=False,
        reason=(
            "the constant-factor smaller joint relation image and complete original-domain preimage are certified, but the remaining full string is still a hard candidate-coset child"
        ),
    )
    return ProofCarryingCoset(
        "undetermined_w1r_after_joint_relation_image_" + candidate.status,
        relation.coset,
        "unresolved_signed_johnson_joint_relation_candidate",
        root_n,
        n,
        True,
        False,
        False,
        0.0,
        False,
        (relation, candidate),
        accounting,
        relation.permutation_candidates_checked + candidate.permutation_candidates_checked,
        (
            "rev183 intersected several informative lower-arity relation constraints in one exact paired image and lifted the complete joint candidate; "
            "existing candidate recursion did not yet close the full string: " + candidate.reason
        ),
    )
