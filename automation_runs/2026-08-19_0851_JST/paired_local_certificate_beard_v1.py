from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from babai_local_certificate_parameter_gate_v1 import (
    BabaiLocalCertificateParameterGate,
    babai_local_certificate_parameter_gate,
)
from coset_stabilizer_primitives import pointwise_stabilizer_chain
from paired_action_element_image_v1 import paired_action_image_of_element
from paired_affected_segment_automorphism_v1 import (
    paired_affected_segment_automorphism_group,
)
from paired_giant_action_certificates_v1 import analyze_paired_giant_action
from paired_local_certificate_test_preimage_v1 import (
    paired_local_certificate_test_preimage,
)
from permutation_group_schreier import StabilizerChain, identity


@dataclass(frozen=True)
class PairedBeardLayer:
    index: int
    input_group_order: int
    affected_before: Tuple[int, ...]
    segment_group_order: int
    structural_image_order_after: int
    giant_type_after: Optional[str]
    affected_after: Tuple[int, ...]
    quotient_nodes: int
    quotient_leaves: int
    kernel_leaf_children: int
    largest_kernel_child_domain: int
    certified_kernel_child_bound: int
    recurrence_child_bound_verified: bool


@dataclass(frozen=True)
class PairedLocalCertificateBeard:
    status: str
    structural_image_degree: int
    test_set: Tuple[int, ...]
    full: Optional[bool]
    test_preimage_group_order: int
    final_group: Optional[StabilizerChain]
    full_automorphism_subgroup: Optional[StabilizerChain]
    parameter_gate: BabaiLocalCertificateParameterGate
    layers: Tuple[PairedBeardLayer, ...]
    theorem_scale_recurrence_evidence: bool
    reason: str


def _map_subgroup_generators(parent, parent_images, subgroup):
    eg = identity(parent.degree)
    gens = tuple(subgroup.original_generators) or (eg,)
    images = []
    for g in gens:
        got = paired_action_image_of_element(parent, parent_images, g)
        if got.status != "exact_paired_action_element_image" or got.image is None:
            raise AssertionError("materialized subgroup generator could not be mapped through paired action")
        images.append(got.image)
    return gens, tuple(images)


