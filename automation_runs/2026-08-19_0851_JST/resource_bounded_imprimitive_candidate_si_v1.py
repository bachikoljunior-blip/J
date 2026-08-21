from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log2

from block_action_preimage_coset_v1 import (
    lift_prepared_block_action_preimage,
    prepare_block_action_preimage,
)
from canonical_block_system import canonical_minimal_block_system
from coset_stabilizer_primitives import RightCoset
from imprimitive_quotient_kernel_resource_v1 import (
    ImprimitiveQuotientKernelResourceEnvelope,
    imprimitive_quotient_kernel_resource_envelope,
    record_imprimitive_quotient_kernel_execution,
)
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import r1_string_isomorphism_child
from proof_carrying_small_order_candidate_v1 import (
    exact_small_order_candidate_string_isomorphism,
)
from proof_carrying_state_orbit_candidate_v1 import (
    exact_state_orbit_candidate_string_isomorphism,
)
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from v2_imprimitive_small_image_v1 import (
    V2ProofCarryingCoset,
    _proof,
    _unresolved,
    enumerate_schreier_group_exact,
)


@dataclass(frozen=True)
class ResourceBoundedImprimitiveProof(V2ProofCarryingCoset):
    resource_envelope: ImprimitiveQuotientKernelResourceEnvelope | None = None


def _attach_resource(proof, envelope):
    return ResourceBoundedImprimitiveProof(
        status=proof.status,
        coset=proof.coset,
        operation_kind=proof.operation_kind,
        root_n=proof.root_n,
        domain_size=proof.domain_size,
        canonical=proof.canonical,
        exact=proof.exact,
        local_cost_certified=proof.local_cost_certified,
        local_log2_cost_bound=proof.local_log2_cost_bound,
        terminal_certified=proof.terminal_certified,
        children=tuple(proof.children),
        accounting=proof.accounting,
        permutation_candidates_checked=proof.permutation_candidates_checked,
        reason=proof.reason,
        proof_identity=proof.proof_identity,
        quotient_image_elements_checked=getattr(
            proof, "quotient_image_elements_checked", 0
        ),
        quotient_image_order=getattr(proof, "quotient_image_order", 0),
        resource_envelope=envelope,
    )


