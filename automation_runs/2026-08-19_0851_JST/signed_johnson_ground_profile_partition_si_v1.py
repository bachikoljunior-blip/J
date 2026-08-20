from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from math import isfinite, log2

from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import (
    _standard_subsets,
    lift_primitive_johnson_to_ground_relation,
)
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class SignedGroundProfilePartitionProof(ProofCarryingCoset):
    ground_size: int = 0
    subset_size: int = 0
    source_ground_cells: tuple[tuple[int, ...], ...] = ()
    target_ground_cells: tuple[tuple[int, ...], ...] = ()
    largest_ground_cell: int = 0
    significant_ground_split: bool = False
    partition_orbit_states: int = 0
    compatible_parities: tuple[bool, ...] = ()
    relation_profile_determined: bool = False
    complement_in_image: bool = False


@dataclass(frozen=True)
class _PartitionTransport:
    status: str
    orbit_states: int
    transporter: tuple[int, ...] | None
    transporter_parity: bool
    stabilizer: object | None
    parity_kernel: object | None
    odd_stabilizer_witness: tuple[int, ...] | None
    action_steps: int
    reason: str


def _color_token(value):
    if value is None:
        return ("none",)
    if isinstance(value, bool):
        return ("bool", int(value))
    if isinstance(value, int) and not isinstance(value, bool):
        return ("int", int(value))
    if isinstance(value, str):
        return ("str", value)
    if isinstance(value, bytes):
        return ("bytes", value.hex())
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("non-finite float string values are not canonical")
        return ("float", value.hex())
    if isinstance(value, tuple):
        return ("tuple", tuple(_color_token(x) for x in value))
    raise ValueError(
        "W1 profile partition requires canonically serializable string values "
        "(None/bool/int/float/str/bytes/tuple)"
    )


def _histogram(tokens):
    return tuple(sorted(Counter(tokens).items()))


def _point_signatures(v, k, value_tokens, *, complement_in_image):
    subsets = _standard_subsets(v, k)
    if len(subsets) != len(value_tokens):
        raise AssertionError("standard Johnson relation length mismatch")
    signatures = []
    for a in range(v):
        star = _histogram(
            value_tokens[i] for i, subset in enumerate(subsets) if a in subset
        )
        if complement_in_image:
            if v != 2 * k:
                raise AssertionError("a complement bit is impossible away from v=2k")
            anti = _histogram(
                value_tokens[i] for i, subset in enumerate(subsets) if a not in subset
            )
            signatures.append(("signed-star",) + tuple(sorted((star, anti))))
        else:
            signatures.append(("star", star))
    return tuple(signatures)


def _ordered_cells(signatures):
    classes = {}
    for point, signature in enumerate(signatures):
        classes.setdefault(signature, []).append(point)
    ordered = tuple(
        (signature, tuple(points))
        for signature, points in sorted(classes.items(), key=lambda item: item[0])
    )
    return ordered


def _profile_table(v, k, cells, value_tokens):
    subsets = _standard_subsets(v, k)
    cell_of = [None] * v
    for cell_id, cell in enumerate(cells):
        for point in cell:
            if cell_of[point] is not None:
                raise AssertionError("ground partition overlaps")
            cell_of[point] = cell_id
    if any(x is None for x in cell_of):
        raise AssertionError("ground partition does not cover the ground")

    table = {}
    for token, subset in zip(value_tokens, subsets):
        counts = [0] * len(cells)
        for point in subset:
            counts[cell_of[point]] += 1
        profile = tuple(counts)
        previous = table.get(profile)
        if previous is None:
            table[profile] = token
        elif previous != token:
            return None
    return table


def _complement_profile(profile, cell_sizes):
    return tuple(size - count for size, count in zip(cell_sizes, profile))


