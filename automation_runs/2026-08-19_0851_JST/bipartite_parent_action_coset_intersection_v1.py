from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Hashable, Iterable

from coset_stabilizer_primitives import RightCoset
from paired_action_coset_preimage_v1 import paired_action_coset_preimage
from paired_bipartite_right_partition_provenance_v1 import _canonical_atom
from permutation_group_schreier import (
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
    validate_perm,
)
from proof_dag_accounting_v1 import build_candidate_si_proof_identity
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


# Instrumentation may wrap the callable, so execution identity is an explicit,
# versioned algorithm label rather than a Python function object's incidental
# module/qualname.  The rev207 entry point advances both globals together.
candidate_si_dispatcher_identity = (
    "u2_candidate_coset_string_iso_v2",
    "candidate_coset_string_isomorphism_u2",
    2,
)

if TYPE_CHECKING:
    from proof_carrying_si_v1 import ProofCarryingCoset


@dataclass(frozen=True)
class BipartiteParentActionCosetIntersection:
    status: str
    parent_degree: int
    left_size: int
    right_size: int
    auxiliary_degree: int
    right_candidate_preimage_order: int
    auxiliary_image_order: int
    image_candidate_status: str | None
    coset: RightCoset | None
    exact: bool
    exact_empty: bool
    parent_action_coupling_preserved: bool
    right_alignment_preimage_verified: bool
    quasipolynomial_cost_certified: bool
    reason: str
    image_candidate_proof: "ProofCarryingCoset | None" = None


def _palette(size: int, colors: Iterable[Hashable] | None, default) -> tuple[tuple, ...]:
    raw = tuple(default for _ in range(size)) if colors is None else tuple(colors)
    if len(raw) != size:
        raise ValueError("vertex color sequence length mismatch")
    return tuple(_canonical_atom(x) for x in raw)


def _edge_set(left_size: int, right_size: int, edges: Iterable[tuple[int, int]]) -> set[tuple[int, int]]:
    out = set()
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < left_size or not 0 <= b < right_size:
            raise ValueError("edge endpoint outside declared bipartite parts")
        out.add((a, b))
    return out


def _validate_part(points: Iterable[int], parent_degree: int, name: str) -> tuple[int, ...]:
    out = tuple(int(x) for x in points)
    if len(set(out)) != len(out):
        raise ValueError(f"{name} points must be distinct")
    if any(not 0 <= x < parent_degree for x in out):
        raise ValueError(f"{name} point outside parent domain")
    if not out:
        raise ValueError(f"{name} part must be nonempty")
    return out


def _part_action(perm, points: tuple[int, ...], index: dict[int, int]) -> tuple[int, ...] | None:
    image = []
    for x in points:
        y = perm[x]
        j = index.get(y)
        if j is None:
            return None
        image.append(j)
    return validate_perm(image)


def _auxiliary_action(
    parent_perm,
    left_points: tuple[int, ...],
    right_points: tuple[int, ...],
    left_index: dict[int, int],
    right_index: dict[int, int],
) -> tuple[int, ...] | None:
    l = len(left_points)
    r = len(right_points)
    degree = l + r + l * r
    image = [0] * degree

    for a, x in enumerate(left_points):
        y = parent_perm[x]
        b = left_index.get(y)
        if b is None:
            return None
        image[a] = b
    for b, x in enumerate(right_points):
        y = parent_perm[x]
        c = right_index.get(y)
        if c is None:
            return None
        image[l + b] = l + c
    for a, x in enumerate(left_points):
        y = parent_perm[x]
        aa = left_index.get(y)
        if aa is None:
            return None
        for b, z in enumerate(right_points):
            w = parent_perm[z]
            bb = right_index.get(w)
            if bb is None:
                return None
            old = l + r + a * r + b
            new = l + r + aa * r + bb
            image[old] = new
    return validate_perm(image)


