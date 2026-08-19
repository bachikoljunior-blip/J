from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import log2

from coherent_pair_refinement import coherent_refine_pair_relation
from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import (
    _standard_subsets,
    lift_primitive_johnson_to_ground_relation,
)
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from signed_johnson_ground_profile_partition_si_v1 import (
    _color_token,
    _histogram,
    _signed_partition_transporter,
)


@dataclass(frozen=True)
class SignedGroundPairRelationProof(ProofCarryingCoset):
    ground_size: int = 0
    subset_size: int = 0
    pair_rank: int = 0
    source_pair_weights: tuple = ()
    target_pair_weights: tuple = ()
    source_ground_cells: tuple[tuple[int, ...], ...] = ()
    target_ground_cells: tuple[tuple[int, ...], ...] = ()
    significant_ground_split: bool = False
    pair_relation_nontrivial: bool = False
    strict_ground_progress: bool = False
    complement_in_image: bool = False
    partition_orbit_states: int = 0


def _pair_signatures(v, k, value_tokens, *, complement_in_image):
    subsets = _standard_subsets(v, k)
    if len(subsets) != len(value_tokens):
        raise AssertionError("standard Johnson relation length mismatch")
    out = []
    for a, b in combinations(range(v), 2):
        by_intersection = []
        pair = {a, b}
        for t in range(3):
            by_intersection.append(
                _histogram(
                    value_tokens[i]
                    for i, subset in enumerate(subsets)
                    if len(pair.intersection(subset)) == t
                )
            )
        h0, h1, h2 = by_intersection
        if complement_in_image:
            if v != 2 * k:
                raise AssertionError("a complement bit is impossible away from v=2k")
            # Complement swaps intersection sizes 0 and 2 and fixes size 1.
            out.append(("signed-pair", h1, tuple(sorted((h0, h2)))))
        else:
            out.append(("pair", h0, h1, h2))
    return tuple(out)


def _ordered_point_cells(point_colors):
    classes = {}
    for point, color in enumerate(point_colors):
        classes.setdefault(int(color), []).append(point)
    return tuple(tuple(points) for _, points in sorted(classes.items()))


def _proof(
    status,
    coset,
    *,
    root_n,
    current_degree,
    exact,
    cost_certified,
    local_bound,
    terminal,
    accounting,
    reason,
    ground_size,
    subset_size,
    pair_rank=0,
    source_pair_weights=(),
    target_pair_weights=(),
    source_cells=(),
    target_cells=(),
    significant=False,
    nontrivial=False,
    strict_progress=False,
    complement_in_image=False,
    orbit_states=0,
    checked=0,
):
    return SignedGroundPairRelationProof(
        status,
        coset,
        "signed_johnson_ground_pair_relation",
        root_n,
        current_degree,
        True,
        exact,
        cost_certified,
        local_bound,
        terminal,
        (),
        accounting,
        checked,
        reason,
        ground_size=ground_size,
        subset_size=subset_size,
        pair_rank=pair_rank,
        source_pair_weights=tuple(source_pair_weights),
        target_pair_weights=tuple(target_pair_weights),
        source_ground_cells=tuple(source_cells),
        target_ground_cells=tuple(target_cells),
        significant_ground_split=significant,
        pair_relation_nontrivial=nontrivial,
        strict_ground_progress=strict_progress,
        complement_in_image=complement_in_image,
        partition_orbit_states=orbit_states,
    )