def _compatible_profile_parities(source_table, target_table, cell_sizes, complement_in_image):
    if source_table is None or target_table is None:
        return ()
    allowed = []
    if source_table == target_table:
        allowed.append(False)
    if complement_in_image:
        ok = True
        for profile, token in source_table.items():
            cp = _complement_profile(profile, cell_sizes)
            if target_table.get(cp) != token:
                ok = False
                break
        if ok and len(source_table) == len(target_table):
            allowed.append(True)
    return tuple(allowed)


def _act_cells(cells, ground_permutation):
    return tuple(
        tuple(sorted(ground_permutation[x] for x in cell))
        for cell in cells
    )


def _parity_kernel(generator_pairs, degree):
    ident = identity(degree)
    pairs = tuple(generator_pairs)
    if not pairs:
        return schreier_stabilizer_chain([ident]), None

    representatives = {False: ident}
    queue = deque([False])
    while queue:
        state = queue.popleft()
        tx = representatives[state]
        for generator, bit in pairs:
            nxt = bool(state) ^ bool(bit)
            if nxt not in representatives:
                representatives[nxt] = compose(tx, generator)
                queue.append(nxt)

    kernel_gens = []
    for state, tx in tuple(representatives.items()):
        for generator, bit in pairs:
            nxt = bool(state) ^ bool(bit)
            ty = representatives[nxt]
            h = compose(compose(tx, generator), inverse(ty))
            if h != ident:
                kernel_gens.append(h)

    kernel = schreier_stabilizer_chain(kernel_gens or [ident])
    return kernel, representatives.get(True)


def _signed_partition_transporter(
    group,
    lifted_generators,
    source_cells,
    target_cells,
    *,
    max_states,
):
    source_cells = tuple(tuple(cell) for cell in source_cells)
    target_cells = tuple(tuple(cell) for cell in target_cells)
    if tuple(map(len, source_cells)) != tuple(map(len, target_cells)):
        return _PartitionTransport(
            "partition_shape_mismatch", 0, None, False, None, None, None, 0,
            "ordered signed-ground profile cells have different sizes",
        )

    domain_gens = tuple(group.original_generators)
    lifted = tuple(lifted_generators)
    if len(domain_gens) != len(lifted):
        raise AssertionError("Johnson lift did not preserve the ambient generator list")
    if not domain_gens:
        domain_gens = (identity(group.degree),)
        ground_degree = sum(len(c) for c in source_cells)
        lifted = ((identity(ground_degree), False),)

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
    trans = {source_cells: ident}
    trans_parity = {source_cells: False}
    queue = deque([source_cells])
    action_steps = 0

    while queue:
        state = queue.popleft()
        tx = trans[state]
        px = trans_parity[state]
        for generator, sigma, bit in zip(domain_gens, ground_gens, parity_bits):
            action_steps += 1
            nxt = _act_cells(state, sigma)
            if nxt not in trans:
                if len(trans) >= max_states:
                    return _PartitionTransport(
                        "undetermined_signed_ground_partition_orbit_limit",
                        len(trans), None, False, None, None, None, action_steps,
                        "signed-ground profile partition orbit exceeded the polynomial state cap",
                    )
                trans[nxt] = compose(tx, generator)
                trans_parity[nxt] = bool(px) ^ bool(bit)
                queue.append(nxt)

    stabilizer_pairs = []
    for state, tx in tuple(trans.items()):
        px = trans_parity[state]
        for generator, sigma, bit in zip(domain_gens, ground_gens, parity_bits):
            nxt = _act_cells(state, sigma)
            ty = trans[nxt]
            py = trans_parity[nxt]
            h = compose(compose(tx, generator), inverse(ty))
            hbit = bool(px) ^ bool(bit) ^ bool(py)
            if h == ident:
                if hbit:
                    raise AssertionError("faithful signed action assigned odd parity to identity")
                continue
            stabilizer_pairs.append((h, hbit))

    stabilizer = schreier_stabilizer_chain(
        [g for g, _ in stabilizer_pairs] or [ident]
    )
    parity_kernel, odd_witness = _parity_kernel(stabilizer_pairs, group.degree)

    if target_cells not in trans:
        return _PartitionTransport(
            "no_signed_ground_partition_transporter",
            len(trans), None, False, stabilizer, parity_kernel, odd_witness,
            action_steps,
            "target signed-ground profile partition is outside the exact ambient orbit",
        )

    return _PartitionTransport(
        "signed_ground_partition_transporter_coset",
        len(trans),
        trans[target_cells],
        trans_parity[target_cells],
        stabilizer,
        parity_kernel,
        odd_witness,
        action_steps,
        "complete bounded partition-orbit Schreier search returned an exact original-domain transporter and parity-aware stabilizer",
    )