def paired_local_certificate_beard(
    group: StabilizerChain,
    structural_image_generators,
    values,
    test_set,
    *,
    max_layers=None,
    max_quotient_leaves=2000000,
    max_child_nodes=200000,
) -> PairedLocalCertificateBeard:
    """Execute the growing-beard local-certificate dichotomy for a paired action.

    The block-specific rev161 executor is insufficient for the current Johnson
    ground because its structural homomorphism is represented generator-by-
    generator rather than by designated blocks in the source permutation domain.
    This routine preserves the exact same proof shape using the paired substrates:
    exact embedded-A(T) preimage, action-generic affected points, quotient/kernel
    segment recursion, and generator-image reconstruction after each beard layer.

    Fullness is claimed only at a stable beard when the exact paired Unaffected
    Stabilizers audit is theorem-applicable and verified. Non-fullness is exact as
    soon as a segment automorphism subgroup loses its A(T)/S(T) image. The outer
    local-certificate parameter window is tracked separately so exact small tests
    cannot be mistaken for theorem-scale quasipolynomial evidence.
    """
    vals = tuple(values)
    if len(vals) != group.degree:
        raise ValueError("string/domain size mismatch")
    images0 = tuple(tuple(int(x) for x in q) for q in structural_image_generators)
    if not images0:
        raise ValueError("structural image generators required")
    structural_degree = len(images0[0])
    T = tuple(sorted(set(int(x) for x in test_set)))
    gate = babai_local_certificate_parameter_gate(
        group.degree, structural_degree, len(T)
    )

    pre = paired_local_certificate_test_preimage(group, images0, T)
    if pre.status != "exact_paired_test_alternating_preimage" or pre.preimage_group is None:
        return PairedLocalCertificateBeard(
            pre.status, structural_degree, T, None, 0, None, None, gate, (),
            False, pre.reason,
        )

    H = pre.preimage_group
    images = pre.paired_test_image_generators
    layers = []
    recurrence_ok = True
    limit = group.degree + 1 if max_layers is None else int(max_layers)
    if limit <= 0:
        raise ValueError("max_layers must be positive")

    for layer_index in range(limit):
        before = analyze_paired_giant_action(H, images)
        if before.giant_type is None:
            return PairedLocalCertificateBeard(
                "certified_nonfull_before_segment", structural_degree, T, False,
                pre.preimage_group_order, H, None, gate, tuple(layers), False,
                "current exact paired segment subgroup already lacks an A(T)/S(T) structural image",
            )
        W = tuple(before.affected_points)
        seg = paired_affected_segment_automorphism_group(
            H, images, vals, W,
            max_quotient_leaves=max_quotient_leaves,
            max_child_nodes=max_child_nodes,
        )
        if not seg.exact or seg.subgroup is None:
            return PairedLocalCertificateBeard(
                seg.status, structural_degree, T, None, pre.preimage_group_order,
                H, None, gate, tuple(layers), False,
                "paired affected-segment recursion did not complete exactly",
            )
        H2 = seg.subgroup
        images2 = seg.paired_image_generators
        after = analyze_paired_giant_action(H2, images2)
        ex = seg.execution
        layer = PairedBeardLayer(
            layer_index, H.order, W, H2.order, after.image_order,
            after.giant_type, tuple(after.affected_points),
            0 if ex is None else ex.quotient_nodes,
            0 if ex is None else ex.quotient_leaves,
            0 if ex is None else ex.kernel_leaf_children,
            0 if ex is None else ex.largest_kernel_child_domain,
            0 if ex is None else ex.certified_kernel_child_bound,
            seg.recurrence_child_bound_verified,
        )
        layers.append(layer)
        recurrence_ok = recurrence_ok and seg.recurrence_child_bound_verified

        if after.giant_type is None:
            return PairedLocalCertificateBeard(
                "certified_nonfull_giant_obstruction", structural_degree, T,
                False, pre.preimage_group_order, H2, None, gate,
                tuple(layers), False,
                "exact automorphisms of the current affected string segment no longer contain A(T); the full-string automorphism image is a subgroup and cannot recover it",
            )

        if not set(W) <= set(after.affected_points):
            raise AssertionError("paired affected set shrank after adding string constraints")

        if tuple(after.affected_points) == W:
            if not (
                after.unaffected_stabilizer_theorem_applicable
                and after.unaffected_stabilizer_theorem_verified
            ):
                return PairedLocalCertificateBeard(
                    "stable_giant_without_unaffected_stabilizer_certificate",
                    structural_degree, T, None, pre.preimage_group_order, H2,
                    None, gate, tuple(layers), False,
                    "the paired beard stabilized, but the exact Unaffected Stabilizers theorem gate is unavailable; fullness is not claimed",
                )

            S = pointwise_stabilizer_chain(H2, after.unaffected_points)
            _Sgens, Simages = _map_subgroup_generators(H2, images2, S)
            stable_audit = analyze_paired_giant_action(S, Simages)
            if stable_audit.giant_type is None:
                raise AssertionError("materialized unaffected pointwise stabilizer lost the giant image certified by the paired audit")
            for g in tuple(S.original_generators) or (identity(S.degree),):
                if any(vals[g[x]] != vals[x] for x in range(group.degree)):
                    raise AssertionError("purported paired fullness subgroup does not preserve the full string")

            theorem_scale = bool(
                gate.certified and recurrence_ok
                and after.unaffected_stabilizer_theorem_applicable
                and after.unaffected_stabilizer_theorem_verified
            )
            return PairedLocalCertificateBeard(
                "certified_full_by_stable_paired_beard", structural_degree, T,
                True, pre.preimage_group_order, H2, S, gate, tuple(layers),
                theorem_scale,
                "the paired beard stabilized and the pointwise stabilizer of every unaffected source point retains A(T)/S(T), giving an exact full-string automorphism subgroup",
            )

        H = H2
        images = images2

    return PairedLocalCertificateBeard(
        "undetermined_beard_layer_limit", structural_degree, T, None,
        pre.preimage_group_order, H, None, gate, tuple(layers), False,
        "paired affected set kept growing beyond max_layers; fail closed",
    )
