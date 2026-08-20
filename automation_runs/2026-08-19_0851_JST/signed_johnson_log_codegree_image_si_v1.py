from __future__ import annotations

from collections import Counter
from dataclasses import replace
from itertools import combinations
from math import ceil, comb, log2

from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from paired_action_coset_preimage_v1 import paired_action_coset_preimage
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4
from signed_johnson_complement_safe_image_si_v1 import (
    complement_safe_t_relation_signatures,
    complement_safe_t_subset_image_generators,
)
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from signed_johnson_log_certificate_design_descent_si_v1 import (
    _codegree_signatures,
    _relation_descent,
)


def _unresolved(status, *, root_n, n, reason, coset=None, children=(), checked=0):
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, min(root_n, n)),
        operation_kind="unresolved_log_codegree_image",
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=(),
        terminal_certified=False,
        reason=reason,
    )
    return ProofCarryingCoset(
        status,
        coset,
        "unresolved_log_codegree_image",
        root_n,
        n,
        True,
        False,
        False,
        0.0,
        False,
        tuple(children),
        accounting,
        checked,
        reason,
    )


def _replay_nonconstant_codegrees_to_pair(v, coords, source_values, target_values, arity):
    """Replay rev184's deterministic nonconstant-codegree descent and expose arity 2."""
    coords = tuple(tuple(x) for x in coords)
    source_values = tuple(source_values)
    target_values = tuple(target_values)
    arity = int(arity)
    path = [arity]
    while arity > 2:
        advanced = False
        for s in range(arity - 1, 1, -1):
            subcoords, src = _codegree_signatures(v, coords, source_values, s)
            _, dst = _codegree_signatures(v, coords, target_values, s)
            if Counter(src) != Counter(dst):
                return None
            if len(set(src).union(dst)) > 1:
                coords = tuple(subcoords)
                source_values = tuple(src)
                target_values = tuple(dst)
                arity = int(s)
                path.append(arity)
                advanced = True
                break
        if not advanced:
            return None
    if arity != 2 or coords != tuple(combinations(range(v), 2)):
        return None
    return coords, source_values, target_values, tuple(path)