def _auxiliary_string(
    left_size: int,
    right_size: int,
    edges: set[tuple[int, int]],
    left_colors: tuple[tuple, ...],
    right_colors: tuple[tuple, ...],
) -> tuple:
    values = []
    values.extend(("L", color) for color in left_colors)
    values.extend(("R", color) for color in right_colors)
    values.extend(
        ("E", int((a, b) in edges))
        for a in range(left_size)
        for b in range(right_size)
    )
    return tuple(values)


def intersect_parent_bipartite_string_through_right_alignment(
    parent_group,
    right_image_generators,
    right_candidate: RightCoset,
    left_points: Iterable[int],
    right_points: Iterable[int],
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    source_left_colors: Iterable[Hashable] | None = None,
    target_left_colors: Iterable[Hashable] | None = None,
    source_right_colors: Iterable[Hashable] | None = None,
    target_right_colors: Iterable[Hashable] | None = None,
    root_n: int | None = None,
    max_auxiliary_degree: int = 200000,
    max_image_group_order: int = 256,
) -> BipartiteParentActionCosetIntersection:
    """Intersect a right structural alignment with the *actual coupled parent action*.

    ``right_image_generators[i]`` must be the restriction/image of
    ``parent_group.original_generators[i]`` on the ordered ``right_points`` part.
    The generic paired-action preimage first recovers exactly the parent-group
    elements lying above ``right_candidate``.  The full colored bipartite state is
    then encoded on a disjoint auxiliary action containing all left vertices, all
    right vertices, and every cross pair.  The preimage subgroup and its fixed
    representative must preserve both parts; otherwise the caller's claimed parent
    provenance is rejected.

    Candidate-coset SI is run on the exact induced subgroup action after shifting
    the source auxiliary string through the fixed representative.  Its image coset
    is lifted back to the parent subgroup with the same generic paired Schreier
    preimage and translated into the original parent candidate.  Thus left/right
    coupling is never relaxed to an independent product action.

    Exactness here is set-theoretic.  The auxiliary domain can have size
    ``|L|+|R|+|L||R|`` and this wrapper does not yet certify the resulting call as
    a globally admissible quasipolynomial recurrence edge; that accounting remains
    a separate obligation.
    """
    n = int(parent_group.degree)
    left = _validate_part(left_points, n, "left")
    right = _validate_part(right_points, n, "right")
    if set(left) & set(right):
        raise ValueError("left and right parent parts must be disjoint")
    l = len(left)
    r = len(right)
    if right_candidate.subgroup.degree != r or len(right_candidate.representative) != r:
        raise ValueError("right candidate degree must equal the ordered right part size")

    auxiliary_degree = l + r + l * r
    if max_auxiliary_degree < 1:
        raise ValueError("max_auxiliary_degree must be positive")
    if auxiliary_degree > max_auxiliary_degree:
        return BipartiteParentActionCosetIntersection(
            "undetermined_parent_bipartite_auxiliary_degree_limit",
            n, l, r, auxiliary_degree, 0, 0, None, None,
            False, False, True, False, False,
            "the complete coupled bipartite auxiliary action exceeded the explicit degree cap",
        )

    right_preimage = paired_action_coset_preimage(
        parent_group,
        tuple(right_image_generators),
        right_candidate,
    )
    if right_preimage.status != "exact_paired_action_coset_preimage" or right_preimage.coset is None:
        return BipartiteParentActionCosetIntersection(
            "undetermined_right_alignment_parent_preimage_" + right_preimage.status,
            n, l, r, auxiliary_degree, 0, 0, None, None,
            False, False, True, False, False,
            "the supplied right candidate was not certified as a complete coset inside the paired parent-to-right action image",
        )

    parent_candidate = right_preimage.coset
    H = parent_candidate.subgroup
    rep = validate_perm(parent_candidate.representative)
    left_index = {x: i for i, x in enumerate(left)}
    right_index = {x: i for i, x in enumerate(right)}

    hgens = tuple(H.original_generators) or (identity(n),)
    aux_gens = []
    for g in hgens:
        q = _auxiliary_action(g, left, right, left_index, right_index)
        if q is None:
            return BipartiteParentActionCosetIntersection(
                "undetermined_parent_subgroup_does_not_preserve_bipartition",
                n, l, r, auxiliary_degree, H.order, 0, None, None,
                False, False, False, True, False,
                "a generator of the exact parent candidate subgroup leaves the declared left/right parts",
            )
        aux_gens.append(q)
    aux_rep = _auxiliary_action(rep, left, right, left_index, right_index)
    if aux_rep is None:
        return BipartiteParentActionCosetIntersection(
            "undetermined_parent_representative_does_not_preserve_bipartition",
            n, l, r, auxiliary_degree, H.order, 0, None, None,
            False, False, False, True, False,
            "the fixed representative of the exact parent candidate does not preserve the declared left/right parts",
        )

    source_lc = _palette(l, source_left_colors, 0)
    target_lc = _palette(l, target_left_colors, 0)
    source_rc = _palette(r, source_right_colors, 1)
    target_rc = _palette(r, target_right_colors, 1)
    source = _auxiliary_string(l, r, _edge_set(l, r, source_edges), source_lc, source_rc)
    target = _auxiliary_string(l, r, _edge_set(l, r, target_edges), target_lc, target_rc)

    aux_group = schreier_stabilizer_chain(tuple(aux_gens) or (identity(auxiliary_degree),))
    rinv = inverse(aux_rep)
    shifted_source = tuple(source[rinv[j]] for j in range(auxiliary_degree))
    image_candidate = RightCoset(aux_group, identity(auxiliary_degree))
    image_root = max(int(root_n or n), auxiliary_degree)
    image_identity = build_candidate_si_proof_identity(
        image_candidate,
        shifted_source,
        target,
        root_n=image_root,
        dispatcher_identity=candidate_si_dispatcher_identity,
        max_group_order=max_image_group_order,
    )
    image_si = candidate_coset_string_isomorphism_u2(
        image_candidate,
        shifted_source,
        target,
        root_n=image_root,
        max_group_order=max_image_group_order,
        proof_identity=image_identity,
    )
    if not image_si.exact:
        return BipartiteParentActionCosetIntersection(
            "undetermined_parent_bipartite_image_si_" + image_si.status,
            n, l, r, auxiliary_degree, H.order, aux_group.order, image_si.status, None,
            False, False, True, True, False,
            "the exact coupled auxiliary action reached an unresolved candidate-coset String Isomorphism child",
            image_si,
        )
    if image_si.coset is None:
        return BipartiteParentActionCosetIntersection(
            "exact_empty_parent_bipartite_candidate",
            n, l, r, auxiliary_degree, H.order, aux_group.order, image_si.status, None,
            True, True, True, True, False,
            "the full colored bipartite string is exactly empty inside the parent-group preimage of the right structural alignment",
            image_si,
        )

    lifted = paired_action_coset_preimage(H, tuple(aux_gens), image_si.coset)
    if lifted.status != "exact_paired_action_coset_preimage" or lifted.coset is None:
        return BipartiteParentActionCosetIntersection(
            "undetermined_parent_bipartite_auxiliary_preimage_" + lifted.status,
            n, l, r, auxiliary_degree, H.order, aux_group.order, image_si.status, None,
            False, False, True, True, False,
            "the exact auxiliary String Isomorphism result could not be lifted back through the coupled parent subgroup action",
            image_si,
        )

    result = RightCoset(
        lifted.coset.subgroup,
        compose(rep, lifted.coset.representative),
    )
    return BipartiteParentActionCosetIntersection(
        "exact_parent_bipartite_coset_intersection",
        n, l, r, auxiliary_degree, H.order, aux_group.order, image_si.status, result,
        True, False, True, True, False,
        "the right structural alignment was exactly lifted into the actual parent group, intersected with the complete colored bipartite incidence string under the coupled left/right action, and lifted back to an exact parent subcoset",
        image_si,
    )
