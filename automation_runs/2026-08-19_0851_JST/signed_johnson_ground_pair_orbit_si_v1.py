from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations
from math import log2

from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from signed_johnson_ground_pair_relation_si_v1 import signed_johnson_ground_pair_relation_si
from signed_johnson_ground_profile_partition_si_v1 import _parity_kernel


@dataclass(frozen=True)
class SignedGroundPairOrbitProof(ProofCarryingCoset):
    ground_size: int = 0
    subset_size: int = 0
    pair_relation_orbit_states: int = 0
    pair_relation_determines_string: bool = False
    complement_in_image: bool = False


@dataclass(frozen=True)
class _RelationTransport:
    status: str
    orbit_states: int
    transporter: tuple[int, ...] | None
    transporter_parity: bool
    stabilizer: object | None
    parity_kernel: object | None
    odd_stabilizer_witness: tuple[int, ...] | None
    action_steps: int
    reason: str


def _act_pair_state(state, sigma, pairs, pair_index):
    out = [None] * len(pairs)
    for i, (a, b) in enumerate(pairs):
        image = tuple(sorted((sigma[a], sigma[b])))
        out[pair_index[image]] = state[i]
    if any(x is None for x in out):
        raise AssertionError("ground permutation failed to act on every unordered pair")
    return tuple(out)


def _signed_pair_relation_transporter(group, lifted_generators, source_state, target_state, v, *, max_states):
    pairs = tuple(combinations(range(v), 2))
    pair_index = {pair: i for i, pair in enumerate(pairs)}
    domain_gens = tuple(group.original_generators)
    lifted = tuple(lifted_generators)
    if len(domain_gens) != len(lifted):
        raise AssertionError("Johnson lift did not preserve the ambient generator list")
    if not domain_gens:
        domain_gens = (identity(group.degree),)
        lifted = ((identity(v), False),)

    ground_gens = []
    parity_bits = []
    for item in lifted:
        if hasattr(item, "ground_permutation"):
            ground_gens.append(tuple(item.ground_permutation))
            parity_bits.append(bool(item.complement))
        else:
            ground_gens.append(tuple(item[0]))
            parity_bits.append(bool(item[1]))

    ident = identity(group.degree)
    trans = {tuple(source_state): ident}
    trans_parity = {tuple(source_state): False}
    queue = deque([tuple(source_state)])
    action_steps = 0

    while queue:
        state = queue.popleft()
        tx = trans[state]
        px = trans_parity[state]
        for generator, sigma, bit in zip(domain_gens, ground_gens, parity_bits):
            action_steps += 1
            nxt = _act_pair_state(state, sigma, pairs, pair_index)
            if nxt not in trans:
                if len(trans) >= max_states:
                    return _RelationTransport(
                        "undetermined_signed_ground_pair_relation_orbit_limit",
                        len(trans), None, False, None, None, None, action_steps,
                        "canonical pair-relation orbit exceeded the configured polynomial state cap",
                    )
                trans[nxt] = compose(tx, generator)
                trans_parity[nxt] = bool(px) ^ bool(bit)
                queue.append(nxt)

    stabilizer_map = {}
    for state, tx in tuple(trans.items()):
        px = trans_parity[state]
        for generator, sigma, bit in zip(domain_gens, ground_gens, parity_bits):
            nxt = _act_pair_state(state, sigma, pairs, pair_index)
            ty = trans[nxt]
            py = trans_parity[nxt]
            h = compose(compose(tx, generator), inverse(ty))
            hbit = bool(px) ^ bool(bit) ^ bool(py)
            if h == ident:
                if hbit:
                    raise AssertionError("faithful signed action assigned odd parity to identity")
                continue
            previous = stabilizer_map.get(h)
            if previous is not None and previous != hbit:
                raise AssertionError("complement parity is not a homomorphism on pair-relation stabilizer")
            stabilizer_map[h] = hbit

    stabilizer_pairs = tuple(stabilizer_map.items())
    stabilizer = schreier_stabilizer_chain([g for g, _ in stabilizer_pairs] or [ident])
    parity_kernel, odd_witness = _parity_kernel(stabilizer_pairs, group.degree)

    target_state = tuple(target_state)
    if target_state not in trans:
        return _RelationTransport(
            "no_signed_ground_pair_relation_transporter",
            len(trans), None, False, stabilizer, parity_kernel, odd_witness,
            action_steps,
            "target canonical pair relation is outside the complete bounded ambient orbit",
        )
    return _RelationTransport(
        "signed_ground_pair_relation_transporter_coset",
        len(trans), trans[target_state], trans_parity[target_state],
        stabilizer, parity_kernel, odd_witness, action_steps,
        "complete bounded pair-relation orbit returned an exact original-domain transporter and stabilizer",
    )