def signed_johnson_log_codegree_image_candidate_si(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
    candidate_dispatch,
    max_test_sets: int = 200000,
    max_recognition_nodes: int = 500000,
    max_johnson_nodes: int = 500000,
    max_class_fraction: float = 0.9,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 256,
    max_depth: int = 64,
    max_johnson_test_sets: int = 200000,
    max_partition_states: int = 4096,
    family_poly_power: int = 2,
    max_family_systems: int = 4096,
    max_family_quotient_order: int = 4096,
):
    """Close rev184's Johnson-structural codegree leaf through its actual pair image.

    rev184 already proves that a logarithmic complete t-set relation canonically
    descends, by exact codegrees, to a homogeneous pair relation that is an exact
    Johnson distance scheme.  The old path stopped at the *second* Johnson-ground
    structural certificate.  This routine observes that no new coordinate solver
    is required to obtain exact String Isomorphism progress: the pair relation is
    itself a canonical string on C(v,2) coordinates, with an exact generator-paired
    action induced from the first Johnson ground.

    We therefore solve that pair-relation string inside its actual action image,
    lift the resulting right coset directly to the original Johnson domain using
    the generic paired-action preimage, then solve the original full string inside
    that exact filter.  Pure exceptional-complement generators map to the identity
    pair action and are retained automatically in the preimage kernel.  Any gate,
    image SI, preimage, recurrence certificate, or final full-string child that
    does not close exactly remains fail-closed.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n < n or max_test_sets < 1:
        raise ValueError("invalid root/test parameters")

    lift = lift_primitive_johnson_to_ground_relation(
        group, source, target, max_recognition_nodes=max_recognition_nodes
    )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        return _unresolved(
            "undetermined_log_codegree_image_johnson_lift",
            root_n=root_n,
            n=n,
            reason=lift.reason,
        )
    if k <= 2:
        return _unresolved(
            "undetermined_log_codegree_image_no_higher_arity",
            root_n=root_n,
            n=n,
            reason="codegree-image bridge requires the same genuinely higher-arity Johnson regime as rev184",
        )

    arity_cap = max(1, ceil(log2(max(2, root_n))))
    t = min(k - 1, max(2, ceil(log2(max(2, v)))))
    test_count = comb(v, t)
    if t > arity_cap or test_count > max_test_sets:
        return _unresolved(
            "undetermined_log_codegree_image_parameter_gate",
            root_n=root_n,
            n=n,
            reason="rev184 logarithmic theorem/test-count gate is not mechanically satisfied",
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
    descent = _relation_descent(
        v,
        coords,
        source_relation,
        target_relation,
        t,
        max_class_fraction=max_class_fraction,
        max_johnson_nodes=max_johnson_nodes,
    )
    if descent.status != "certified_log_certificate_johnson_descent":
        return _unresolved(
            "undetermined_log_codegree_image_not_johnson_structural_leaf",
            root_n=root_n,
            n=n,
            reason="this bridge applies only after rev184 certifies the homogeneous pair relation as an exact Johnson structural descent; got " + descent.status,
            checked=test_count,
        )

    replay = _replay_nonconstant_codegrees_to_pair(
        v, coords, source_relation, target_relation, t
    )
    if replay is None:
        raise AssertionError("rev184 certified Johnson descent but deterministic codegree replay did not reach pairs")
    pair_coords, pair_source, pair_target, path = replay
    if tuple(descent.arity_path) != tuple(path):
        raise AssertionError("codegree replay path disagrees with rev184 structural certificate")

    induced_coords, image_gens, _parity = complement_safe_t_subset_image_generators(
        lift.lifted_generators, v, 2
    )
    if tuple(induced_coords) != tuple(pair_coords):
        raise AssertionError("pair-action coordinate order disagrees with codegree replay")
    if not image_gens:
        image_gens = (identity(len(pair_coords)),)
    image = schreier_stabilizer_chain(image_gens)
    image_candidate = candidate_dispatch(
        RightCoset(image, identity(len(pair_coords))),
        pair_source,
        pair_target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=candidate_group_order_poly_power,
        max_group_order=max_candidate_group_order,
        max_depth=max_depth,
        max_johnson_test_sets=max_johnson_test_sets,
        max_partition_states=max_partition_states,
        max_recognition_nodes=max_recognition_nodes,
        max_johnson_nodes=max_johnson_nodes,
        family_poly_power=family_poly_power,
        max_family_systems=max_family_systems,
        max_family_quotient_order=max_family_quotient_order,
    )
    if not image_candidate.exact:
        return _unresolved(
            "undetermined_log_codegree_pair_image_" + image_candidate.status,
            root_n=root_n,
            n=n,
            reason="the canonical rev184 codegree pair image is exact and strictly smaller, but its candidate SI child remains unresolved: " + image_candidate.reason,
            children=(image_candidate,),
            checked=test_count + image_candidate.permutation_candidates_checked,
        )

    image_check = validate_quasipoly_recurrence_tree_v4(image_candidate.accounting)
    if not image_check.certified:
        return _unresolved(
            "undetermined_log_codegree_pair_image_accounting_" + image_check.status,
            root_n=root_n,
            n=n,
            reason="pair-image SI is exact but its recurrence certificate did not validate: " + image_check.reason,
            children=(image_candidate,),
            checked=test_count + image_candidate.permutation_candidates_checked,
        )

    scan_bound = log2(max(1, test_count * max(1, t) * max(1, n))) + 56.0 * log2(max(2, root_n)) + 80.0
    if image_candidate.coset is None:
        bound = scan_bound + image_check.certified_log2_work_bound
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, min(root_n, v)),
            operation_kind="log_codegree_pair_image_empty_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=bound,
            children=(),
            terminal_certified=True,
            reason="the canonical rev184 codegree pair image has exact empty SI in the actual induced action, so the original full-string SI is empty",
        )
        return ProofCarryingCoset(
            "exact_empty_log_codegree_pair_image",
            None,
            "log_codegree_pair_image_empty_terminal",
            root_n,
            n,
            True,
            True,
            True,
            bound,
            True,
            (),
            accounting,
            test_count + image_candidate.permutation_candidates_checked,
            accounting.reason,
        )

    preimage = paired_action_coset_preimage(group, image_gens, image_candidate.coset)
    if preimage.status != "exact_paired_action_coset_preimage" or preimage.coset is None:
        return _unresolved(
            "undetermined_log_codegree_pair_preimage_" + preimage.status,
            root_n=root_n,
            n=n,
            reason="exact pair-image SI did not lift to a certified original-domain preimage: " + preimage.reason,
            children=(image_candidate,),
            checked=test_count + image_candidate.permutation_candidates_checked,
        )

    filtered = candidate_dispatch(
        preimage.coset,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=candidate_group_order_poly_power,
        max_group_order=max_candidate_group_order,
        max_depth=max_depth,
        max_johnson_test_sets=max_johnson_test_sets,
        max_partition_states=max_partition_states,
        max_recognition_nodes=max_recognition_nodes,
        max_johnson_nodes=max_johnson_nodes,
        family_poly_power=family_poly_power,
        max_family_systems=max_family_systems,
        max_family_quotient_order=max_family_quotient_order,
    )
    if not filtered.exact:
        return _unresolved(
            "undetermined_log_codegree_full_candidate_" + filtered.status,
            root_n=root_n,
            n=n,
            coset=preimage.coset,
            reason="pair-image SI and complete original-domain preimage are exact, but the remaining full-string candidate child is unresolved: " + filtered.reason,
            children=(image_candidate, filtered),
            checked=test_count + image_candidate.permutation_candidates_checked + filtered.permutation_candidates_checked,
        )

    filtered_check = validate_quasipoly_recurrence_tree_v4(filtered.accounting)
    if not filtered_check.certified:
        return _unresolved(
            "undetermined_log_codegree_full_accounting_" + filtered_check.status,
            root_n=root_n,
            n=n,
            coset=preimage.coset,
            reason="full-string candidate is exact but its recurrence certificate did not validate: " + filtered_check.reason,
            children=(image_candidate, filtered),
            checked=test_count + image_candidate.permutation_candidates_checked + filtered.permutation_candidates_checked,
        )

    extra = (
        scan_bound
        + image_check.certified_log2_work_bound
        + log2(max(1, preimage.sift_levels + preimage.kernel_order.bit_length() + image.order.bit_length()))
        + 32.0 * log2(max(2, n))
        + 32.0
    )
    accounting = replace(
        filtered.accounting,
        local_log2_cost_bound=filtered.accounting.local_log2_cost_bound + extra,
        reason=(
            filtered.accounting.reason
            + "; preceded by rev184 canonical codegree descent, exact induced pair-image SI, and exact paired-action preimage"
        ),
    )
    return ProofCarryingCoset(
        "exact_w1r_log_codegree_pair_candidate_" + filtered.status,
        filtered.coset,
        filtered.operation_kind,
        root_n,
        n,
        True,
        True,
        bool(filtered.local_cost_certified),
        filtered.local_log2_cost_bound + extra,
        filtered.terminal_certified,
        filtered.children,
        accounting,
        test_count + image_candidate.permutation_candidates_checked + filtered.permutation_candidates_checked,
        (
            "rev184's second-Johnson structural leaf was closed without a label-dependent coordinate choice: the actual canonical codegree pair relation was solved in its induced action, lifted exactly to the original domain, and the remaining full string was solved inside that filter"
        ),
    )


__all__ = [
    "_replay_nonconstant_codegrees_to_pair",
    "signed_johnson_log_codegree_image_candidate_si",
]
