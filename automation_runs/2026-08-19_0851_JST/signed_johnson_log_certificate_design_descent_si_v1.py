from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from itertools import combinations
from math import ceil, comb, log2

from johnson_ground_relational_lift_v1 import (
    _standard_subsets,
    lift_primitive_johnson_to_ground_relation,
)
from master_canonical_reduction import reduce_canonical_pair_structure
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from signed_johnson_complement_safe_image_si_v1 import complement_safe_t_relation_signatures
from signed_johnson_ground_profile_partition_si_v1 import (
    _color_token,
    _signed_partition_transporter,
)
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2
from coset_stabilizer_primitives import RightCoset


@dataclass(frozen=True)
class RelationDescent:
    status: str
    arity_path: tuple[int, ...]
    source_cells: tuple[tuple[int, ...], ...]
    target_cells: tuple[tuple[int, ...], ...]
    significant_split: bool
    johnson_ground_size: int | None
    johnson_subset_size: int | None
    relation_rank: int
    reason: str


@dataclass(frozen=True)
class SignedJohnsonLogCertificateProof(ProofCarryingCoset):
    ground_size: int = 0
    subset_size: int = 0
    test_arity: int = 0
    test_count: int = 0
    theorem_arity_cap: int = 0
    theorem_parameter_gate: bool = False
    arity_path: tuple[int, ...] = ()
    source_ground_cells: tuple[tuple[int, ...], ...] = ()
    target_ground_cells: tuple[tuple[int, ...], ...] = ()
    significant_ground_split: bool = False
    johnson_ground_size: int | None = None
    johnson_subset_size: int | None = None
    partition_orbit_states: int = 0


def _cells(colors):
    buckets = {}
    for u, color in enumerate(colors):
        buckets.setdefault(int(color), []).append(u)
    return tuple(tuple(xs) for _, xs in sorted(buckets.items()))


def _paired_incidence_refinement(v, coords, source_values, target_values):
    """Jointly color two complete t-set incidence structures with comparable IDs."""
    coords = tuple(tuple(x) for x in coords)
    source_values = tuple(source_values)
    target_values = tuple(target_values)
    if len(coords) != len(source_values) or len(coords) != len(target_values):
        raise ValueError("coordinate/value length mismatch")

    initial_values = sorted(set(source_values).union(target_values), key=repr)
    value_ids = {x: i for i, x in enumerate(initial_values)}
    sp = [0] * v
    tp = [0] * v
    ss = [value_ids[x] for x in source_values]
    ts = [value_ids[x] for x in target_values]
    rounds = 0

    while True:
        def signatures(point_colors, subset_colors, raw_values):
            ps = []
            for u in range(v):
                inc = Counter(subset_colors[j] for j, S in enumerate(coords) if u in S)
                ps.append(("P", point_colors[u], tuple(sorted(inc.items()))))
            rs = []
            for j, S in enumerate(coords):
                inc = Counter(point_colors[u] for u in S)
                rs.append(("R", raw_values[j], subset_colors[j], tuple(sorted(inc.items()))))
            return ps, rs

        sps, srs = signatures(sp, ss, source_values)
        tps, trs = signatures(tp, ts, target_values)
        universe = set(sps + srs + tps + trs)
        labels = {x: i for i, x in enumerate(sorted(universe, key=repr))}
        nsp = [labels[x] for x in sps]
        ntp = [labels[x] for x in tps]
        nss = [labels[x] for x in srs]
        nts = [labels[x] for x in trs]
        rounds += 1
        if nsp == sp and ntp == tp and nss == ss and nts == ts:
            break
        sp, tp, ss, ts = nsp, ntp, nss, nts
        if rounds > 2 * (v + len(coords)) + 4:
            raise AssertionError("paired certificate incidence refinement failed to stabilize")

    return tuple(sp), tuple(tp), rounds


def _codegree_signatures(v, coords, values, s):
    coords = tuple(coords)
    values = tuple(values)
    subsets = tuple(combinations(range(v), s))
    out = []
    for U in subsets:
        Uset = set(U)
        counts = Counter(values[j] for j, S in enumerate(coords) if Uset.issubset(S))
        out.append(tuple(sorted(counts.items(), key=lambda item: repr(item[0]))))
    return subsets, tuple(out)


