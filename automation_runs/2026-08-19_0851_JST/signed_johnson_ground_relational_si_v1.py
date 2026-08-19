from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import log2

from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import (
    SignedJohnsonGroundGenerator,
    _induce_signed_ground_generator,
    lift_primitive_johnson_to_ground_relation,
)
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class SignedJohnsonGroundRelationalProof(ProofCarryingCoset):
    ground_size: int = 0
    subset_size: int = 0
    certified_signed_group_order: int = 0
    signed_elements_checked: int = 0
    recognition_search_nodes: int = 0


def _compose_signed(a: SignedJohnsonGroundGenerator, b: SignedJohnsonGroundGenerator):
    return SignedJohnsonGroundGenerator(
        compose(a.ground_permutation, b.ground_permutation),
        bool(a.complement) ^ bool(b.complement),
    )


def _inverse_signed(a: SignedJohnsonGroundGenerator):
    # The Johnson complement is central and involutory, so the parity bit is its
    # own inverse and commutes with every ground permutation.
    return SignedJohnsonGroundGenerator(inverse(a.ground_permutation), bool(a.complement))


def _current_domain_permutation(coordinate, p_std):
    m = len(coordinate)
    cinv = [0] * m
    for current, std in enumerate(coordinate):
        cinv[std] = current
    return tuple(cinv[p_std[coordinate[current]]] for current in range(m))


def _enumerate_signed_group_exact(lift, *, expected_order: int, max_elements: int):
    if expected_order < 1 or max_elements < 1:
        raise ValueError("orders/caps must be positive")
    if expected_order > max_elements:
        return None

    ident = SignedJohnsonGroundGenerator(identity(lift.ground_size), False)
    raw = set(lift.lifted_generators)
    raw.update(_inverse_signed(g) for g in tuple(raw))
    raw.discard(ident)
    steps = tuple(sorted(raw, key=lambda g: (g.complement, g.ground_permutation)))

    seen = {ident}
    q = deque([ident])
    while q:
        current = q.popleft()
        for step in steps:
            nxt = _compose_signed(current, step)
            if nxt in seen:
                continue
            seen.add(nxt)
            if len(seen) > expected_order:
                raise AssertionError("signed-ground BFS exceeded the faithful ambient group order")
            q.append(nxt)

    if len(seen) != expected_order:
        raise AssertionError("signed-ground BFS did not match the faithful ambient group order")
    return tuple(sorted(seen, key=lambda g: (g.complement, g.ground_permutation)))


def _proof(status, coset, *, root_n, current_degree, ground_size, subset_size,
           exact, cost_certified, local_bound, terminal, accounting, checked,
           reason, group_order, recognition_nodes):
    return SignedJohnsonGroundRelationalProof(
        status,
        coset,
        "signed_johnson_ground_relational_terminal" if exact else "signed_johnson_ground_relational_unresolved",
        root_n,
        current_degree,
        True,
        exact,
        cost_certified,
        local_bound,
        terminal,
        (),
        accounting,
        checked,
        reason,
        ground_size=ground_size,
        subset_size=subset_size,
        certified_signed_group_order=group_order,
        signed_elements_checked=checked,
        recognition_search_nodes=recognition_nodes,
    )


