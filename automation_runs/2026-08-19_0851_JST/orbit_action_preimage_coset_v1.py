from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from block_action_preimage_coset_v1 import _paired_chain
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import (
    Permutation,
    StabilizerChain,
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
    validate_perm,
)


@dataclass(frozen=True)
class OrbitActionPreimageCoset:
    status: str
    orbit: Tuple[int, ...]
    image_order: int
    kernel_order: int
    preimage_subgroup_order: int
    representative: Optional[Permutation]
    subgroup: Optional[StabilizerChain]
    coset: Optional[RightCoset]
    reason: str


def orbit_action(p: Permutation, orbit) -> Permutation:
    O = tuple(sorted(set(int(x) for x in orbit)))
    index = {x: i for i, x in enumerate(O)}
    if not O:
        raise ValueError("orbit must be nonempty")
    images = [p[x] for x in O]
    if set(images) != set(O):
        raise ValueError("supplied subset is not invariant under permutation")
    return tuple(index[p[x]] for x in O)


def _lift_from_levels(levels, target, domain_degree):
    residual = target
    selected = []
    for base, raw_trans in levels:
        trans = dict(raw_trans)
        x = residual[base]
        if x not in trans:
            return None
        tg, tq = trans[x]
        selected.append(tg)
        residual = compose(residual, inverse(tq))
    if residual != identity(len(target)):
        return None
    out = identity(domain_degree)
    for tg in reversed(selected):
        out = compose(out, tg)
    return out


def orbit_action_preimage_coset(
    group: StabilizerChain,
    orbit,
    image_coset: RightCoset,
) -> OrbitActionPreimageCoset:
    """Lift an exact coset from one invariant orbit action to the full domain.

    Paired Schreier recursion constructs the action image and exact kernel while
    retaining full-domain words.  The child representative and every child
    subgroup generator are sifted/lifted independently.  Kernel generators plus
    lifted child-subgroup generators generate exactly the subgroup preimage, so
    the returned RightCoset is the exact full-domain preimage of `image_coset`.

    This is the composition primitive Q1 needs after solving a smaller kernel-
    orbit String-Isomorphism child.  It neither enumerates the action image nor
    claims that the child SI problem itself has already been solved efficiently.
    """
    O = tuple(sorted(set(int(x) for x in orbit)))
    if not O or any(x < 0 or x >= group.degree for x in O):
        raise ValueError("invalid invariant orbit")
    m = len(O)
    if image_coset.subgroup.degree != m or len(image_coset.representative) != m:
        raise ValueError("child coset degree does not match orbit")

    eg = identity(group.degree)
    eq = identity(m)
    domain_gens = group.original_generators or (eg,)
    try:
        image_gens = tuple(orbit_action(g, O) for g in domain_gens)
    except ValueError as exc:
        return OrbitActionPreimageCoset(
            "subset_not_invariant", O, 0, 0, 0, None, None, None, str(exc)
        )

    image = schreier_stabilizer_chain(image_gens or [eq])
    child_subgroup = image_coset.subgroup
    if not image.contains(image_coset.representative):
        return OrbitActionPreimageCoset(
            "child_representative_outside_image", O, image.order, 0, 0,
            None, None, None,
            "child coset representative is not in the orbit action image",
        )
    if any(not image.contains(g) for g in child_subgroup.original_generators):
        return OrbitActionPreimageCoset(
            "child_subgroup_outside_image", O, image.order, 0, 0,
            None, None, None,
            "child coset subgroup is not contained in the orbit action image",
        )

    levels, kernel_gens = _paired_chain(domain_gens, image_gens)
    kernel = schreier_stabilizer_chain(kernel_gens or [eg])
    if kernel.order * image.order != group.order:
        raise AssertionError("orbit action violates homomorphism order theorem")

    representative = _lift_from_levels(levels, validate_perm(image_coset.representative), group.degree)
    if representative is None:
        raise AssertionError("image-contained child representative failed paired-Schreier lift")
    if orbit_action(representative, O) != image_coset.representative:
        raise AssertionError("lifted child representative has wrong orbit image")

    lifted_subgroup_gens = list(kernel.original_generators)
    for q in child_subgroup.original_generators:
        lift = _lift_from_levels(levels, q, group.degree)
        if lift is None:
            raise AssertionError("image-contained child subgroup generator failed lift")
        if orbit_action(lift, O) != q:
            raise AssertionError("lifted child subgroup generator has wrong orbit image")
        lifted_subgroup_gens.append(lift)

    preimage_subgroup = schreier_stabilizer_chain(lifted_subgroup_gens or [eg])
    expected = kernel.order * child_subgroup.order
    if preimage_subgroup.order != expected:
        raise AssertionError("subgroup preimage violates |preimage(L)|=|kernel|*|L|")
    if any(not group.contains(g) for g in preimage_subgroup.original_generators):
        raise AssertionError("subgroup preimage escaped ambient group")

    coset = RightCoset(preimage_subgroup, representative)
    return OrbitActionPreimageCoset(
        "exact_orbit_action_coset_preimage",
        O,
        image.order,
        kernel.order,
        preimage_subgroup.order,
        representative,
        preimage_subgroup,
        coset,
        "paired-Schreier orbit action lifted the exact child coset to its exact full-domain preimage",
    )
