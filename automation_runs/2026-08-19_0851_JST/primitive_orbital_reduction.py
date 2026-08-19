from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from permutation_group_schreier import identity, schreier_stabilizer_chain
from giant_block_action_certificates import _block_action
from local_fullness_certificates import exact_string_stabilizer
from canonical_block_system import canonical_minimal_block_system
from canonical_orbital_size_relation import canonical_orbital_size_relation
from master_canonical_reduction import reduce_canonical_pair_structure


@dataclass(frozen=True)
class PrimitiveOrbitalReduction:
    status: str
    quotient_size: int
    quotient_group_order: int
    orbital_signature_count: int
    reduced_domain_size: Optional[int]
    johnson_ground_size: Optional[int]
    johnson_subset_size: Optional[int]
    split_classes: Tuple[Tuple[int, ...], ...]
    progress_verified: bool
    reason: str


def reduce_primitive_quotient_by_orbital_sizes(
    group,
    blocks,
    values,
    *,
    max_nodes=500000,
    max_class_fraction=0.9,
    max_johnson_nodes=500000,
) -> PrimitiveOrbitalReduction:
    """Use a canonical orbital-size coarsening on an exact primitive quotient.

    The exact string automorphism group is projected to the quotient blocks. The
    caller-visible result proceeds only if that action is primitive. Ordered-pair
    orbit cardinalities then induce a label-free canonical pair relation (rev133),
    which is passed through the coherent/Johnson reducer from rev127.

    This can expose Johnson structure in primitive rank>2 actions without naming
    individual orbitals. If equal-sized orbitals coarsen too much, the result is
    left unresolved rather than assigning arbitrary orbital colors.
    """
    blocks = tuple(tuple(b) for b in blocks)
    m = len(blocks)
    intersection = exact_string_stabilizer(group, values, max_nodes=max_nodes)
    if intersection.status == "undetermined_node_limit":
        return PrimitiveOrbitalReduction(
            "undetermined_search_limit", m, 0, 0, None, None, None, (), False,
            "exact global string-stabilizer search exceeded max_nodes",
        )
    if intersection.status == "empty_intersection":
        raise AssertionError("identity must stabilize every string")

    aut = intersection.coset.subgroup
    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    quotient_gens = [
        _block_action(g, blocks, point_to_block)
        for g in (aut.original_generators or (identity(group.degree),))
    ]
    quotient = schreier_stabilizer_chain(quotient_gens or [identity(m)])
    block_cert = canonical_minimal_block_system(quotient)
    if block_cert.status != "primitive_or_trivial":
        return PrimitiveOrbitalReduction(
            "quotient_not_primitive", m, quotient.order, 0, None, None, None, (), False,
            "quotient has intransitive/imprimitive structure and should be handled by rev131 first",
        )

    relation = canonical_orbital_size_relation(quotient)
    reduced = reduce_canonical_pair_structure(
        m,
        relation.pair_weights,
        max_class_fraction=max_class_fraction,
        max_johnson_nodes=max_johnson_nodes,
    )
    if reduced.progress_verified:
        return PrimitiveOrbitalReduction(
            "primitive_orbital_" + reduced.status,
            m,
            quotient.order,
            relation.signature_count,
            reduced.reduced_domain_size,
            reduced.johnson_ground_size,
            reduced.johnson_subset_size,
            reduced.split_classes,
            True,
            "canonical orbital-size relation produced a verified coherent/Johnson reduction: " + reduced.reason,
        )
    return PrimitiveOrbitalReduction(
        "primitive_orbital_relation_unresolved", m, quotient.order,
        relation.signature_count, None, None, None, reduced.split_classes, False,
        "canonical orbital-size relation did not yield a verified split or exact Johnson ground reduction; finer orbital/design structure remains required",
    )