def _maps_string(source, target, permutation):
    return all(source[i] == target[permutation[i]] for i in range(len(source)))


def _stabilizes_string(source, permutation):
    return all(source[i] == source[permutation[i]] for i in range(len(source)))


def _proof(status, coset, *, root_n, m, exact, cost, bound, terminal, accounting, reason,
           v, k, states=0, determines=False, complement=False, checked=0):
    return SignedGroundPairOrbitProof(
        status, coset, "signed_johnson_ground_pair_relation_orbit",
        root_n, m, True, exact, cost, bound, terminal, (), accounting, checked, reason,
        ground_size=v,
        subset_size=k,
        pair_relation_orbit_states=states,
        pair_relation_determines_string=determines,
        complement_in_image=complement,
    )


def signed_johnson_ground_pair_relation_orbit_si(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    relation_state_poly_power: int = 3,
    max_relation_states: int = 50000,
    max_recognition_nodes: int = 500000,
):
    """Bounded relational-orbit closure layered on rev178's canonical pair lift.

    The orbit search ranges over labeled canonical pair relations, not over group
    elements.  Therefore a large represented signed group can still be handled
    when the number of distinct pair-relation images is polynomially bounded.
    Original-domain transporters and the complement homomorphism are carried by
    Schreier reconstruction.  For k=2 away from the exceptional complement case,
    the pair signature contains the actual color of each 2-subset, so equality of
    the pair relation is exactly equality of the original string and the resulting
    right coset is an exact SI terminal.  Other k remain exact candidate filters.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    m = group.degree
    if root_n is None:
        root_n = m
    if root_n < m or relation_state_poly_power < 1 or max_relation_states < 1:
        raise ValueError("invalid root/state-bound parameters")

    base = signed_johnson_ground_pair_relation_si(
        group, source, target, root_n=root_n, max_recognition_nodes=max_recognition_nodes
    )
    if base.exact and base.terminal_certified:
        return _proof(
            base.status, base.coset, root_n=root_n, m=m, exact=True,
            cost=base.local_cost_certified, bound=base.local_log2_cost_bound,
            terminal=True, accounting=base.accounting, reason=base.reason,
            v=base.ground_size, k=base.subset_size,
            determines=False, complement=base.complement_in_image,
            checked=base.permutation_candidates_checked,
        )
    if not base.pair_relation_nontrivial or not base.strict_ground_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, base.ground_size or m),
            operation_kind="signed_johnson_ground_pair_relation_orbit_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="rev178 did not expose a nontrivial strictly smaller pair relation",
        )
        return _proof(
            "undetermined_signed_ground_pair_relation_orbit_no_input", None,
            root_n=root_n, m=m, exact=False, cost=False, bound=0.0,
            terminal=False, accounting=accounting, reason=accounting.reason,
            v=base.ground_size, k=base.subset_size,
            complement=base.complement_in_image,
        )

    lift = lift_primitive_johnson_to_ground_relation(
        group, source, target, max_recognition_nodes=max_recognition_nodes
    )
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, base.ground_size),
            operation_kind="signed_johnson_ground_pair_relation_orbit_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="second Johnson lift for relation-orbit transport was not certified",
        )
        return _proof(
            "undetermined_signed_ground_pair_relation_orbit_lift", None,
            root_n=root_n, m=m, exact=False, cost=False, bound=0.0,
            terminal=False, accounting=accounting, reason=lift.reason,
            v=base.ground_size, k=base.subset_size,
            complement=base.complement_in_image,
        )

    v = int(lift.ground_size)
    k = int(lift.subset_size)
    complement = any(bool(g.complement) for g in lift.lifted_generators)
    source_state = tuple(weight for _, weight in base.source_pair_weights)
    target_state = tuple(weight for _, weight in base.target_pair_weights)
    allowed_states = min(max_relation_states, max(1, root_n ** relation_state_poly_power))
    transport = _signed_pair_relation_transporter(
        group, lift.lifted_generators, source_state, target_state, v,
        max_states=allowed_states,
    )

    work_units = max(
        1,
        transport.action_steps * (len(source_state) + m + v + 1)
        + transport.orbit_states * max(1, len(group.original_generators)) * (m + 1),
    )
    local_bound = (
        base.local_log2_cost_bound
        + log2(work_units)
        + 40.0 * log2(max(2, root_n))
        + 64.0
    )

    if transport.status == "undetermined_signed_ground_pair_relation_orbit_limit":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, v),
            operation_kind="signed_johnson_ground_pair_relation_orbit_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False, reason=transport.reason,
        )
        return _proof(
            transport.status, None, root_n=root_n, m=m, exact=False, cost=False,
            bound=0.0, terminal=False, accounting=accounting, reason=transport.reason,
            v=v, k=k, states=transport.orbit_states, complement=complement,
            checked=transport.action_steps,
        )

    if transport.status == "no_signed_ground_pair_relation_transporter":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, v),
            operation_kind="signed_johnson_ground_pair_relation_orbit_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
            children=(), terminal_certified=True,
            reason="complete polynomial-capped pair-relation orbit contains no target relation",
        )
        return _proof(
            "exact_empty_signed_ground_pair_relation_orbit", None,
            root_n=root_n, m=m, exact=True, cost=True, bound=local_bound,
            terminal=True, accounting=accounting, reason=transport.reason,
            v=v, k=k, states=transport.orbit_states, complement=complement,
            checked=transport.action_steps,
        )

    if transport.status != "signed_ground_pair_relation_transporter_coset":
        raise AssertionError("unexpected pair-relation transport status")

    candidate = RightCoset(transport.stabilizer, transport.transporter)
    determines = (k == 2 and not complement)
    if not determines:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, v),
            operation_kind="signed_johnson_ground_pair_relation_orbit_filter",
            canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
            children=(), terminal_certified=False,
            reason="complete pair-relation orbit produced an exact candidate coset, but pair equality does not yet determine the full k-subset string",
        )
        return _proof(
            "verified_signed_ground_pair_relation_orbit_filter", candidate,
            root_n=root_n, m=m, exact=False, cost=True, bound=local_bound,
            terminal=False, accounting=accounting, reason=accounting.reason,
            v=v, k=k, states=transport.orbit_states, determines=False,
            complement=complement, checked=transport.action_steps,
        )

    if not group.contains(candidate.representative):
        raise AssertionError("pair-relation transporter left the ambient group")
    if not _maps_string(source, target, candidate.representative):
        raise AssertionError("k=2 pair-relation transporter does not map the original string")
    for generator in candidate.subgroup.original_generators or (identity(m),):
        if not _stabilizes_string(source, generator):
            raise AssertionError("k=2 pair-relation stabilizer does not stabilize the original string")

    accounting = RecurrenceAccountingNode(
        n=root_n, m=max(1, v),
        operation_kind="signed_johnson_ground_pair_relation_orbit_terminal",
        canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
        children=(), terminal_certified=True,
        reason="k=2 pair relation determines the full string and its complete polynomial-capped relational orbit reconstructs the exact original-domain SI coset",
    )
    return _proof(
        "exact_signed_ground_pair_relation_orbit_coset", candidate,
        root_n=root_n, m=m, exact=True, cost=True, bound=local_bound,
        terminal=True, accounting=accounting,
        reason="large represented group was avoided: only distinct canonical pair-relation images were enumerated and Schreier-composed in the original domain",
        v=v, k=k, states=transport.orbit_states, determines=True,
        complement=complement, checked=transport.action_steps,
    )
