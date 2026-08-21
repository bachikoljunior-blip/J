from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Callable

from coset_stabilizer_primitives import RightCoset
from paired_action_coset_preimage_v1 import paired_action_coset_preimage
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
class PairedActionPreimageDifferential:
    status: str
    accepted: bool
    exact: bool
    complete: bool
    domain_order: int
    image_order: int
    kernel_order: int
    elements_checked: int
    direct_match_count: int
    image_match_count: int
    preimage_match_count: int
    distinct_image_match_count: int
    homomorphism_certified: bool
    reason: str


def _result(
    status: str,
    *,
    group: StabilizerChain,
    image_order: int = 0,
    kernel_order: int = 0,
    accepted: bool = False,
    exact: bool = False,
    complete: bool = False,
    checked: int = 0,
    direct: int = 0,
    image: int = 0,
    preimage: int = 0,
    distinct_image: int = 0,
    homomorphism: bool = False,
    reason: str,
) -> PairedActionPreimageDifferential:
    return PairedActionPreimageDifferential(
        status,
        bool(accepted),
        bool(exact),
        bool(complete),
        int(group.order),
        int(image_order),
        int(kernel_order),
        int(checked),
        int(direct),
        int(image),
        int(preimage),
        int(distinct_image),
        bool(homomorphism),
        reason,
    )


def _enumerate_group_exact(
    group: StabilizerChain,
    *,
    max_group_order: int,
) -> tuple[Permutation, ...] | None:
    if group.order > max_group_order:
        return None
    e = identity(group.degree)
    generators = set(group.original_generators or (e,))
    generators.update(inverse(g) for g in tuple(generators))
    generators.discard(e)
    steps = tuple(sorted(generators))
    seen = {e}
    queue = deque((e,))
    while queue:
        current = queue.popleft()
        for step in steps:
            nxt = compose(current, step)
            if nxt in seen:
                continue
            seen.add(nxt)
            if len(seen) > group.order:
                raise AssertionError(
                    "differential enumeration exceeded the certified domain order"
                )
            queue.append(nxt)
    if len(seen) != group.order:
        raise AssertionError(
            "differential enumeration missed certified domain elements"
        )
    return tuple(sorted(seen))


