from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from coset_stabilizer_primitives import RightCoset
from implicit_relation_image_action_v1 import ImplicitRelationImageAction
from implicit_relation_image_value_coset_v1 import ImplicitRelationImageValueCoset
from bounded_relation_image_coset_v1 import _induced_permutation, _relation_signature
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
class ImplicitRelationImagePreimageCoset:
    status: str
    exact: bool
    complete: bool
    domain_degree: int
    auxiliary_degree: int
    image_subgroup_order: int
    preimage_subgroup_order: int
    representative: Optional[Permutation]
    subgroup: Optional[StabilizerChain]
    coset: Optional[RightCoset]
    reason: str


def _lift_image_element(
    action: ImplicitRelationImageAction,
    target_image,
) -> Optional[Permutation]:
    """Sift one auxiliary image element while retaining its domain word."""
    target = validate_perm(target_image)
    if len(target) != action.auxiliary_degree:
        raise ValueError("target auxiliary permutation has wrong degree")
    if action.domain_group is None or action.image_group is None or action.kernel is None:
        raise ValueError("exact rev257 action groups are required")

    eg = identity(action.domain_degree)
    eq = identity(action.auxiliary_degree)
    residual = target
    selected_domain = []
    for base, raw_trans in action.paired_levels:
        trans = dict(raw_trans)
        x = residual[base]
        if x not in trans:
            return None
        tg, tq = trans[x]
        selected_domain.append(tg)
        residual = compose(residual, inverse(tq))
    if residual != eq:
        return None

    representative = eg
    for tg in reversed(selected_domain):
        representative = compose(representative, tg)
    return representative


def exact_implicit_relation_image_preimage_coset(
    action: ImplicitRelationImageAction,
    image_result: ImplicitRelationImageValueCoset,
) -> ImplicitRelationImagePreimageCoset:
    """Lift rev258's complete auxiliary coset to the original domain exactly.

    Rev257 stores a paired Schreier chain for the domain->auxiliary homomorphism.
    Rev258 returns the complete value-preserving auxiliary right coset.  We lift
    its representative and every stabilizer generator through that paired chain,
    then adjoin the exact homomorphism kernel.  The generated subgroup is exactly
    the full preimage of the rev258 stabilizer, so the returned original-domain
    ``RightCoset`` is complete and does not enumerate either group.

    Original-root quasipolynomial resource accounting remains a separate child.
    """
    if not isinstance(action, ImplicitRelationImageAction):
        raise TypeError("action must be an ImplicitRelationImageAction")
    if not isinstance(image_result, ImplicitRelationImageValueCoset):
        raise TypeError("image_result must be an ImplicitRelationImageValueCoset")

    n = action.domain_degree
    m = action.auxiliary_degree
    if action.status.startswith("exact_empty_") or (
        image_result.exact and image_result.complete and image_result.coset is None
    ):
        return ImplicitRelationImagePreimageCoset(
            "exact_empty_original_domain_relation_coset", True, True, n, m,
            0, 0, None, None, None,
            "the exact auxiliary relation transporter is empty, hence its original-domain preimage is exactly empty",
        )
    if action.status != "exact_implicit_relation_image_paired_action":
        return ImplicitRelationImagePreimageCoset(
            "undetermined_original_preimage_action", False, False, n, m,
            0, 0, None, None, None,
            "original-domain lifting requires rev257's exact paired implicit image action",
        )
    if not image_result.exact or not image_result.complete:
        return ImplicitRelationImagePreimageCoset(
            "undetermined_original_preimage_image_coset", False, False, n, m,
            0, 0, None, None, None,
            "original-domain lifting requires a complete exact rev258 auxiliary value coset",
        )
    if image_result.coset is None:
        raise AssertionError("nonempty exact rev258 result omitted its coset")
    if action.domain_group is None or action.image_group is None or action.kernel is None:
        raise AssertionError("exact rev257 action omitted a domain/image/kernel chain")

    image_coset = image_result.coset
    image_subgroup = image_coset.subgroup
    if image_subgroup.degree != m:
        raise ValueError("rev258 image subgroup degree mismatch")
    if not action.image_group.contains(image_coset.representative):
        raise AssertionError("rev258 representative escaped rev257 image group")
    for generator in image_subgroup.original_generators or (identity(m),):
        if not action.image_group.contains(generator):
            raise AssertionError("rev258 stabilizer generator escaped rev257 image group")

    representative = _lift_image_element(action, image_coset.representative)
    if representative is None:
        raise AssertionError("rev258 representative could not be lifted through rev257 paired chain")

    lifted_generators = []
    for generator in image_subgroup.original_generators or (identity(m),):
        lift = _lift_image_element(action, generator)
        if lift is None:
            raise AssertionError("rev258 stabilizer generator could not be lifted")
        lifted_generators.append(lift)

    eg = identity(n)
    kernel_generators = action.kernel.original_generators or (eg,)
    preimage_subgroup = schreier_stabilizer_chain(
        tuple(kernel_generators) + tuple(lifted_generators) or (eg,)
    )

    signature = _relation_signature_from_features_action(action)
    if _induced_permutation(representative, signature, n) != image_coset.representative:
        raise AssertionError("paired representative lift has the wrong auxiliary image")
    for generator in preimage_subgroup.original_generators or (eg,):
        auxiliary = _induced_permutation(generator, signature, n)
        if not image_subgroup.contains(auxiliary):
            raise AssertionError("generated original preimage subgroup maps outside rev258 stabilizer")

    expected_order = action.kernel.order * image_subgroup.order
    if preimage_subgroup.order != expected_order:
        raise AssertionError("original preimage subgroup violates |preimage(K)|=|ker|*|K|")
    if not action.domain_group.contains(representative):
        raise AssertionError("paired representative lift escaped the original domain group")

    coset = RightCoset(preimage_subgroup, representative)
    return ImplicitRelationImagePreimageCoset(
        "exact_original_domain_relation_preimage_coset", True, True, n, m,
        image_subgroup.order, preimage_subgroup.order, representative,
        preimage_subgroup, coset,
        "paired Schreier sifts lifted the complete rev258 auxiliary right coset; adjoining the exact rev257 kernel reconstructed its complete original-domain preimage",
    )


def _relation_signature_from_features_action(
    action: ImplicitRelationImageAction,
) -> tuple[tuple[str, int], ...]:
    """Recover the unary/binary signature from rev257 feature coordinates."""
    n = action.domain_degree
    features = tuple(action.source_features)
    offset = n
    result = []
    while offset < len(features):
        name = features[offset][0]
        remaining_same_name = 0
        while offset + remaining_same_name < len(features) and features[offset + remaining_same_name][0] == name:
            remaining_same_name += 1
        if remaining_same_name == n:
            result.append((name, 1))
            offset += n
        elif remaining_same_name == n * n:
            result.append((name, 2))
            offset += n * n
        else:
            raise AssertionError("rev257 feature layout is not a named unary/binary incidence string")
    return tuple(result)


__all__ = [
    "ImplicitRelationImagePreimageCoset",
    "exact_implicit_relation_image_preimage_coset",
]