def _conjugate_source_stabilizer_to_target(source_stabilizer, representative):
    """Convert source stabilizers to this repository's target-side right coset.

    `RightCoset(H, r)` contains permutations `compose(r, h)`, so after `r`
    transports source to target, `H` must stabilize the target.  The partition
    Schreier search naturally produces the source stabilizer K.  Its target-side
    copy is r K r^-1 in conventional notation, which is the composition below
    under this module's apply-left-then-right convention.
    """
    r = tuple(representative)
    rinv = inverse(r)
    generators = tuple(source_stabilizer.original_generators) or (identity(len(r)),)
    conjugated = tuple(
        compose(compose(rinv, generator), r)
        for generator in generators
    )
    return schreier_stabilizer_chain(conjugated or (identity(len(r)),))


def _maps_string(source, target, permutation):
    return all(source[i] == target[permutation[i]] for i in range(len(source)))


def _stabilizes_string(source, permutation):
    return all(source[i] == source[permutation[i]] for i in range(len(source)))


def _proof(
    status,
    coset,
    *,
    root_n,
    current_degree,
    exact,
    cost_certified,
    local_bound,
    terminal,
    accounting,
    reason,
    ground_size,
    subset_size,
    source_cells=(),
    target_cells=(),
    significant=False,
    orbit_states=0,
    compatible_parities=(),
    profile_determined=False,
    complement_in_image=False,
    checked=0,
):
    largest = max((len(c) for c in source_cells), default=0)
    return SignedGroundProfilePartitionProof(
        status,
        coset,
        "signed_johnson_ground_profile_partition",
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
        source_ground_cells=tuple(source_cells),
        target_ground_cells=tuple(target_cells),
        largest_ground_cell=largest,
        significant_ground_split=significant,
        partition_orbit_states=orbit_states,
        compatible_parities=tuple(compatible_parities),
        relation_profile_determined=profile_determined,
        complement_in_image=complement_in_image,
    )