def resource_bounded_imprimitive_string_isomorphism(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    quotient_order_poly_power: int = 2,
    max_quotient_image_order: int = 4096,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 256,
    max_imprimitive_quotient_kernel_work: int,
    certified_block_system=None,
) -> ResourceBoundedImprimitiveProof:
    """Solve one unique transitive-imprimitive SI instance after full admission.

    The operator first obtains the existing canonical unique block-system
    certificate.  It then reserves the *whole* quotient/kernel phase before the
    first block action.  Once admitted, one prepared paired homomorphism is shared
    across all quotient lifts.  Each lifted kernel fiber is forced to an exact
    terminal: the existing small-order terminal when its universal kernel bound
    passes the gate, otherwise the complete reserved string-state-orbit terminal.
    The exact disjoint fiber family is finally rebuilt as one right coset.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n
    root_n = int(root_n)
    if root_n < n:
        raise ValueError("root_n must dominate current degree")
    if max_imprimitive_quotient_kernel_work <= 0:
        raise ValueError("max_imprimitive_quotient_kernel_work must be positive")

    try:
        multiplicities_match = Counter(source) == Counter(target)
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc
    if not multiplicities_match:
        base = r1_string_isomorphism_child(
            group,
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
        )
        proof = _proof(
            base.status,
            base.coset,
            base.operation_kind,
            base.root_n,
            base.domain_size,
            base.canonical,
            base.exact,
            base.local_cost_certified,
            base.local_log2_cost_bound,
            base.terminal_certified,
            base.children,
            base.accounting,
            base.permutation_candidates_checked,
            base.reason,
        )
        return _attach_resource(proof, None)

    if certified_block_system is None:
        cert = canonical_minimal_block_system(group)
        if cert.status == "multiple_canonical_minimal_block_systems":
            proof = _unresolved(
                "canonical_imprimitive_family_requires_resource_operator",
                root_n=root_n,
                degree=n,
                reason=(
                    "the resource-bounded unique-block operator cannot choose one "
                    "member of an equally canonical block-system family"
                ),
            )
            return _attach_resource(proof, None)
        if cert.status != "unique_canonical_minimal_block_system":
            proof = _unresolved(
                "not_unique_canonical_imprimitive_resource_case",
                root_n=root_n,
                degree=n,
                reason=(
                    "resource-bounded quotient/kernel execution requires one "
                    "unique canonical nontrivial block system"
                ),
            )
            return _attach_resource(proof, None)
        blocks = cert.selected_block_system
    else:
        blocks = tuple(tuple(int(point) for point in block) for block in certified_block_system)
    envelope = imprimitive_quotient_kernel_resource_envelope(
        group,
        blocks,
        target,
        original_root_degree=root_n,
        quotient_order_poly_power=quotient_order_poly_power,
        max_quotient_image_order=max_quotient_image_order,
        candidate_group_order_poly_power=candidate_group_order_poly_power,
        max_candidate_group_order=max_candidate_group_order,
        max_work=max_imprimitive_quotient_kernel_work,
    )
    if not envelope.admitted:
        proof = _unresolved(
            envelope.status,
            root_n=root_n,
            degree=n,
            reason=envelope.reason,
        )
        return _attach_resource(proof, envelope)

    prepared = prepare_block_action_preimage(group, blocks)
    image = prepared.image
    kernel = prepared.kernel
    if image.order > envelope.quotient_order_upper_bound:
        raise AssertionError("actual quotient image exceeded its universal reservation")
    if kernel.order > envelope.kernel_order_upper_bound:
        raise AssertionError("actual quotient kernel exceeded its transitive-block bound")
    if kernel.order * image.order != group.order:
        raise AssertionError("prepared block homomorphism violates |G|=|ker|*|im|")

    allowed_order = min(
        int(max_quotient_image_order),
        root_n ** int(quotient_order_poly_power),
    )
    if image.order > allowed_order:
        raise AssertionError("admitted universal quotient gate was exceeded")
    image_elements = enumerate_schreier_group_exact(
        image,
        max_elements=allowed_order,
    )
    if image_elements is None or len(image_elements) != image.order:
        raise AssertionError("exact quotient enumeration disagrees with Schreier order")

    children = []
    successful = []
    for quotient_perm in image_elements:
        lift = lift_prepared_block_action_preimage(prepared, quotient_perm)
        if lift.status != "exact_block_action_preimage_coset" or lift.coset is None:
            raise AssertionError("an enumerated quotient element lacked its exact lift")
        if lift.kernel.order != kernel.order:
            raise AssertionError("prepared quotient lifts do not share one exact kernel")

        if envelope.child_terminal_kind == "small_order":
            child = exact_small_order_candidate_string_isomorphism(
                lift.coset,
                source,
                target,
                root_n=root_n,
                group_order_poly_power=candidate_group_order_poly_power,
                max_group_order=max_candidate_group_order,
            )
        elif envelope.child_terminal_kind == "state_orbit":
            child = exact_state_orbit_candidate_string_isomorphism(
                lift.coset,
                source,
                target,
                root_n=root_n,
                max_work=envelope.child_work_per_fiber_upper_bound,
            )
        else:
            raise AssertionError("unknown admitted imprimitive child terminal")

        children.append(child)
        if not child.exact:
            raise AssertionError(
                "an admitted imprimitive quotient fiber failed its guaranteed exact terminal"
            )
        if child.coset is not None:
            successful.append(child.coset)

    envelope = record_imprimitive_quotient_kernel_execution(
        envelope,
        children,
        prepared_homomorphism_count=1,
        quotient_order=image.order,
        complete=True,
    )

    local_bound = (
        log2(max(1, envelope.work_upper_bound))
        + 20.0 * log2(max(2, n))
        + 40.0
    )
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, n),
        operation_kind="imprimitive_small_quotient",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=tuple(AccountingChild(child.accounting) for child in children),
        terminal_certified=False,
        reason=(
            "one pre-admitted prepared block homomorphism enumerated every "
            "quotient fiber, forced an exact small-order/state-orbit child, "
            "and reserved complete right-coset reassembly"
        ),
    )
    checked = len(image_elements) + sum(
        child.permutation_candidates_checked for child in children
    )

    if not successful:
        proof = _proof(
            "exact_empty_resource_bounded_imprimitive_si",
            None,
            "imprimitive_small_quotient",
            root_n,
            n,
            True,
            True,
            True,
            local_bound,
            False,
            tuple(children),
            accounting,
            checked,
            "every exactly lifted quotient fiber is empty",
            quotient_image_elements_checked=len(image_elements),
            quotient_image_order=image.order,
        )
        return _attach_resource(proof, envelope)

    r0 = successful[0].representative
    rebuild_generators = []
    expected_size = 0
    for fiber_coset in successful:
        expected_size += int(fiber_coset.subgroup.order)
        rebuild_generators.extend(fiber_coset.subgroup.original_generators)
        rebuild_generators.append(compose(inverse(r0), fiber_coset.representative))
    rebuilt = schreier_stabilizer_chain(
        rebuild_generators or (identity(n),)
    )
    if rebuilt.order != expected_size:
        raise AssertionError(
            "resource-bounded quotient fibers did not rebuild the exact union"
        )
    result = RightCoset(rebuilt, r0)
    for fiber_coset in successful:
        if not result.contains(fiber_coset.representative):
            raise AssertionError("reassembly lost a quotient-fiber representative")
        if any(
            not rebuilt.contains(generator)
            for generator in fiber_coset.subgroup.original_generators
        ):
            raise AssertionError("reassembly lost a quotient-fiber subgroup")

    proof = _proof(
        "exact_resource_bounded_imprimitive_si_coset",
        result,
        "imprimitive_small_quotient",
        root_n,
        n,
        True,
        True,
        True,
        local_bound,
        False,
        tuple(children),
        accounting,
        checked,
        (
            "the complete quotient image was lifted through one prepared paired "
            "homomorphism; every kernel fiber terminated exactly and the "
            "cardinality-audited union is one right coset"
        ),
        quotient_image_elements_checked=len(image_elements),
        quotient_image_order=image.order,
    )
    return _attach_resource(proof, envelope)


__all__ = [
    "ResourceBoundedImprimitiveProof",
    "resource_bounded_imprimitive_string_isomorphism",
]
