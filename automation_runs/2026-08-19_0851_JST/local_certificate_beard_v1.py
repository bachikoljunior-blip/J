from __future__ import annotations

from dataclasses import dataclass, replace
from math import factorial
from typing import Optional, Tuple

from affected_segment_automorphism_v2 import affected_segment_automorphism_group_v2
from affected_segment_quotient_resource_v1 import AffectedSegmentQuotientResourceEnvelope
from affected_segment_reassembly_resource_v1 import AffectedSegmentReassemblyResourceEnvelope
from babai_local_certificate_parameter_gate_v1 import (
    BabaiLocalCertificateParameterGate,
    babai_local_certificate_parameter_gate,
)
from block_action_preimage_coset_v1 import (
    lift_prepared_block_action_preimage,
    prepare_block_action_preimage,
)
from giant_block_action_certificates import analyze_giant_block_action
from giant_action_resource_envelope_v1 import (
    GiantActionResourceEnvelope,
    giant_action_resource_envelope,
)
from local_fullness_certificates import _alternating_test_generators
from local_certificate_preimage_resource_v1 import (
    PreimageSchreierResourceEnvelope,
    preimage_schreier_resource_envelope,
)
from permutation_group_schreier import StabilizerChain, identity, schreier_stabilizer_chain
from single_test_resource_envelope_v1 import (
    SingleTestResourceEnvelope,
    SingleTestResourcePhaseCharge,
    single_test_resource_envelope,
)
from unaffected_stabilizer_reduction_v1 import unaffected_stabilizer_reduction


@dataclass(frozen=True)
class BeardLayer:
    index: int
    input_group_order: int
    affected_before: Tuple[int, ...]
    segment_group_order: int
    giant_type_after: Optional[str]
    affected_after: Tuple[int, ...]
    quotient_nodes: int
    quotient_leaves: int
    kernel_leaf_children: int
    largest_kernel_child_domain: int
    certified_kernel_child_bound: int
    recurrence_child_bound_verified: bool
    segment_resource_envelope: Optional[AffectedSegmentQuotientResourceEnvelope] = None
    reassembly_resource_envelope: Optional[AffectedSegmentReassemblyResourceEnvelope] = None


@dataclass(frozen=True)
class LocalCertificateBeard:
    status: str
    test_set: Tuple[int, ...]
    full: Optional[bool]
    test_preimage_group_order: int
    final_group: Optional[StabilizerChain]
    full_automorphism_subgroup: Optional[StabilizerChain]
    parameter_gate: BabaiLocalCertificateParameterGate
    layers: Tuple[BeardLayer, ...]
    theorem_scale_recurrence_evidence: bool
    reason: str
    preimage_resource_envelope: Optional[PreimageSchreierResourceEnvelope] = None
    giant_action_resource_envelopes: Tuple[GiantActionResourceEnvelope, ...] = ()
    single_test_resource_envelope: Optional[SingleTestResourceEnvelope] = None


def _same_subgroup(a: StabilizerChain, b: StabilizerChain):
    if a.degree != b.degree or a.order != b.order:
        return False
    ea = identity(a.degree)
    return (
        all(b.contains(g) for g in (a.original_generators or (ea,)))
        and all(a.contains(g) for g in (b.original_generators or (ea,)))
    )