def _pair_weights_joint(v, coords, source_values, target_values):
    if len(coords) != comb(v, 2):
        raise ValueError("pair relation must contain every pair")
    labels = {
        x: i for i, x in enumerate(sorted(set(source_values).union(target_values), key=repr))
    }
    source = tuple((tuple(coords[i]), labels[source_values[i]]) for i in range(len(coords)))
    target = tuple((tuple(coords[i]), labels[target_values[i]]) for i in range(len(coords)))
    return source, target


def _relation_descent(v, coords, source_values, target_values, arity, *, max_class_fraction, max_johnson_nodes, path=()):
    """Canonical arity descent by incidence split, codegrees, then pair/Johnson."""
    path = tuple(path) + (int(arity),)
    sp, tp, _rounds = _paired_incidence_refinement(v, coords, source_values, target_values)
    source_cells = _cells(sp)
    target_cells = _cells(tp)
    source_shape = tuple((color, len(cell)) for color, cell in zip(sorted(set(sp)), source_cells))
    target_shape = tuple((color, len(cell)) for color, cell in zip(sorted(set(tp)), target_cells))
    if source_shape != target_shape:
        return RelationDescent(
            "relation_invariant_mismatch", path, source_cells, target_cells,
            False, None, None, len(set(source_values).union(target_values)),
            "jointly normalized incidence refinement produced different canonical point-cell invariants",
        )

    largest = max((len(c) for c in source_cells), default=v)
    significant = len(source_cells) > 1 and largest <= max_class_fraction * v + 1e-12
    if significant:
        return RelationDescent(
            "certified_log_certificate_point_split", path, source_cells, target_cells,
            True, None, None, len(set(source_values).union(target_values)),
            "canonical colored test-set incidence refinement produced a significant ground-point split",
        )

    if arity == 2:
        source_pair, target_pair = _pair_weights_joint(v, coords, source_values, target_values)
        sr = reduce_canonical_pair_structure(
            v, source_pair, max_class_fraction=max_class_fraction, max_johnson_nodes=max_johnson_nodes
        )
        tr = reduce_canonical_pair_structure(
            v, target_pair, max_class_fraction=max_class_fraction, max_johnson_nodes=max_johnson_nodes
        )
        sinv = (sr.status, sr.johnson_ground_size, sr.johnson_subset_size, tuple(map(len, sr.split_classes)))
        tinv = (tr.status, tr.johnson_ground_size, tr.johnson_subset_size, tuple(map(len, tr.split_classes)))
        if sinv != tinv:
            return RelationDescent(
                "relation_invariant_mismatch", path, source_cells, target_cells,
                False, None, None, len(set(source_values).union(target_values)),
                "canonical coherent/Johnson pair reductions have different source/target invariants",
            )
        if sr.status == "exact_johnson_ground_reduction_available" and sr.progress_verified:
            return RelationDescent(
                "certified_log_certificate_johnson_descent", path, source_cells, target_cells,
                False, int(sr.johnson_ground_size), int(sr.johnson_subset_size),
                len(set(source_values).union(target_values)),
                "homogeneous pair certificate relation is an exact Johnson distance scheme on a strictly smaller ideal ground",
            )
        return RelationDescent(
            "homogeneous_pair_relation_unresolved", path, source_cells, target_cells,
            False, None, None, len(set(source_values).union(target_values)),
            "stable homogeneous pair relation is not a certified Johnson reduction",
        )

    # Descend to the largest lower arity carrying nonconstant exact codegrees.
    for s in range(arity - 1, 1, -1):
        subcoords, src = _codegree_signatures(v, coords, source_values, s)
        _, dst = _codegree_signatures(v, coords, target_values, s)
        if Counter(src) != Counter(dst):
            return RelationDescent(
                "relation_invariant_mismatch", path + (s,), source_cells, target_cells,
                False, None, None, len(set(src).union(dst)),
                "a canonical lower-arity codegree relation has different source/target color multiplicities",
            )
        if len(set(src).union(dst)) > 1:
            return _relation_descent(
                v, subcoords, src, dst, s,
                max_class_fraction=max_class_fraction,
                max_johnson_nodes=max_johnson_nodes,
                path=path,
            )

    return RelationDescent(
        "homogeneous_design_gate_unresolved", path, source_cells, target_cells,
        False, None, None, len(set(source_values).union(target_values)),
        "the nontrivial logarithmic-arity relation is codegree-homogeneous at every lower arity; a stronger Design-Lemma theorem gate is required before claiming split-or-Johnson progress",
    )