def verify_paired_action_coset_preimage_differential(
    group: StabilizerChain,
    image_generators,
    target_coset: RightCoset | None,
    *,
    image_of: Callable[[Permutation], Permutation],
    direct_accepts: Callable[[Permutation, Permutation], bool],
    exact_empty: bool = False,
    complete_image_result: bool = True,
    max_group_order: int = 4096,
) -> PairedActionPreimageDifferential:
    """Replay a paired-action coset preimage by bounded complete enumeration.

    This is an independent differential oracle, not a production preimage
    algorithm. Once the Schreier-certified domain order passes the explicit
    cap, it enumerates the complete domain group by generator/inverse BFS,
    independently evaluates the action image and a caller-supplied direct
    acceptance predicate, and compares those results element-for-element with
    both the target image right coset and ``paired_action_coset_preimage``.

    ``image_of`` must evaluate the intended action on an arbitrary domain
    element. ``direct_accepts`` must decide the original semantic condition
    without consulting ``target_coset`` or the returned paired preimage.
    """
    if not isinstance(group, StabilizerChain):
        raise TypeError("group must be a StabilizerChain")
    if not callable(image_of) or not callable(direct_accepts):
        raise TypeError("image_of and direct_accepts must be callable")
    if (
        isinstance(max_group_order, bool)
        or not isinstance(max_group_order, int)
        or max_group_order < 1
    ):
        raise ValueError("max_group_order must be a positive integer")
    if not isinstance(exact_empty, bool) or not isinstance(
        complete_image_result, bool
    ):
        raise ValueError("exact_empty and complete_image_result must be booleans")
    if target_coset is not None and not isinstance(target_coset, RightCoset):
        raise TypeError("target_coset must be a RightCoset or None")
    if target_coset is not None and exact_empty:
        raise ValueError("a nonempty target coset contradicts exact_empty=True")
    if not complete_image_result:
        return _result(
            "undetermined_differential_requires_complete_image_result",
            group=group,
            reason=(
                "the image result is not complete; bounded differential replay "
                "cannot promote or reinterpret it"
            ),
        )
    if target_coset is None and not exact_empty:
        return _result(
            "undetermined_differential_requires_exact_empty_or_coset",
            group=group,
            reason=(
                "a missing target coset must carry an exact-empty certificate"
            ),
        )

    domain_generators = tuple(group.original_generators)
    if not domain_generators:
        domain_generators = (identity(group.degree),)
    images = tuple(validate_perm(q) for q in image_generators)
    if len(images) != len(domain_generators):
        raise ValueError(
            "one image generator is required for every domain generator"
        )
    if not images:
        raise ValueError("image generator list cannot be empty")
    image_degree = len(images[0])
    if any(len(q) != image_degree for q in images):
        raise ValueError("image generator degree mismatch")
    if target_coset is not None and (
        target_coset.subgroup.degree != image_degree
        or len(target_coset.representative) != image_degree
    ):
        raise ValueError("target coset has wrong image degree")

    image_group = schreier_stabilizer_chain(images)
    expected_kernel_order, remainder = divmod(group.order, image_group.order)
    if remainder:
        raise AssertionError("certified domain/image orders are not divisible")
    if group.order > max_group_order:
        return _result(
            "undetermined_differential_group_order_cap",
            group=group,
            image_order=image_group.order,
            kernel_order=expected_kernel_order,
            reason=(
                "certified domain order exceeds max_group_order; no domain "
                "element, action image, or acceptance predicate was evaluated"
            ),
        )

    elements = _enumerate_group_exact(
        group, max_group_order=max_group_order
    )
    if elements is None:
        raise AssertionError("order gate admitted enumeration but BFS refused it")
    image_identity = identity(image_degree)
    domain_identity = identity(group.degree)

    mapped: dict[Permutation, Permutation] = {}
    for element in elements:
        q = validate_perm(image_of(element))
        if len(q) != image_degree:
            raise ValueError("image_of returned a permutation of the wrong degree")
        if not image_group.contains(q):
            return _result(
                "differential_action_image_outside_generated_group",
                group=group,
                image_order=image_group.order,
                kernel_order=expected_kernel_order,
                exact=True,
                complete=True,
                checked=len(mapped) + 1,
                reason=(
                    "image_of mapped a domain element outside the certified "
                    "generator image"
                ),
            )
        mapped[element] = q

    if mapped[domain_identity] != image_identity:
        return _result(
            "differential_action_identity_mismatch",
            group=group,
            image_order=image_group.order,
            kernel_order=expected_kernel_order,
            exact=True,
            complete=True,
            checked=len(elements),
            reason="image_of does not map identity to identity",
        )
    for generator, expected in zip(domain_generators, images):
        if mapped[generator] != expected:
            return _result(
                "differential_generator_pairing_mismatch",
                group=group,
                image_order=image_group.order,
                kernel_order=expected_kernel_order,
                exact=True,
                complete=True,
                checked=len(elements),
                reason=(
                    "image_of disagrees with the supplied image of a domain "
                    "generator"
                ),
            )

    for element in elements:
        q = mapped[element]
        for generator, q_generator in zip(domain_generators, images):
            child = compose(element, generator)
            expected = compose(q, q_generator)
            if mapped[child] != expected:
                return _result(
                    "differential_action_homomorphism_mismatch",
                    group=group,
                    image_order=image_group.order,
                    kernel_order=expected_kernel_order,
                    exact=True,
                    complete=True,
                    checked=len(elements),
                    reason=(
                        "image_of failed a complete generator-edge "
                        "homomorphism replay"
                    ),
                )

    fibers = Counter(mapped.values())
    if len(fibers) != image_group.order or any(
        multiplicity != expected_kernel_order
        for multiplicity in fibers.values()
    ):
        return _result(
            "differential_action_fiber_cardinality_mismatch",
            group=group,
            image_order=image_group.order,
            kernel_order=expected_kernel_order,
            exact=True,
            complete=True,
            checked=len(elements),
            homomorphism=True,
            reason=(
                "complete action replay disagrees with the certified "
                "kernel-times-image cardinality"
            ),
        )

    direct_flags = tuple(
        bool(direct_accepts(element, mapped[element]))
        for element in elements
    )
    image_flags = (
        tuple(False for _ in elements)
        if target_coset is None
        else tuple(target_coset.contains(mapped[element]) for element in elements)
    )
    direct_count = sum(direct_flags)
    image_count = sum(image_flags)
    distinct_image_count = len(
        {
            mapped[element]
            for element, accepted in zip(elements, image_flags)
            if accepted
        }
    )
    if direct_flags != image_flags:
        return _result(
            "differential_direct_image_coset_mismatch",
            group=group,
            image_order=image_group.order,
            kernel_order=expected_kernel_order,
            exact=True,
            complete=True,
            checked=len(elements),
            direct=direct_count,
            image=image_count,
            distinct_image=distinct_image_count,
            homomorphism=True,
            reason=(
                "caller-supplied direct semantics and target image-coset "
                "membership disagree element-for-element"
            ),
        )

    if target_coset is None:
        if direct_count:
            raise AssertionError(
                "exact-empty image result has direct acceptance witnesses"
            )
        return _result(
            "verified_exact_empty_paired_action_preimage_differential",
            group=group,
            image_order=image_group.order,
            kernel_order=expected_kernel_order,
            accepted=True,
            exact=True,
            complete=True,
            checked=len(elements),
            homomorphism=True,
            reason=(
                "complete domain enumeration, direct semantics, and the "
                "exact-empty image result agree"
            ),
        )

    preimage = paired_action_coset_preimage(group, images, target_coset)
    if (
        preimage.status != "exact_paired_action_coset_preimage"
        or preimage.coset is None
    ):
        return _result(
            "differential_paired_preimage_reconstruction_failed",
            group=group,
            image_order=image_group.order,
            kernel_order=expected_kernel_order,
            exact=True,
            complete=True,
            checked=len(elements),
            direct=direct_count,
            image=image_count,
            distinct_image=distinct_image_count,
            homomorphism=True,
            reason=(
                "generic paired preimage did not return an exact right coset: "
                + preimage.status
            ),
        )

    preimage_flags = tuple(preimage.coset.contains(element) for element in elements)
    preimage_count = sum(preimage_flags)
    cardinalities_agree = (
        preimage.kernel_order == expected_kernel_order
        and preimage.preimage_subgroup_order == preimage_count
        and preimage_count
        == expected_kernel_order * target_coset.subgroup.order
        and distinct_image_count == target_coset.subgroup.order
    )
    if direct_flags != preimage_flags or not cardinalities_agree:
        return _result(
            "differential_paired_preimage_set_or_order_mismatch",
            group=group,
            image_order=image_group.order,
            kernel_order=expected_kernel_order,
            exact=True,
            complete=True,
            checked=len(elements),
            direct=direct_count,
            image=image_count,
            preimage=preimage_count,
            distinct_image=distinct_image_count,
            homomorphism=True,
            reason=(
                "direct semantics, image-coset membership, and paired preimage "
                "differ in set membership or certified cardinality"
            ),
        )

    return _result(
        "verified_paired_action_coset_preimage_differential",
        group=group,
        image_order=image_group.order,
        kernel_order=expected_kernel_order,
        accepted=True,
        exact=True,
        complete=True,
        checked=len(elements),
        direct=direct_count,
        image=image_count,
        preimage=preimage_count,
        distinct_image=distinct_image_count,
        homomorphism=True,
        reason=(
            "complete bounded replay agrees on direct semantics, image right "
            "coset, and generic paired-preimage right coset"
        ),
    )


__all__ = [
    "PairedActionPreimageDifferential",
    "verify_paired_action_coset_preimage_differential",
]
