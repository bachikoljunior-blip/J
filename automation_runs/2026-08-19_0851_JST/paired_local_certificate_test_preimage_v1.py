from __future__ import annotations

from dataclasses import dataclass
from math import factorial
from typing import Optional, Tuple

from local_fullness_certificates import _alternating_test_generators
from paired_action_subgroup_preimage_v1 import paired_action_subgroup_preimage
from permutation_group_schreier import (
    Permutation,
    StabilizerChain,
    identity,
    schreier_stabilizer_chain,
    validate_perm,
)


@dataclass(frozen=True)
class PairedLocalCertificateTestPreimage:
    status: str
    structural_image_degree: int
    test_set: Tuple[int, ...]
    test_degree: int
    source_group_order: int
    source_image_order: int
    source_kernel_order: int
    test_alternating_order: int
    preimage_group_order: int
    preimage_group: Optional[StabilizerChain]
    paired_domain_generators: Tuple[Permutation, ...]
    paired_test_image_generators: Tuple[Permutation, ...]
    reason: str


def _restrict_to_test(q, test_set):
    T = tuple(test_set)
    pos = {x: i for i, x in enumerate(T)}
    if {q[x] for x in T} != set(T):
        raise ValueError("target image generator does not preserve the test set")
    if any(q[x] != x for x in range(len(q)) if x not in pos):
        raise ValueError("target A(T) generator must fix structural-image points outside T")
    return tuple(pos[q[x]] for x in T)


def paired_local_certificate_test_preimage(
    group: StabilizerChain,
    image_generators,
    test_set,
) -> PairedLocalCertificateTestPreimage:
    """Restrict a paired structural action to the exact preimage of embedded A(T).

    Babai's local-certificate routine starts from the subgroup whose structural
    image is the alternating group on a logarithmic test set T while fixing the
    rest of the structural-image points.  For Johnson-ground and other non-block
    actions J has only a generator-paired homomorphism.  This helper constructs
    embedded A(T) in that structural image, takes its exact full-domain subgroup
    preimage, and returns a new generator pairing from the preimage group onto the
    compressed |T|-point A(T) action.  The compressed pairing can therefore be fed
    directly to the action-generic affected-point/growing-beard machinery.
    """
    domain_gens = tuple(group.original_generators) or (identity(group.degree),)
    images = tuple(validate_perm(q) for q in image_generators)
    if len(images) != len(domain_gens):
        raise ValueError("one structural image generator is required per domain generator")
    if not images:
        raise ValueError("image generator list cannot be empty")
    m = len(images[0])
    if any(len(q) != m for q in images):
        raise ValueError("structural image degree mismatch")

    T = tuple(sorted(set(int(x) for x in test_set)))
    t = len(T)
    if t < 5:
        raise ValueError("local-certificate test set must have at least five points")
    if any(x < 0 or x >= m for x in T):
        raise ValueError("test point outside structural image")

    target_gens = tuple(_alternating_test_generators(m, T))
    target = schreier_stabilizer_chain(target_gens or (identity(m),))
    expected = factorial(t) // 2
    if target.order != expected:
        raise AssertionError("standard embedded A(T) generators have the wrong order")

    pre = paired_action_subgroup_preimage(group, images, target)
    if pre.status == "target_subgroup_outside_image":
        return PairedLocalCertificateTestPreimage(
            "test_alternating_subgroup_outside_image", m, T, t, group.order,
            pre.source_image_order, pre.kernel_order, expected, 0, None, (), (),
            "the structural image does not contain the embedded alternating group on T",
        )
    if pre.status != "exact_paired_action_subgroup_preimage" or pre.preimage_subgroup is None:
        return PairedLocalCertificateTestPreimage(
            "undetermined_test_alternating_preimage", m, T, t, group.order,
            pre.source_image_order, pre.kernel_order, expected, 0, None, (), (),
            "paired subgroup preimage did not complete exactly",
        )

    local_images = tuple(
        _restrict_to_test(q, T) for q in pre.paired_image_generators
    )
    local_image = schreier_stabilizer_chain(local_images or (identity(t),))
    if local_image.order != expected:
        raise AssertionError("compressed preimage generator pairing does not regenerate A(T)")

    return PairedLocalCertificateTestPreimage(
        "exact_paired_test_alternating_preimage", m, T, t, group.order,
        pre.source_image_order, pre.kernel_order, expected,
        pre.preimage_subgroup.order, pre.preimage_subgroup,
        pre.paired_domain_generators, local_images,
        "exact embedded-A(T) subgroup preimage with a retained generator pairing onto the compressed test-set alternating action",
    )