def _test_alternating_preimage(group, blocks, test_set):
    blocks = tuple(tuple(b) for b in blocks)
    k = len(blocks)
    T = tuple(sorted(set(int(x) for x in test_set)))
    if len(T) < 5:
        raise ValueError("growing-beard giant certificate requires at least five test points")
    if any(x < 0 or x >= k for x in T):
        raise ValueError("test-set point outside quotient")

    prepared = prepare_block_action_preimage(group, blocks)
    lifts = []
    kernel = None
    for q in _alternating_test_generators(k, T):
        lift = lift_prepared_block_action_preimage(prepared, q)
        if lift.status != "exact_block_action_preimage_coset" or lift.coset is None:
            return None, tuple(blocks[i] for i in T), "embedded A(T) generator has no quotient preimage"
        if kernel is None:
            kernel = lift.kernel
        elif not _same_subgroup(kernel, lift.kernel):
            raise AssertionError("embedded A(T) lifts disagree on the quotient kernel")
        lifts.append(lift.representative)
    if kernel is None:
        raise AssertionError("A(T) generator family unexpectedly empty")

    gens = list(kernel.original_generators)
    gens.extend(lifts)
    preimage = schreier_stabilizer_chain(gens or (identity(group.degree),))
    test_blocks = tuple(blocks[i] for i in T)
    return preimage, test_blocks, "exact preimage of embedded A(T) generated from quotient kernel and standard 3-cycle lifts"