def signed_johnson_ground_relational_small_order_terminal(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    group_order_poly_power: int = 2,
    max_group_order: int = 4096,
    max_recognition_nodes: int = 500000,
):
    """Exact SI for a certified Johnson relation when its signed ground group is small.

    rev175 gives a faithful lift of every supplied ambient generator from the
    J(v,k) point domain to a signed ground action (sigma,c), where c is the
    exceptional complement bit only possible for v=2k.  Because rev175 also
    re-induces every generator exactly, the lift is faithful: its represented
    signed group has the same certified order as the supplied Schreier chain.

    This terminal enumerates that represented signed group, not S_v and not the
    C(v,k)-point symmetric group.  It therefore closes large-ground Johnson
    instances whenever the actual ambient group order is polynomially/hard-cap
    small.  Every signed element is induced back to the original point domain,
    exact ambient membership is rechecked, the complete colored k-subset relation
    is tested, and the exact solution set is reconstructed/audited as a right
    coset.  Larger signed groups fail closed for W1 structural/local-certificate
    recursion rather than being hidden behind a node cap.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    m = group.degree
    if len(source) != m or len(target) != m:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = m
    if root_n < m:
        raise ValueError("root_n must dominate the current Johnson domain")
    if group_order_poly_power < 1 or max_group_order < 1:
        raise ValueError("invalid signed-ground enumeration parameters")

    lift = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=max_recognition_nodes,
    )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, min(root_n, v or m)),
            operation_kind="signed_johnson_ground_unresolved",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason="rev175 did not certify a strictly smaller faithful signed Johnson ground",
        )
        return _proof(
            "undetermined_signed_johnson_ground_lift",
            None,
            root_n=root_n,
            current_degree=m,
            ground_size=v,
            subset_size=k,
            exact=False,
            cost_certified=False,
            local_bound=0.0,
            terminal=False,
            accounting=accounting,
            checked=0,
            reason=lift.reason,
            group_order=group.order,
            recognition_nodes=lift.recognition_search_nodes,
        )

    allowed_order = min(max_group_order, root_n ** group_order_poly_power)
    if group.order > allowed_order:
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=v,
            operation_kind="signed_johnson_ground_unresolved",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason="faithful signed-ground group order exceeds the polynomial/implementation enumeration cap",
        )
        return _proof(
            "undetermined_signed_ground_group_order_cap",
            None,
            root_n=root_n,
            current_degree=m,
            ground_size=v,
            subset_size=k,
            exact=False,
            cost_certified=False,
            local_bound=0.0,
            terminal=False,
            accounting=accounting,
            checked=0,
            reason="W1 must recurse on the smaller relational ground; exhaustive signed-group enumeration is forbidden above the certified cap",
            group_order=group.order,
            recognition_nodes=lift.recognition_search_nodes,
        )

    elements = _enumerate_signed_group_exact(
        lift,
        expected_order=group.order,
        max_elements=allowed_order,
    )
    if elements is None:
        raise AssertionError("small-order gate admitted signed-ground enumeration but BFS declined")

    domain_elements = []
    matches = []
    for signed in elements:
        p_std = _induce_signed_ground_generator(v, k, signed.ground_permutation, signed.complement)
        q_current = _current_domain_permutation(lift.coordinate, p_std)
        if not group.contains(q_current):
            raise AssertionError("faithfully generated signed-ground element left the supplied ambient group")
        domain_elements.append(q_current)
        if all(
            lift.source_on_standard_subsets[i]
            == lift.target_on_standard_subsets[p_std[i]]
            for i in range(m)
        ):
            matches.append(q_current)

    if len(set(domain_elements)) != group.order:
        raise AssertionError("signed-ground lift was not faithful on the enumerated ambient group")

    checked = len(elements)
    execution_units = max(1, checked * max(1, m) * max(1, k))
    local_bound = (
        log2(execution_units)
        + 16.0 * log2(max(2, v))
        + 12.0 * log2(max(2, m))
        + 32.0
    )
    if local_bound + 1e-12 < log2(max(1, execution_units)):
        raise AssertionError("signed-ground terminal charge does not dominate the executed relation scan")

    if not matches:
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=v,
            operation_kind="signed_johnson_ground_relational_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason="complete faithful signed-ground group enumeration found no colored k-subset relation isomorphism",
        )
        return _proof(
            "exact_empty_signed_johnson_ground_relation",
            None,
            root_n=root_n,
            current_degree=m,
            ground_size=v,
            subset_size=k,
            exact=True,
            cost_certified=True,
            local_bound=local_bound,
            terminal=True,
            accounting=accounting,
            checked=checked,
            reason="every represented signed-ground element was induced, ambient-checked, and tested against the full relation",
            group_order=group.order,
            recognition_nodes=lift.recognition_search_nodes,
        )

    matches = tuple(sorted(matches))
    witness = matches[0]
    translated = tuple(compose(inverse(witness), p) for p in matches)
    subgroup = schreier_stabilizer_chain(translated or (identity(m),))
    result = RightCoset(subgroup, witness)
    if subgroup.order != len(matches):
        raise AssertionError("signed-ground relation matches did not reconstruct the expected subgroup order")
    if any(not result.contains(p) for p in matches):
        raise AssertionError("reconstructed signed-ground relation coset lost an exact match")

    reconstructed = tuple(sorted(p for p in domain_elements if result.contains(p)))
    checked += len(domain_elements)
    if reconstructed != matches:
        raise AssertionError("reconstructed signed-ground relation coset differs from exact enumeration")

    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=v,
        operation_kind="signed_johnson_ground_relational_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=True,
        reason="complete faithful signed-ground enumeration plus second-pass exact coset audit",
    )
    return _proof(
        "exact_signed_johnson_ground_relation_coset",
        result,
        root_n=root_n,
        current_degree=m,
        ground_size=v,
        subset_size=k,
        exact=True,
        cost_certified=True,
        local_bound=local_bound,
        terminal=True,
        accounting=accounting,
        checked=checked,
        reason="the exact SI subset of the represented signed Johnson ground action was reconstructed as one right coset on the original domain",
        group_order=group.order,
        recognition_nodes=lift.recognition_search_nodes,
    )