def signed_johnson_ground_profile_partition_si(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    max_class_fraction: float = 0.9,
    partition_state_poly_power: int = 2,
    max_partition_states: int = 4096,
    max_recognition_nodes: int = 500000,
):
    """W1 exact terminal/filter from the actual colored Johnson k-subset relation.

    The point invariant is the color histogram on each Johnson star.  If the
    signed ground action contains the exceptional v=2k complement, the unordered
    pair (star histogram, anti-star histogram) is used, so the invariant survives
    either parity.  A nontrivial invariant gives a canonical ground partition.

    Unlike the rev176 small-order terminal, this routine never enumerates the
    represented signed group.  It explores only the orbit of the canonical ground
    partition, with an explicit polynomial-in-root_n state cap, while carrying
    original-domain transporters and the complement parity through Schreier
    generators.  If the complete colored k-subset relation is determined solely
    by the resulting cell-count profile, that partition plus the compatible
    parity mode is sufficient to reconstruct the exact original-domain SI coset.
    Otherwise the routine returns a verified structural filter but does not claim
    the remaining local-certificate recurrence is solved.
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
    if not (0.0 < max_class_fraction < 1.0):
        raise ValueError("max_class_fraction must be in (0,1)")
    if partition_state_poly_power < 1 or max_partition_states < 1:
        raise ValueError("invalid partition-orbit parameters")

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
            operation_kind="signed_johnson_ground_profile_unresolved",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason="Johnson ground lift was not certified",
        )
        return _proof(
            "undetermined_signed_ground_profile_lift",
            None,
            root_n=root_n,
            current_degree=m,
            exact=False,
            cost_certified=False,
            local_bound=0.0,
            terminal=False,
            accounting=accounting,
            reason=lift.reason,
            ground_size=v,
            subset_size=k,
        )

    complement_in_image = any(bool(g.complement) for g in lift.lifted_generators)
    source_tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    target_tokens = tuple(_color_token(x) for x in lift.target_on_standard_subsets)

    source_signatures = _point_signatures(
        v, k, source_tokens, complement_in_image=complement_in_image
    )
    target_signatures = _point_signatures(
        v, k, target_tokens, complement_in_image=complement_in_image
    )
    source_ordered = _ordered_cells(source_signatures)
    target_ordered = _ordered_cells(target_signatures)

    source_shape = tuple((sig, len(cell)) for sig, cell in source_ordered)
    target_shape = tuple((sig, len(cell)) for sig, cell in target_ordered)
    if source_shape != target_shape:
        local_bound = 24.0 * log2(max(2, root_n)) + 24.0
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=v,
            operation_kind="signed_johnson_ground_profile_invariant_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason="complement-safe star/anti-star color signatures have different canonical cell invariants",
        )
        return _proof(
            "exact_empty_signed_ground_profile_invariant",
            None,
            root_n=root_n,
            current_degree=m,
            exact=True,
            cost_certified=True,
            local_bound=local_bound,
            terminal=True,
            accounting=accounting,
            reason="any signed Johnson isomorphism must preserve the canonical ground signature multiset",
            ground_size=v,
            subset_size=k,
            source_cells=tuple(cell for _, cell in source_ordered),
            target_cells=tuple(cell for _, cell in target_ordered),
            complement_in_image=complement_in_image,
        )

    source_cells = tuple(cell for _, cell in source_ordered)
    target_cells = tuple(cell for _, cell in target_ordered)
    cell_sizes = tuple(map(len, source_cells))
    largest = max(cell_sizes)
    significant = (
        len(source_cells) > 1
        and largest <= max_class_fraction * v + 1e-12
    )

    source_table = _profile_table(v, k, source_cells, source_tokens)
    target_table = _profile_table(v, k, target_cells, target_tokens)
    profile_determined = source_table is not None and target_table is not None
    compatible_parities = _compatible_profile_parities(
        source_table, target_table, cell_sizes, complement_in_image
    ) if profile_determined else ()

    if profile_determined and not compatible_parities:
        local_bound = 28.0 * log2(max(2, root_n)) + 32.0
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=v,
            operation_kind="signed_johnson_ground_profile_table_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason="the full colored k-subset relation is cell-profile determined but neither signed parity matches source to target",
        )
        return _proof(
            "exact_empty_signed_ground_profile_table",
            None,
            root_n=root_n,
            current_degree=m,
            exact=True,
            cost_certified=True,
            local_bound=local_bound,
            terminal=True,
            accounting=accounting,
            reason="profile table comparison rules out every parity before ambient transporter search",
            ground_size=v,
            subset_size=k,
            source_cells=source_cells,
            target_cells=target_cells,
            significant=significant,
            compatible_parities=(),
            profile_determined=True,
            complement_in_image=complement_in_image,
        )

    if not profile_determined and not significant:
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=v,
            operation_kind="signed_johnson_ground_profile_unresolved",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason="actual colored relation is not determined by point-profile cells and no significant split was obtained",
        )
        return _proof(
            "undetermined_signed_ground_profile_no_split",
            None,
            root_n=root_n,
            current_degree=m,
            exact=False,
            cost_certified=False,
            local_bound=0.0,
            terminal=False,
            accounting=accounting,
            reason="W1 still requires a higher-order/local-certificate relation on the smaller ground",
            ground_size=v,
            subset_size=k,
            source_cells=source_cells,
            target_cells=target_cells,
            significant=False,
            profile_determined=False,
            complement_in_image=complement_in_image,
        )

    allowed_states = min(
        max_partition_states,
        max(1, root_n ** partition_state_poly_power),
    )
    transport = _signed_partition_transporter(
        group,
        lift.lifted_generators,
        source_cells,
        target_cells,
        max_states=allowed_states,
    )
    if transport.status == "undetermined_signed_ground_partition_orbit_limit":
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=v,
            operation_kind="signed_johnson_ground_profile_unresolved",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason=transport.reason,
        )
        return _proof(
            transport.status,
            None,
            root_n=root_n,
            current_degree=m,
            exact=False,
            cost_certified=False,
            local_bound=0.0,
            terminal=False,
            accounting=accounting,
            reason=transport.reason,
            ground_size=v,
            subset_size=k,
            source_cells=source_cells,
            target_cells=target_cells,
            significant=significant,
            orbit_states=transport.orbit_states,
            compatible_parities=compatible_parities,
            profile_determined=profile_determined,
            complement_in_image=complement_in_image,
        )

    execution_units = (
        max(1, len(source_tokens) * max(1, k))
        + max(1, transport.action_steps * (v + 1))
        + max(1, transport.orbit_states * max(1, len(group.original_generators)) * (m + 1))
    )
    local_bound = (
        log2(max(1, execution_units))
        + 40.0 * log2(max(2, root_n))
        + 48.0
    )

    if transport.status == "no_signed_ground_partition_transporter":
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=v,
            operation_kind="signed_johnson_ground_profile_partition_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason="complete polynomial-capped signed-ground partition orbit contains no target partition",
        )
        return _proof(
            "exact_empty_signed_ground_partition_orbit",
            None,
            root_n=root_n,
            current_degree=m,
            exact=True,
            cost_certified=True,
            local_bound=local_bound,
            terminal=True,
            accounting=accounting,
            reason=transport.reason,
            ground_size=v,
            subset_size=k,
            source_cells=source_cells,
            target_cells=target_cells,
            significant=significant,
            orbit_states=transport.orbit_states,
            compatible_parities=compatible_parities,
            profile_determined=profile_determined,
            complement_in_image=complement_in_image,
            checked=transport.action_steps,
        )

    if transport.status != "signed_ground_partition_transporter_coset":
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=v,
            operation_kind="signed_johnson_ground_profile_unresolved",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason=transport.reason,
        )
        return _proof(
            "undetermined_signed_ground_partition_transport",
            None,
            root_n=root_n,
            current_degree=m,
            exact=False,
            cost_certified=False,
            local_bound=0.0,
            terminal=False,
            accounting=accounting,
            reason=transport.reason,
            ground_size=v,
            subset_size=k,
            source_cells=source_cells,
            target_cells=target_cells,
            significant=significant,
            orbit_states=transport.orbit_states,
            compatible_parities=compatible_parities,
            profile_determined=profile_determined,
            complement_in_image=complement_in_image,
        )

    if not profile_determined:
        target_stabilizer = _conjugate_source_stabilizer_to_target(
            transport.stabilizer,
            transport.transporter,
        )
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=v,
            operation_kind="signed_johnson_ground_profile_filter",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=False,
            reason="canonical significant ground split and exact original-domain partition transporter were obtained, but the residual colored relation is not profile determined",
        )
        return _proof(
            "verified_signed_ground_profile_partition_filter",
            RightCoset(target_stabilizer, transport.transporter),
            root_n=root_n,
            current_degree=m,
            exact=False,
            cost_certified=True,
            local_bound=local_bound,
            terminal=False,
            accounting=accounting,
            reason="the next W1 local-certificate child may restrict to this exact candidate coset; no exact SI claim is made yet",
            ground_size=v,
            subset_size=k,
            source_cells=source_cells,
            target_cells=target_cells,
            significant=significant,
            orbit_states=transport.orbit_states,
            profile_determined=False,
            complement_in_image=complement_in_image,
            checked=transport.action_steps,
        )

    parity_set = set(compatible_parities)
    representative = transport.transporter
    source_subgroup = transport.stabilizer

    if parity_set == {False, True}:
        pass
    elif len(parity_set) == 1:
        desired = next(iter(parity_set))
        needed_h_parity = bool(desired) ^ bool(transport.transporter_parity)
        if not needed_h_parity:
            source_subgroup = transport.parity_kernel
        else:
            if transport.odd_stabilizer_witness is None:
                accounting = RecurrenceAccountingNode(
                    n=root_n,
                    m=v,
                    operation_kind="signed_johnson_ground_profile_partition_terminal",
                    canonical=True,
                    cost_certified=True,
                    local_log2_cost_bound=local_bound,
                    children=(),
                    terminal_certified=True,
                    reason="partition transporter exists but its stabilizer parity image cannot realize the only relation-compatible total parity",
                )
                return _proof(
                    "exact_empty_signed_ground_parity_coset",
                    None,
                    root_n=root_n,
                    current_degree=m,
                    exact=True,
                    cost_certified=True,
                    local_bound=local_bound,
                    terminal=True,
                    accounting=accounting,
                    reason="the complement-bit homomorphism excludes the only profile-compatible orientation",
                    ground_size=v,
                    subset_size=k,
                    source_cells=source_cells,
                    target_cells=target_cells,
                    significant=significant,
                    orbit_states=transport.orbit_states,
                    compatible_parities=compatible_parities,
                    profile_determined=True,
                    complement_in_image=complement_in_image,
                    checked=transport.action_steps,
                )
            # The witness stabilizes the source partition, so it acts before the
            # source-to-target transporter.  The previous order acted on target
            # coordinates and silently broke nonidentity coset completeness.
            representative = compose(transport.odd_stabilizer_witness, representative)
            source_subgroup = transport.parity_kernel
    else:
        raise AssertionError("profile-determined branch reached an impossible parity set")

    target_subgroup = _conjugate_source_stabilizer_to_target(
        source_subgroup,
        representative,
    )
    result = RightCoset(target_subgroup, representative)

    if not group.contains(result.representative):
        raise AssertionError("reconstructed profile terminal representative left the ambient group")
    if not _maps_string(source, target, result.representative):
        raise AssertionError("profile terminal representative does not map source to target")
    for generator in result.subgroup.original_generators or (identity(m),):
        if not _stabilizes_string(target, generator):
            raise AssertionError("profile terminal subgroup generator does not stabilize the target relation")

    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=v,
        operation_kind="signed_johnson_ground_profile_partition_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=True,
        reason=(
            "full colored k-subset relation is determined by canonical ground-cell profiles; "
            "bounded partition-orbit Schreier transport plus complement-parity kernel reconstructs the exact original-domain SI coset"
        ),
    )
    return _proof(
        "exact_signed_ground_profile_partition_coset",
        result,
        root_n=root_n,
        current_degree=m,
        exact=True,
        cost_certified=True,
        local_bound=local_bound,
        terminal=True,
        accounting=accounting,
        reason=(
            "no signed-group enumeration was used: the exact solution coset follows from the "
            "canonical star/anti-star partition, profile-determined relation, exact partition transporter, and parity-aware Schreier reconstruction"
        ),
        ground_size=v,
        subset_size=k,
        source_cells=source_cells,
        target_cells=target_cells,
        significant=significant,
        orbit_states=transport.orbit_states,
        compatible_parities=compatible_parities,
        profile_determined=True,
        complement_in_image=complement_in_image,
        checked=transport.action_steps,
    )