def local_certificate_beard(
    group: StabilizerChain,
    blocks,
    values,
    test_set,
    *,
    max_layers=None,
    max_quotient_leaves=2000000,
    max_child_nodes=200000,
    max_preimage_schreier_work=None,
    max_giant_action_schreier_work=None,
    max_affected_segment_schreier_work=None,
    max_reassembly_schreier_work=None,
    max_single_test_schreier_work=None,
) -> LocalCertificateBeard:
    """Execute Babai's growing-beard local-certificate dichotomy exactly.

    We first restrict to the exact preimage of the embedded alternating group on
    the test set T (fixing quotient points outside T).  For the current giant
    subgroup H, let W be its affected set.  The next subgroup is computed exactly
    as Aut_H(x|W), but the string work is performed only after quotient recursion
    reaches the kernel, and only on affected kernel-orbit children.  Unaffected
    orbits are not sent to opaque SI terminals.

    If the quotient ceases to be giant, the global automorphism group (a subgroup
    of the current segment automorphism group) cannot contain A(T), proving
    non-fullness.  If the affected set stabilizes while the quotient remains
    giant, the exact Unaffected Stabilizer subgroup fixes the complement pointwise;
    because it also lies in Aut_H(x|W), all of its generators preserve the full
    string.  Its retained A(T) image is therefore a genuine global fullness
    certificate.

    The theorem-side parameter gate |T|>max(8,2+log2 n), |T|<=m/10 is tracked
    separately from exact correctness.  A result can be exact without being
    promoted to theorem-scale recurrence evidence.
    """
    vals = tuple(values)
    blocks = tuple(tuple(b) for b in blocks)
    T = tuple(sorted(set(int(x) for x in test_set)))
    if len(vals) != group.degree:
        raise ValueError("string/domain size mismatch")
    gate = babai_local_certificate_parameter_gate(group.degree, len(blocks), len(T))

    if max_single_test_schreier_work is not None and any(
        cap is not None for cap in (
            max_preimage_schreier_work,
            max_giant_action_schreier_work,
            max_affected_segment_schreier_work,
            max_reassembly_schreier_work,
        )
    ):
        raise ValueError("single-test cap cannot be mixed with per-phase caps")
    single_cap = (
        None if max_single_test_schreier_work is None
        else int(max_single_test_schreier_work)
    )
    if single_cap is not None and single_cap <= 0:
        raise ValueError("max_single_test_schreier_work must be positive")
    single_remaining = single_cap
    single_phases = []

    def record_single_phase(name, envelope, executed):
        nonlocal single_remaining
        if single_cap is None or envelope is None:
            return
        phase = SingleTestResourcePhaseCharge(
            name,
            int(envelope.work_upper_bound),
            bool(envelope.admitted),
            bool(executed),
        )
        single_phases.append(phase)
        if phase.admitted and phase.executed:
            if phase.work_upper_bound > single_remaining:
                raise AssertionError("admitted single-test phase exceeded remaining budget")
            single_remaining -= phase.work_upper_bound

    def finish(cert):
        if single_cap is None:
            return cert
        frozen = single_test_resource_envelope(single_cap, single_phases)
        if frozen.remaining_work != single_remaining:
            raise AssertionError("single-test ledger remaining budget mismatch")
        return replace(cert, single_test_resource_envelope=frozen)

    resource_envelope = None
    preimage_cap = (
        single_remaining if single_cap is not None
        else max_preimage_schreier_work
    )
    if preimage_cap is not None:
        resource_envelope = preimage_schreier_resource_envelope(
            group,
            len(blocks),
            len(_alternating_test_generators(len(blocks), T)),
            preimage_cap,
        )
        if not resource_envelope.admitted:
            record_single_phase("prepared_preimage", resource_envelope, False)
            return finish(LocalCertificateBeard(
                "undetermined_preimage_schreier_work_cap", T, None, 0,
                None, None, gate, (), False,
                "complete preimage Schreier work bound exceeded before execution; fail closed",
                resource_envelope,
            ))
        record_single_phase("prepared_preimage", resource_envelope, True)

    preimage, test_blocks, preimage_reason = _test_alternating_preimage(group, blocks, T)
    if preimage is None:
        return finish(LocalCertificateBeard(
            "test_alternating_preimage_unavailable", T, None, 0, None, None,
            gate, (), False, preimage_reason, resource_envelope,
        ))

    H = preimage
    layers = []
    giant_envelopes = []
    remaining_giant_work = (
        None if single_cap is not None or max_giant_action_schreier_work is None
        else int(max_giant_action_schreier_work)
    )
    if remaining_giant_work is not None and remaining_giant_work <= 0:
        raise ValueError("max_giant_action_schreier_work must be positive")

    def audited_giant_action(source):
        nonlocal remaining_giant_work
        audit_cap = single_remaining if single_cap is not None else remaining_giant_work
        if audit_cap is not None:
            envelope = giant_action_resource_envelope(source, len(test_blocks), audit_cap)
            giant_envelopes.append(envelope)
            if not envelope.admitted:
                record_single_phase("giant_action_audit", envelope, False)
                return None
            record_single_phase("giant_action_audit", envelope, True)
            if remaining_giant_work is not None:
                remaining_giant_work -= envelope.work_upper_bound
        return analyze_giant_block_action(source, test_blocks)

    current_giant = audited_giant_action(H)
    if current_giant is None:
        return finish(LocalCertificateBeard(
            "undetermined_giant_action_schreier_work_cap", T, None, preimage.order,
            H, None, gate, (), False,
            "complete structural-audit work bound exceeded before execution; fail closed",
            resource_envelope, tuple(giant_envelopes),
        ))
    expected = factorial(len(T)) // 2
    if current_giant.giant_type != "A_k" or current_giant.image_order != expected:
        return finish(LocalCertificateBeard(
            "test_alternating_preimage_unavailable", T, None, preimage.order,
            H, None, gate, (), False,
            "generated test-set preimage did not have exact A(T) quotient image",
            resource_envelope, tuple(giant_envelopes),
        ))
    recurrence_ok = True
    limit = group.degree + 1 if max_layers is None else int(max_layers)
    if limit <= 0:
        raise ValueError("max_layers must be positive")

    for layer_index in range(limit):
        before = current_giant
        if before.giant_type is None:
            return finish(LocalCertificateBeard(
                "certified_nonfull_before_segment", T, False, preimage.order,
                H, None, gate, tuple(layers), False,
                "current exact segment automorphism subgroup already lacks a giant A(T)/S(T) image", resource_envelope,
            ))
        W = tuple(before.affected_points)
        seg = affected_segment_automorphism_group_v2(
            H,
            test_blocks,
            vals,
            W,
            max_quotient_leaves=max_quotient_leaves,
            max_child_nodes=max_child_nodes,
            giant_certificate=before,
            max_quotient_schreier_work=max_affected_segment_schreier_work,
            max_reassembly_schreier_work=max_reassembly_schreier_work,
            max_combined_schreier_work=(
                single_remaining if single_cap is not None else None
            ),
        )
        segment_executed = seg.status not in {
            "undetermined_quotient_leaf_limit",
            "undetermined_quotient_schreier_work_cap",
            "undetermined_reassembly_schreier_work_cap",
        }
        record_single_phase(
            "affected_segment_quotient_kernel",
            seg.execution.resource_envelope,
            segment_executed,
        )
        record_single_phase(
            "affected_segment_parent_reassembly",
            seg.execution.reassembly_resource_envelope,
            segment_executed,
        )
        if not seg.exact or seg.subgroup is None:
            return finish(LocalCertificateBeard(
                seg.status, T, None, preimage.order, H, None, gate,
                tuple(layers), False,
                "affected-segment automorphism recursion did not complete exactly", resource_envelope,
            ))
        H2 = seg.subgroup
        after = audited_giant_action(H2)
        if after is None:
            return finish(LocalCertificateBeard(
                "undetermined_giant_action_schreier_work_cap", T, None,
                preimage.order, H2, None, gate, tuple(layers), False,
                "complete structural-audit work bound exceeded before the next layer audit; fail closed",
                resource_envelope, tuple(giant_envelopes),
            ))
        ex = seg.execution
        layer = BeardLayer(
            layer_index,
            H.order,
            W,
            H2.order,
            after.giant_type,
            tuple(after.affected_points),
            ex.quotient_nodes,
            ex.quotient_leaves,
            ex.kernel_leaf_children,
            ex.largest_kernel_child_domain,
            ex.certified_kernel_child_bound,
            seg.recurrence_child_bound_verified,
            ex.resource_envelope,
            ex.reassembly_resource_envelope,
        )
        layers.append(layer)
        recurrence_ok = recurrence_ok and seg.recurrence_child_bound_verified

        if after.giant_type is None:
            return finish(LocalCertificateBeard(
                "certified_nonfull_giant_obstruction", T, False,
                preimage.order, H2, None, gate, tuple(layers), False,
                "exact automorphisms of the current affected string segment no longer contain A(T); the full-string automorphism image is a subgroup and therefore cannot contain A(T) either", resource_envelope,
            ))

        if not set(W) <= set(after.affected_points):
            raise AssertionError("affected set shrank after adding string constraints")

        if tuple(after.affected_points) == W:
            stable = unaffected_stabilizer_reduction(H2, test_blocks, giant_certificate=after)
            if stable.status != "exact_unaffected_pointwise_stabilizer_with_giant_image" or stable.subgroup is None:
                return finish(LocalCertificateBeard(
                    "stable_giant_without_unaffected_stabilizer_certificate", T,
                    None, preimage.order, H2, None, gate, tuple(layers),
                    False,
                    "the beard stabilized, but the exact Unaffected Stabilizer theorem gate is unavailable; fullness is not claimed", resource_envelope,
                ))
            S = stable.subgroup
            for g in S.original_generators:
                if any(vals[g[x]] != vals[x] for x in range(group.degree)):
                    raise AssertionError("purported global fullness subgroup does not preserve the full string")
            theorem_scale = bool(
                gate.certified and recurrence_ok and stable.theorem_verified
            )
            return finish(LocalCertificateBeard(
                "certified_full_by_stable_beard", T, True,
                preimage.order, H2, S, gate, tuple(layers), theorem_scale,
                "the beard stabilized with a giant quotient; the pointwise stabilizer of every unaffected point still has giant image and was independently verified to preserve the entire string", resource_envelope, tuple(giant_envelopes),
            ))

        H = H2
        current_giant = after

    return finish(LocalCertificateBeard(
        "undetermined_beard_layer_limit", T, None, preimage.order, H,
        None, gate, tuple(layers), False,
        "affected set kept growing beyond max_layers; fail closed", resource_envelope,
    ))
