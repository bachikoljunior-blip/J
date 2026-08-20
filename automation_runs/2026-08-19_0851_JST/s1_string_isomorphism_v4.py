from __future__ import annotations

from math import factorial, log2

from coset_stabilizer_primitives import RightCoset
from candidate_full_accept_terminal_v1 import exact_if_entire_candidate_maps_string
from literal_giant_candidate_si_v1 import exact_literal_giant_string_isomorphism
from orbit_action_preimage_coset_v1 import orbit_action_preimage_coset
from orbit_factored_string_coset_intersection_v1 import _image_chain
from permutation_group_schreier import compose, identity, inverse
from primitive_johnson_ground_terminal_v1 import (
    primitive_johnson_ground_string_isomorphism_terminal,
)
from proof_carrying_si_v1 import r1_string_isomorphism_child
from proof_carrying_small_order_si_v1 import exact_small_order_group_string_isomorphism
from s1_string_isomorphism_v1 import _orbit_partition_parent, _structural_stop
from s1_structural_classifier_v1 import classify_s1_structure
from signed_johnson_ground_profile_partition_si_v1 import (
    signed_johnson_ground_profile_partition_si,
)


def s1_string_isomorphism_v4(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 4096,
    max_partition_states: int = 4096,
    max_recognition_nodes: int = 500000,
    max_depth: int = 64,
    _depth: int = 0,
):
    """S1 with shared full-candidate and bounded Johnson-ground terminals.

    rev213 closes the orbit children exposed by rev212's significant Johnson
    profile filter without inventing another SI search.  It reuses rev209's exact
    whole-candidate acceptance, rev208's literal natural giant terminal, rev173's
    bounded-ground Johnson terminal, and rev177's larger profile path.  Canonical
    intransitive children recurse through this same dispatcher so the terminals
    are not lost inside v1.  Transitive imprimitive children are represented as
    identity candidate cosets and returned to the existing v7 block/family
    dispatcher.  Every failed recognition or resource gate remains fail closed.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if root_n is None:
        root_n = n
    if max_partition_states < 1:
        raise ValueError("max_partition_states must be positive")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    small = exact_small_order_group_string_isomorphism(
        group,
        source,
        target,
        root_n=root_n,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
    )
    if small.exact:
        return small

    explicit = r1_string_isomorphism_child(
        group,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
    )
    if explicit.exact:
        return explicit

    accepted = exact_if_entire_candidate_maps_string(
        RightCoset(group, identity(n)),
        source,
        target,
        root_n=root_n,
    )
    if accepted.exact:
        return accepted

    giant = exact_literal_giant_string_isomorphism(
        group,
        source,
        target,
        root_n=root_n,
    )
    if giant.exact:
        return giant

    classification = classify_s1_structure(
        group,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
    )
    if _depth > max_depth:
        return _structural_stop(
            classification,
            root_n=root_n,
            reason="S1 v4 structural recursion exceeded max_depth; fail closed",
        )

    if classification.status == "canonical_intransitive_partition":
        H = group
        representative = identity(n)
        children = []
        for orbit in classification.group_orbits:
            image = _image_chain(H, orbit)
            rinv = inverse(representative)
            local_source = tuple(source[rinv[j]] for j in orbit)
            local_target = tuple(target[j] for j in orbit)
            child = s1_string_isomorphism_v4(
                image,
                local_source,
                local_target,
                root_n=root_n,
                polylog_power=polylog_power,
                max_explicit_degree=max_explicit_degree,
                group_order_poly_power=group_order_poly_power,
                max_group_order=max_group_order,
                max_partition_states=max_partition_states,
                max_recognition_nodes=max_recognition_nodes,
                max_depth=max_depth,
                _depth=_depth + 1,
            )
            children.append(child)
            if not child.exact:
                return _structural_stop(
                    classification,
                    root_n=root_n,
                    children=tuple(children),
                    reason="canonical intransitive S1 v4 parent reached an unresolved structural child",
                )
            if child.coset is None:
                return _orbit_partition_parent(
                    root_n=root_n,
                    degree=n,
                    coset=None,
                    exact=True,
                    children=tuple(children),
                    status="exact_empty_orbit_partition_v4",
                    reason="one exact S1 v4 orbit child is empty, so the complete SI coset is empty",
                )

            lifted = orbit_action_preimage_coset(H, orbit, child.coset)
            if lifted.status != "exact_orbit_action_coset_preimage" or lifted.coset is None:
                return _structural_stop(
                    classification,
                    root_n=root_n,
                    children=tuple(children),
                    reason="an exact S1 v4 orbit child could not be lifted by paired Schreier preimage",
                )
            H = lifted.subgroup
            representative = compose(representative, lifted.representative)

        return _orbit_partition_parent(
            root_n=root_n,
            degree=n,
            coset=RightCoset(H, representative),
            exact=True,
            children=tuple(children),
            status="exact_intransitive_s1_coset_v4",
            reason="every canonical orbit child recursively closed through S1 v4 and exact preimage composition",
        )

    if classification.status in {
        "canonical_imprimitive_block_system",
        "canonical_imprimitive_family",
    }:
        # Runtime import avoids the module cycle: candidate v2 uses S1 v4 for
        # orbit children, while a transitive imprimitive S1 child needs the
        # already validated candidate block/family machinery.
        from u2_candidate_coset_string_iso_v7 import candidate_coset_string_isomorphism_u7

        quotient_cap = max_group_order
        q = int(classification.quotient_degree)
        auxiliary_window = log2(max(2, root_n)) ** polylog_power
        if q <= max_explicit_degree and q <= auxiliary_window + 1e-12:
            quotient_cap = max(
                quotient_cap,
                min(root_n ** group_order_poly_power, factorial(q)),
            )

        return candidate_coset_string_isomorphism_u7(
            RightCoset(group, identity(n)),
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            group_order_poly_power=group_order_poly_power,
            max_group_order=quotient_cap,
            max_depth=max_depth,
            max_partition_states=max_partition_states,
            max_recognition_nodes=max_recognition_nodes,
        )

    if classification.status != "primitive_non_giant":
        return _structural_stop(classification, root_n=root_n)

    bounded_ground = primitive_johnson_ground_string_isomorphism_terminal(
        group,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_ground_degree=max_explicit_degree,
    )
    if bounded_ground.exact:
        return bounded_ground

    return signed_johnson_ground_profile_partition_si(
        group,
        source,
        target,
        root_n=root_n,
        max_partition_states=min(max_partition_states, max(1, root_n ** 2)),
        max_recognition_nodes=max_recognition_nodes,
    )


__all__ = ["s1_string_isomorphism_v4"]
