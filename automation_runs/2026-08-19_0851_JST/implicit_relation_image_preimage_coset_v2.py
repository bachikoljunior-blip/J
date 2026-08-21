from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from coset_stabilizer_primitives import RightCoset
from implicit_relation_image_action_v1 import ImplicitRelationImageAction
from bounded_relation_image_coset_v1 import _induced_permutation
from permutation_group_schreier import (
    Permutation,
    StabilizerChain,
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
    validate_perm,
)


@runtime_checkable
class ExactImageValueCosetContract(Protocol):
    """Structural boundary implemented by rev262's exact image-coset result."""

    status: str
    exact: bool
    complete: bool
    auxiliary_degree: int
    coset: Optional[RightCoset]


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


def _closed(
    status: str,
    *,
    n: int,
    m: int,
    reason: str,
    exact: bool = False,
    complete: bool = False,
) -> ImplicitRelationImagePreimageCoset:
    return ImplicitRelationImagePreimageCoset(
        status,
        exact,
        complete,
        n,
        m,
        0,
        0,
        None,
        None,
        None,
        reason,
    )


def _lift_image_element(
    action: ImplicitRelationImageAction,
    target_image,
) -> Optional[Permutation]:
    """Sift one auxiliary image element while retaining its original-domain word."""
    target = validate_perm(target_image)
    if len(target) != action.auxiliary_degree:
        raise ValueError("target auxiliary permutation has wrong degree")
    if action.domain_group is None or action.image_group is None or action.kernel is None:
        raise ValueError("exact rev257 action groups are required")

    residual = target
    image_identity = identity(action.auxiliary_degree)
    selected_domain: list[Permutation] = []
    for base, raw_transversal in action.paired_levels:
        transversal = dict(raw_transversal)
        point = residual[base]
        if point not in transversal:
            return None
        domain_word, image_word = transversal[point]
        selected_domain.append(domain_word)
        residual = compose(residual, inverse(image_word))
    if residual != image_identity:
        return None

    representative = identity(action.domain_degree)
    for domain_word in reversed(selected_domain):
        representative = compose(representative, domain_word)
    return representative


def _relation_signature_from_features_action(
    action: ImplicitRelationImageAction,
) -> tuple[tuple[str, int], ...]:
    """Recover the named unary/binary coordinate layout stored by rev257."""
    n = action.domain_degree
    features = tuple(action.source_features)
    if n < 0 or len(features) != action.auxiliary_degree:
        raise AssertionError("rev257 feature layout disagrees with its declared degree")
    if tuple(features[:n]) != (("point", False),) * n:
        raise AssertionError("rev257 feature layout omitted the faithful neutral point layer")

    offset = n
    signature: list[tuple[str, int]] = []
    while offset < len(features):
        feature = features[offset]
        if not isinstance(feature, tuple) or len(feature) != 2 or not isinstance(feature[0], str):
            raise AssertionError("rev257 relation feature coordinate is malformed")
        name = feature[0]
        run = 0
        while offset + run < len(features):
            item = features[offset + run]
            if not isinstance(item, tuple) or len(item) != 2 or item[0] != name:
                break
            run += 1
        if run == n:
            arity = 1
        elif run == n * n:
            arity = 2
        else:
            raise AssertionError("rev257 feature layout is not a named unary/binary incidence string")
        signature.append((name, arity))
        offset += run
    return tuple(signature)