def _proof(status, coset, *, root_n, n, exact, cost, bound, terminal, accounting, checked, reason,
           v, k, t, test_count, arity_cap, gate, descent, orbit_states=0):
    return SignedJohnsonLogCertificateProof(
        status, coset, "signed_johnson_log_certificate_design_descent",
        root_n, n, True, exact, cost, bound, terminal, (), accounting, checked, reason,
        ground_size=v, subset_size=k, test_arity=t, test_count=test_count,
        theorem_arity_cap=arity_cap, theorem_parameter_gate=gate,
        arity_path=tuple(descent.arity_path) if descent is not None else (),
        source_ground_cells=tuple(descent.source_cells) if descent is not None else (),
        target_ground_cells=tuple(descent.target_cells) if descent is not None else (),
        significant_ground_split=bool(descent.significant_split) if descent is not None else False,
        johnson_ground_size=descent.johnson_ground_size if descent is not None else None,
        johnson_subset_size=descent.johnson_subset_size if descent is not None else None,
        partition_orbit_states=orbit_states,
    )


def signed_johnson_log_certificate_design_descent_si(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    max_class_fraction: float = 0.9,
    max_test_sets: int = 200000,
    max_recognition_nodes: int = 500000,
    max_johnson_nodes: int = 500000,
    partition_state_poly_power: int = 2,
    max_partition_states: int = 4096,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 256,
    max_depth: int = 64,
):
    """W1R-H5 logarithmic test-set relation aggregation and fail-closed descent.

    The actual colored Johnson k-set string supplies an exact complement-safe color
    signature on every canonical t-subset of the smaller ideal ground, with
    t=min(k-1, ceil(log2(v))).  Thus t is explicitly logarithmic and the complete
    t-set relation is label-invariant.  Joint incidence refinement first seeks a
    significant point split.  If it stays homogeneous, exact codegree relations
    descend arity canonically until a pair structure can be handed to the existing
    coherent/Johnson reducer.  A truly codegree-homogeneous design is *not* called
    solved: the routine fails closed until the stronger Design-Lemma hypotheses are
    encoded and verified.

    A significant point split is connected immediately to the existing signed
    partition-transporter and candidate-coset SI machinery.  This routine therefore
    proves real progress where its mechanical gates fire without treating the
    remaining homogeneous design case as solved.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n
    if root_n < n or max_test_sets < 1 or max_partition_states < 1:
        raise ValueError("invalid root/test/partition parameters")
    if not (0.0 < max_class_fraction < 1.0):
        raise ValueError("max_class_fraction must lie in (0,1)")

    lift = lift_primitive_johnson_to_ground_relation(
        group, source, target, max_recognition_nodes=max_recognition_nodes
    )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    arity_cap = max(1, ceil(log2(max(2, root_n))))
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, min(root_n, v or n)),
            operation_kind="unresolved_log_certificate_design_descent",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="logarithmic certificate descent requires a certified strictly smaller Johnson ground lift",
        )
        return _proof(
            "undetermined_log_certificate_johnson_lift", None,
            root_n=root_n, n=n, exact=False, cost=False, bound=0.0, terminal=False,
            accounting=accounting, checked=0, reason=lift.reason,
            v=v, k=k, t=0, test_count=0, arity_cap=arity_cap, gate=False, descent=None,
        )

    if k <= 2:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="unresolved_log_certificate_design_descent",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="no genuinely higher-arity Johnson test-set relation exists when k<=2",
        )
        return _proof(
            "undetermined_log_certificate_no_higher_arity", None,
            root_n=root_n, n=n, exact=False, cost=False, bound=0.0, terminal=False,
            accounting=accounting, checked=0, reason=accounting.reason,
            v=v, k=k, t=0, test_count=0, arity_cap=arity_cap, gate=False, descent=None,
        )

    t = min(k - 1, max(2, ceil(log2(max(2, v)))))
    test_count = comb(v, t)
    gate = t <= arity_cap and test_count <= max_test_sets
    if not gate:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="unresolved_log_certificate_design_descent",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="logarithmic theorem/test-count parameter gate is not mechanically satisfied",
        )
        return _proof(
            "undetermined_log_certificate_parameter_gate", None,
            root_n=root_n, n=n, exact=False, cost=False, bound=0.0, terminal=False,
            accounting=accounting, checked=0, reason=accounting.reason,
            v=v, k=k, t=t, test_count=test_count, arity_cap=arity_cap, gate=False, descent=None,
        )

    complement = any(bool(g.complement) for g in lift.lifted_generators)
    source_tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    target_tokens = tuple(_color_token(x) for x in lift.target_on_standard_subsets)
    source_relation = complement_safe_t_relation_signatures(
        v, k, source_tokens, t, complement_in_image=complement
    )
    target_relation = complement_safe_t_relation_signatures(
        v, k, target_tokens, t, complement_in_image=complement
    )
    coords = tuple(combinations(range(v), t))
    if len(coords) != test_count or len(source_relation) != test_count or len(target_relation) != test_count:
        raise AssertionError("logarithmic certificate relation size mismatch")

    scan_bound = log2(max(1, test_count * max(1, t) * max(1, n))) + 48.0 * log2(max(2, root_n)) + 64.0
    if Counter(source_relation) != Counter(target_relation):
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="log_certificate_invariant_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=scan_bound,
            children=(), terminal_certified=True,
            reason="complete complement-safe logarithmic test-set relation has different color multiplicities",
        )
        empty_descent = RelationDescent(
            "relation_invariant_mismatch", (t,), (), (), False, None, None,
            len(set(source_relation).union(target_relation)), accounting.reason,
        )
        return _proof(
            "exact_empty_log_certificate_relation_invariant", None,
            root_n=root_n, n=n, exact=True, cost=True, bound=scan_bound, terminal=True,
            accounting=accounting, checked=test_count, reason=accounting.reason,
            v=v, k=k, t=t, test_count=test_count, arity_cap=arity_cap, gate=True,
            descent=empty_descent,
        )

    descent = _relation_descent(
        v, coords, source_relation, target_relation, t,
        max_class_fraction=max_class_fraction,
        max_johnson_nodes=max_johnson_nodes,
    )
    if descent.status == "relation_invariant_mismatch":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="log_certificate_invariant_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=scan_bound,
            children=(), terminal_certified=True, reason=descent.reason,
        )
        return _proof(
            "exact_empty_log_certificate_descent_invariant", None,
            root_n=root_n, n=n, exact=True, cost=True, bound=scan_bound, terminal=True,
            accounting=accounting, checked=test_count, reason=descent.reason,
            v=v, k=k, t=t, test_count=test_count, arity_cap=arity_cap, gate=True, descent=descent,
        )

    if descent.significant_split:
        allowed_states = min(max_partition_states, max(1, root_n ** partition_state_poly_power))
        transport = _signed_partition_transporter(
            group, lift.lifted_generators,
            descent.source_cells, descent.target_cells,
            max_states=allowed_states,
        )
        if transport.status == "undetermined_signed_ground_partition_orbit_limit":
            accounting = RecurrenceAccountingNode(
                n=root_n, m=v, operation_kind="unresolved_log_certificate_design_descent",
                canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
                children=(), terminal_certified=False, reason=transport.reason,
            )
            return _proof(
                transport.status, None, root_n=root_n, n=n, exact=False, cost=False,
                bound=0.0, terminal=False, accounting=accounting, checked=transport.action_steps,
                reason=transport.reason, v=v, k=k, t=t, test_count=test_count,
                arity_cap=arity_cap, gate=True, descent=descent, orbit_states=transport.orbit_states,
            )

        local_bound = scan_bound + log2(max(1, transport.action_steps * (v + n + 1))) + 24.0
        if transport.status == "no_signed_ground_partition_transporter":
            accounting = RecurrenceAccountingNode(
                n=root_n, m=v, operation_kind="log_certificate_partition_terminal",
                canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
                children=(), terminal_certified=True, reason=transport.reason,
            )
            return _proof(
                "exact_empty_log_certificate_partition_orbit", None,
                root_n=root_n, n=n, exact=True, cost=True, bound=local_bound, terminal=True,
                accounting=accounting, checked=transport.action_steps, reason=transport.reason,
                v=v, k=k, t=t, test_count=test_count, arity_cap=arity_cap, gate=True,
                descent=descent, orbit_states=transport.orbit_states,
            )
        if transport.status != "signed_ground_partition_transporter_coset":
            accounting = RecurrenceAccountingNode(
                n=root_n, m=v, operation_kind="unresolved_log_certificate_design_descent",
                canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
                children=(), terminal_certified=False, reason=transport.reason,
            )
            return _proof(
                "undetermined_log_certificate_partition_transport", None,
                root_n=root_n, n=n, exact=False, cost=False, bound=0.0, terminal=False,
                accounting=accounting, checked=transport.action_steps, reason=transport.reason,
                v=v, k=k, t=t, test_count=test_count, arity_cap=arity_cap, gate=True,
                descent=descent, orbit_states=transport.orbit_states,
            )

        relation_coset = RightCoset(transport.stabilizer, transport.transporter)
        candidate = candidate_coset_string_isomorphism_u2(
            relation_coset, source, target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            group_order_poly_power=candidate_group_order_poly_power,
            max_group_order=max_candidate_group_order,
            max_depth=max_depth,
        )
        if candidate.exact:
            extra = local_bound + 8.0 * log2(max(2, n)) + 16.0
            accounting = replace(
                candidate.accounting,
                local_log2_cost_bound=candidate.accounting.local_log2_cost_bound + extra,
                reason=candidate.accounting.reason + "; preceded by canonical logarithmic certificate split and exact signed partition transport",
            )
            return SignedJohnsonLogCertificateProof(
                "exact_w1r_log_certificate_candidate_" + candidate.status,
                candidate.coset, candidate.operation_kind, root_n, n, True, True,
                candidate.local_cost_certified,
                candidate.local_log2_cost_bound + extra,
                candidate.terminal_certified, candidate.children, accounting,
                candidate.permutation_candidates_checked + transport.action_steps,
                "W1R-H5 logarithmic certificate partition restricted the ambient coset and existing candidate recursion solved the remaining full string",
                ground_size=v, subset_size=k, test_arity=t, test_count=test_count,
                theorem_arity_cap=arity_cap, theorem_parameter_gate=True,
                arity_path=descent.arity_path,
                source_ground_cells=descent.source_cells,
                target_ground_cells=descent.target_cells,
                significant_ground_split=True,
                partition_orbit_states=transport.orbit_states,
            )

        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="log_certificate_partition_filter",
            canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
            children=(), terminal_certified=False,
            reason="canonical logarithmic certificate split has an exact original-domain signed partition transporter; remaining full string stays a candidate child",
        )
        return _proof(
            "verified_log_certificate_partition_filter", relation_coset,
            root_n=root_n, n=n, exact=False, cost=True, bound=local_bound, terminal=False,
            accounting=accounting, checked=transport.action_steps, reason=accounting.reason,
            v=v, k=k, t=t, test_count=test_count, arity_cap=arity_cap, gate=True,
            descent=descent, orbit_states=transport.orbit_states,
        )

    if descent.status == "certified_log_certificate_johnson_descent":
        local_bound = scan_bound + 32.0 * log2(max(2, v)) + 48.0
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="log_certificate_johnson_structural_descent",
            canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
            children=(), terminal_certified=False,
            reason=descent.reason,
        )
        return _proof(
            "verified_log_certificate_johnson_structural_descent", None,
            root_n=root_n, n=n, exact=False, cost=True, bound=local_bound, terminal=False,
            accounting=accounting, checked=test_count, reason=(
                descent.reason + "; exact SI still requires composing this second Johnson ground with the existing signed candidate machinery"
            ),
            v=v, k=k, t=t, test_count=test_count, arity_cap=arity_cap, gate=True, descent=descent,
        )

    accounting = RecurrenceAccountingNode(
        n=root_n, m=v, operation_kind="unresolved_log_certificate_design_descent",
        canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
        children=(), terminal_certified=False, reason=descent.reason,
    )
    return _proof(
        "undetermined_log_certificate_design_gate", None,
        root_n=root_n, n=n, exact=False, cost=False, bound=0.0, terminal=False,
        accounting=accounting, checked=test_count, reason=descent.reason,
        v=v, k=k, t=t, test_count=test_count, arity_cap=arity_cap, gate=True, descent=descent,
    )