def signed_johnson_ground_pair_relation_si(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    max_class_fraction: float = 0.9,
    max_coherent_rounds: int = 128,
    partition_state_poly_power: int = 2,
    max_partition_states: int = 4096,
    max_recognition_nodes: int = 500000,
):
    """W1R second-order canonical relation for unresolved signed Johnson leaves.

    For each unordered pair of ground points, record the exact color histograms of
    k-subsets meeting that pair in 0, 1, and 2 points.  When the exceptional
    v=2k complement is present, the 0/2 histograms are stored as an unordered pair,
    making the signature invariant under the complement bit while remaining
    equivariant under every ground permutation.

    The resulting canonical edge-colored complete graph is coherently refined.
    A significant diagonal split is transported back through the original-domain
    signed Johnson action, producing an exact candidate partition coset (a filter,
    not yet the exact string-isomorphism coset).  If the coherent relation remains
    homogeneous but has rank > 1, the proof exposes a strictly smaller v-point
    canonical pair relation as the next local-certificate/design recurrence target.
    No unresolved branch is promoted to an exact SI claim.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    m = group.degree
    if len(source) != m or len(target) != m:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = m
    if root_n < m:
        raise ValueError("root_n must dominate the current Johnson domain")
    if not (0.0 < max_class_fraction < 1.0):
        raise ValueError("max_class_fraction must be in (0,1)")
    if max_coherent_rounds < 1 or partition_state_poly_power < 1 or max_partition_states < 1:
        raise ValueError("invalid refinement/orbit parameters")

    lift = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=max_recognition_nodes,
    )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, min(root_n, v or m)),
            operation_kind="signed_johnson_ground_pair_unresolved",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason="Johnson ground lift was not certified",
        )
        return _proof(
            "undetermined_signed_ground_pair_lift",
            None,
            root_n=root_n,
            current_degree=m,
            exact=False,
            cost_certified=False,
            local_bound=0.0,
            terminal=False,
            accounting=accounting,
            reason=lift.reason,
            ground_size=v,
            subset_size=k,
        )

    complement_in_image = any(bool(g.complement) for g in lift.lifted_generators)
    source_tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    target_tokens = tuple(_color_token(x) for x in lift.target_on_standard_subsets)
    source_signatures = _pair_signatures(
        v, k, source_tokens, complement_in_image=complement_in_image
    )
    target_signatures = _pair_signatures(
        v, k, target_tokens, complement_in_image=complement_in_image
    )
    pairs = tuple(combinations(range(v), 2))
    pair_count = len(pairs)

    scan_units = max(1, 6 * max(1, pair_count) * max(1, len(source_tokens)) * max(1, k))
    base_bound = log2(scan_units) + 36.0 * log2(max(2, root_n)) + 48.0
    strict_progress = v < m

    if Counter(source_signatures) != Counter(target_signatures):
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, v),
            operation_kind="signed_johnson_ground_pair_invariant_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=base_bound,
            children=(),
            terminal_certified=True,
            reason="complement-safe pair-signature multisets differ",
        )
        return _proof(
            "exact_empty_signed_ground_pair_invariant",
            None,
            root_n=root_n,
            current_degree=m,
            exact=True,
            cost_certified=True,
            local_bound=base_bound,
            terminal=True,
            accounting=accounting,
            reason="every signed Johnson isomorphism preserves the canonical pair-signature multiset",
            ground_size=v,
            subset_size=k,
            strict_progress=strict_progress,
            complement_in_image=complement_in_image,
        )

    labels = {
        signature: i
        for i, signature in enumerate(
            sorted(set(source_signatures).union(target_signatures), key=repr)
        )
    }
    source_weights = tuple((pair, labels[sig]) for pair, sig in zip(pairs, source_signatures))
    target_weights = tuple((pair, labels[sig]) for pair, sig in zip(pairs, target_signatures))
    pair_rank = len(labels)
    nontrivial = pair_rank > 1

    source_coherent = coherent_refine_pair_relation(
        v,
        source_weights,
        max_class_fraction=max_class_fraction,
        max_rounds=max_coherent_rounds,
    )
    target_coherent = coherent_refine_pair_relation(
        v,
        target_weights,
        max_class_fraction=max_class_fraction,
        max_rounds=max_coherent_rounds,
    )
    if source_coherent.status == "undetermined_round_limit" or target_coherent.status == "undetermined_round_limit":
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, v),
            operation_kind="signed_johnson_ground_pair_unresolved",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason="coherent pair refinement hit its explicit round cap",
        )
        return _proof(
            "undetermined_signed_ground_pair_coherent_round_limit",
            None,
            root_n=root_n,
            current_degree=m,
            exact=False,
            cost_certified=False,
            local_bound=0.0,
            terminal=False,
            accounting=accounting,
            reason="fail closed rather than treating an incomplete 2-WL refinement as canonical closure",
            ground_size=v,
            subset_size=k,
            pair_rank=pair_rank,
            source_pair_weights=source_weights,
            target_pair_weights=target_weights,
            nontrivial=nontrivial,
            strict_progress=strict_progress,
            complement_in_image=complement_in_image,
        )

    source_cells = _ordered_point_cells(source_coherent.point_colors)
    target_cells = _ordered_point_cells(target_coherent.point_colors)
    source_shape = tuple((source_coherent.point_colors[cell[0]], len(cell)) for cell in source_cells)
    target_shape = tuple((target_coherent.point_colors[cell[0]], len(cell)) for cell in target_cells)

    coherent_units = max(
        1,
        (source_coherent.refinement_rounds + target_coherent.refinement_rounds + 2)
        * max(1, v ** 3),
    )
    local_bound = log2(scan_units + coherent_units) + 40.0 * log2(max(2, root_n)) + 56.0

    if source_shape != target_shape:
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, v),
            operation_kind="signed_johnson_ground_pair_coherent_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason="stable coherent diagonal color multiplicities differ",
        )
        return _proof(
            "exact_empty_signed_ground_pair_coherent_invariant",
            None,
            root_n=root_n,
            current_degree=m,
            exact=True,
            cost_certified=True,
            local_bound=local_bound,
            terminal=True,
            accounting=accounting,
            reason="any signed Johnson isomorphism induces an isomorphism of the canonical pair relation and hence preserves coherent diagonal fibers",
            ground_size=v,
            subset_size=k,
            pair_rank=pair_rank,
            source_pair_weights=source_weights,
            target_pair_weights=target_weights,
            source_cells=source_cells,
            target_cells=target_cells,
            nontrivial=nontrivial,
            strict_progress=strict_progress,
            complement_in_image=complement_in_image,
        )

    significant = (
        source_coherent.significant_split
        and target_coherent.significant_split
        and len(source_cells) > 1
    )
    if significant:
        allowed_states = min(max_partition_states, max(1, root_n ** partition_state_poly_power))
        transport = _signed_partition_transporter(
            group,
            lift.lifted_generators,
            source_cells,
            target_cells,
            max_states=allowed_states,
        )
        transport_bound = (
            local_bound
            + log2(max(1, transport.action_steps * (v + 1) + transport.orbit_states * max(1, m)))
            + 8.0 * log2(max(2, root_n))
            + 16.0
        )
        if transport.status == "undetermined_signed_ground_partition_orbit_limit":
            accounting = RecurrenceAccountingNode(
                n=root_n,
                m=max(1, v),
                operation_kind="signed_johnson_ground_pair_unresolved",
                canonical=True,
                cost_certified=False,
                local_log2_cost_bound=0.0,
                children=(),
                terminal_certified=False,
                reason=transport.reason,
            )
            return _proof(
                transport.status,
                None,
                root_n=root_n,
                current_degree=m,
                exact=False,
                cost_certified=False,
                local_bound=0.0,
                terminal=False,
                accounting=accounting,
                reason=transport.reason,
                ground_size=v,
                subset_size=k,
                pair_rank=pair_rank,
                source_pair_weights=source_weights,
                target_pair_weights=target_weights,
                source_cells=source_cells,
                target_cells=target_cells,
                significant=True,
                nontrivial=nontrivial,
                strict_progress=strict_progress,
                complement_in_image=complement_in_image,
                orbit_states=transport.orbit_states,
                checked=transport.action_steps,
            )
        if transport.status == "no_signed_ground_partition_transporter":
            accounting = RecurrenceAccountingNode(
                n=root_n,
                m=max(1, v),
                operation_kind="signed_johnson_ground_pair_partition_terminal",
                canonical=True,
                cost_certified=True,
                local_log2_cost_bound=transport_bound,
                children=(),
                terminal_certified=True,
                reason="canonical coherent ground partition has no ambient signed transporter",
            )
            return _proof(
                "exact_empty_signed_ground_pair_partition_orbit",
                None,
                root_n=root_n,
                current_degree=m,
                exact=True,
                cost_certified=True,
                local_bound=transport_bound,
                terminal=True,
                accounting=accounting,
                reason=transport.reason,
                ground_size=v,
                subset_size=k,
                pair_rank=pair_rank,
                source_pair_weights=source_weights,
                target_pair_weights=target_weights,
                source_cells=source_cells,
                target_cells=target_cells,
                significant=True,
                nontrivial=nontrivial,
                strict_progress=strict_progress,
                complement_in_image=complement_in_image,
                orbit_states=transport.orbit_states,
                checked=transport.action_steps,
            )
        if transport.status == "signed_ground_partition_transporter_coset":
            accounting = RecurrenceAccountingNode(
                n=root_n,
                m=max(1, v),
                operation_kind="signed_johnson_ground_pair_partition_filter",
                canonical=True,
                cost_certified=True,
                local_log2_cost_bound=transport_bound,
                children=(),
                terminal_certified=False,
                reason="canonical second-order pair relation produced an exact original-domain partition transporter coset; residual relation SI remains recursive",
            )
            return _proof(
                "verified_signed_ground_pair_partition_filter",
                RightCoset(transport.stabilizer, transport.transporter),
                root_n=root_n,
                current_degree=m,
                exact=False,
                cost_certified=True,
                local_bound=transport_bound,
                terminal=False,
                accounting=accounting,
                reason="W1R may recurse inside this exact candidate partition coset; no exact full SI claim is made",
                ground_size=v,
                subset_size=k,
                pair_rank=pair_rank,
                source_pair_weights=source_weights,
                target_pair_weights=target_weights,
                source_cells=source_cells,
                target_cells=target_cells,
                significant=True,
                nontrivial=nontrivial,
                strict_progress=strict_progress,
                complement_in_image=complement_in_image,
                orbit_states=transport.orbit_states,
                checked=transport.action_steps,
            )

    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, v),
        operation_kind="signed_johnson_ground_pair_relation_filter",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=False,
        reason=(
            "complement-safe second-order relation is exact and canonical on the smaller Johnson ground; "
            "no significant diagonal fiber was obtained, so local-certificate/design recurrence remains"
        ),
    )
    return _proof(
        "verified_signed_ground_pair_relation_recurrence_target" if nontrivial and strict_progress else "undetermined_signed_ground_pair_no_progress",
        None,
        root_n=root_n,
        current_degree=m,
        exact=False,
        cost_certified=True,
        local_bound=local_bound,
        terminal=False,
        accounting=accounting,
        reason=(
            "the unresolved W1R leaf now has an explicit smaller canonical pair relation for coherent/local-certificate recurrence"
            if nontrivial and strict_progress
            else "pair signatures did not produce a nontrivial strictly smaller recurrence target"
        ),
        ground_size=v,
        subset_size=k,
        pair_rank=pair_rank,
        source_pair_weights=source_weights,
        target_pair_weights=target_weights,
        source_cells=source_cells,
        target_cells=target_cells,
        significant=False,
        nontrivial=nontrivial,
        strict_progress=strict_progress,
        complement_in_image=complement_in_image,
    )