def exact_implicit_relation_image_preimage_coset(
    action: ImplicitRelationImageAction,
    image_result: ExactImageValueCosetContract,
) -> ImplicitRelationImagePreimageCoset:
    """Lift a complete exact auxiliary right coset to the original domain.

    Rev257 stores a paired Schreier chain for the original-domain -> faithful
    auxiliary-image homomorphism.  The rev262 contract supplies either the exact
    empty result or one representative plus the complete image-side stabilizer.
    Every required image element is lifted by paired sifting and the exact
    homomorphism kernel is adjoined, yielding the full original-domain preimage
    without group enumeration.

    This function is deliberately structural at the rev262 boundary so this
    independently claimed leaf does not import or modify the still-active
    rev262 implementation path.  Its accepted nonempty status is nevertheless
    pinned to rev262's exact contract string.
    """
    if not isinstance(action, ImplicitRelationImageAction):
        raise TypeError("action must be an ImplicitRelationImageAction")
    if not isinstance(image_result, ExactImageValueCosetContract):
        raise TypeError("image_result must implement ExactImageValueCosetContract")

    n = action.domain_degree
    m = action.auxiliary_degree
    if isinstance(image_result.auxiliary_degree, bool) or image_result.auxiliary_degree != m:
        raise ValueError("image_result auxiliary degree mismatch")
    if not isinstance(image_result.status, str):
        raise TypeError("image_result status must be a string")
    if not isinstance(image_result.exact, bool) or not isinstance(image_result.complete, bool):
        raise TypeError("image_result exact/complete flags must be booleans")

    image_exact_empty = (
        image_result.status.startswith("exact_empty_")
        and image_result.exact
        and image_result.complete
        and image_result.coset is None
    )
    action_exact_empty = action.status.startswith("exact_empty_")
    if action_exact_empty:
        if image_exact_empty:
            return _closed(
                "exact_empty_original_domain_relation_coset",
                n=n,
                m=m,
                exact=True,
                complete=True,
                reason="rev257 and the exact image-coset contract independently agree that the auxiliary transporter is empty, so its original-domain preimage is exactly empty",
            )
        return _closed(
            "undetermined_original_preimage_contradictory_exact_evidence",
            n=n,
            m=m,
            reason="an exact-empty rev257 action was paired with image evidence that did not certify the same empty outcome",
        )

    if action.status != "exact_implicit_relation_image_paired_action":
        return _closed(
            "undetermined_original_preimage_action",
            n=n,
            m=m,
            reason="original-domain lifting requires rev257's exact paired implicit image action",
        )
    if image_exact_empty:
        return _closed(
            "exact_empty_original_domain_relation_coset",
            n=n,
            m=m,
            exact=True,
            complete=True,
            reason="the complete exact auxiliary image transporter is empty, hence its original-domain preimage is exactly empty",
        )
    if not image_result.exact or not image_result.complete:
        return _closed(
            "undetermined_original_preimage_image_coset",
            n=n,
            m=m,
            reason="original-domain lifting requires a complete exact auxiliary value coset",
        )
    if image_result.status != "exact_implicit_relation_image_value_coset":
        return _closed(
            "undetermined_original_preimage_image_coset_contract",
            n=n,
            m=m,
            reason="nonempty lifting only accepts the rev262 exact image-value-coset contract",
        )
    if image_result.coset is None:
        return _closed(
            "undetermined_original_preimage_missing_coset",
            n=n,
            m=m,
            reason="a nonempty exact image-value-coset result omitted its right coset",
        )
    if action.domain_group is None or action.image_group is None or action.kernel is None:
        raise AssertionError("exact rev257 action omitted a domain/image/kernel chain")

    image_coset = image_result.coset
    image_subgroup = image_coset.subgroup
    if image_subgroup.degree != m:
        raise ValueError("image subgroup degree mismatch")
    image_representative = validate_perm(image_coset.representative)
    if len(image_representative) != m:
        raise ValueError("image coset representative degree mismatch")
    if not action.image_group.contains(image_representative):
        raise AssertionError("image representative escaped rev257's exact image group")

    image_generators = image_subgroup.original_generators or (identity(m),)
    for generator in image_generators:
        if not action.image_group.contains(generator):
            raise AssertionError("image stabilizer generator escaped rev257's exact image group")
    if action.image_group.order % image_subgroup.order != 0:
        raise AssertionError("image stabilizer order does not divide the exact image-group order")

    signature = _relation_signature_from_features_action(action)
    representative = _lift_image_element(action, image_representative)
    if representative is None:
        raise AssertionError("image representative could not be lifted through rev257's paired chain")
    if _induced_permutation(representative, signature, n) != image_representative:
        raise AssertionError("paired representative lift has the wrong auxiliary image")
    if not action.domain_group.contains(representative):
        raise AssertionError("paired representative lift escaped the original domain group")

    lifted_generators: list[Permutation] = []
    for generator in image_generators:
        lift = _lift_image_element(action, generator)
        if lift is None:
            raise AssertionError("image stabilizer generator could not be lifted")
        if _induced_permutation(lift, signature, n) != generator:
            raise AssertionError("paired stabilizer lift has the wrong auxiliary image")
        if not action.domain_group.contains(lift):
            raise AssertionError("paired stabilizer lift escaped the original domain group")
        lifted_generators.append(lift)

    domain_identity = identity(n)
    kernel_generators = action.kernel.original_generators or (domain_identity,)
    preimage_subgroup = schreier_stabilizer_chain(
        tuple(kernel_generators) + tuple(lifted_generators) or (domain_identity,)
    )

    for generator in preimage_subgroup.original_generators or (domain_identity,):
        if not action.domain_group.contains(generator):
            raise AssertionError("generated preimage subgroup escaped the original domain group")
        auxiliary = _induced_permutation(generator, signature, n)
        if not image_subgroup.contains(auxiliary):
            raise AssertionError("generated original preimage subgroup maps outside the image stabilizer")

    expected_order = action.kernel.order * image_subgroup.order
    if preimage_subgroup.order != expected_order:
        raise AssertionError("original preimage subgroup violates |preimage(K)|=|ker|*|K|")

    coset = RightCoset(preimage_subgroup, representative)
    return ImplicitRelationImagePreimageCoset(
        "exact_original_domain_relation_preimage_coset",
        True,
        True,
        n,
        m,
        image_subgroup.order,
        preimage_subgroup.order,
        representative,
        preimage_subgroup,
        coset,
        "paired Schreier sifts lifted the complete auxiliary right coset and adjoining the exact rev257 kernel reconstructed its complete original-domain preimage",
    )


__all__ = [
    "ExactImageValueCosetContract",
    "ImplicitRelationImagePreimageCoset",
    "exact_implicit_relation_image_preimage_coset",
]
