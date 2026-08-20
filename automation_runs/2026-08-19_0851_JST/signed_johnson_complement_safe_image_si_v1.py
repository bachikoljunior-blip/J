from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import comb, log2
from typing import Optional

from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import (
    SignedJohnsonGroundGenerator,
    _standard_subsets,
    lift_primitive_johnson_to_ground_relation,
)
from paired_action_full_candidate_filter_v1 import build_paired_action_preimage_artifact
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from recursive_point_image_coset_intersection import right_coset_intersection_recursive
from signed_johnson_ground_profile_partition_si_v1 import _color_token, _histogram


@dataclass(frozen=True)
class SignedJohnsonComplementSafeImageProof(ProofCarryingCoset):
    ground_size: int = 0
    subset_size: int = 0
    relation_arity: int = 0
    image_degree: int = 0
    image_order: int = 0
    kernel_order: int = 0
    image_si_order: int = 0
    preimage_filter_order: int = 0
    relation_rank: int = 0
    complement_in_image: bool = False
    strict_image_progress: bool = False
    relation_determines_string: bool = False
    image_search_nodes: int = 0
    image_generators: tuple[tuple[int, ...], ...] = ()
    image_coset: Optional[RightCoset] = None


def _signed_item(item):
    if isinstance(item, SignedJohnsonGroundGenerator) or hasattr(item, "ground_permutation"):
        return tuple(item.ground_permutation), bool(item.complement)
    return tuple(item[0]), bool(item[1])


def complement_safe_t_subset_image_generators(lifted_generators, v: int, t: int):
    """Induce the signed Johnson action on complement-safe t-ground-subset coordinates.

    A complement bit acts on the *k-subset colors*, not on the ground points.
    Complement-safe relation signatures below quotient that bit by identifying the
    intersection-histogram vector with its reversal.  Consequently the coordinate
    action on a t-subset T is exactly T -> sigma(T); a pure complement maps every
    relation coordinate to itself and is deliberately placed in the action kernel.

    This is the same finite-set action exposed by GAP's Action/ActionHomomorphism
    with OnSets, specialized to the proof-carrying generator pairing used in J.
    """
    v = int(v)
    t = int(t)
    if not (1 <= t <= v):
        raise ValueError("relation arity must be between 1 and the ground size")
    coords = tuple(combinations(range(v), t))
    index = {coord: i for i, coord in enumerate(coords)}
    out = []
    parity = []
    for raw in tuple(lifted_generators):
        sigma, bit = _signed_item(raw)
        if len(sigma) != v or sorted(sigma) != list(range(v)):
            raise ValueError("signed Johnson ground generator has wrong degree")
        q = tuple(index[tuple(sorted(sigma[x] for x in coord))] for coord in coords)
        out.append(q)
        parity.append(bit)
    return coords, tuple(out), tuple(parity)


def complement_safe_t_relation_signatures(
    v: int,
    k: int,
    value_tokens,
    t: int,
    *,
    complement_in_image: bool,
):
    """Canonical t-local color signatures, invariant under the exceptional complement.

    For a t-subset T of ground points, the j-th component is the histogram of
    colors of k-subsets meeting T in exactly j points.  If v=2k and the ambient
    signed Johnson image contains complement, complementing every k-subset sends
    j to t-j.  Canonicalizing the histogram vector under reversal therefore keeps
    all information available to a complement-safe t-local relation while making
    the signature equivariant under the signed action.
    """
    v = int(v)
    k = int(k)
    t = int(t)
    if not (1 <= k < v):
        raise ValueError("invalid Johnson parameters")
    if not (1 <= t <= v):
        raise ValueError("invalid relation arity")
    subsets = _standard_subsets(v, k)
    tokens = tuple(value_tokens)
    if len(tokens) != len(subsets):
        raise ValueError("value token count does not match the Johnson domain")
    if complement_in_image and v != 2 * k:
        raise ValueError("a signed complement is possible only for v=2k")

    signatures = []
    for coord in combinations(range(v), t):
        C = set(coord)
        hist = tuple(
            _histogram(
                tokens[i]
                for i, subset in enumerate(subsets)
                if len(C.intersection(subset)) == j
            )
            for j in range(t + 1)
        )
        if complement_in_image:
            rev = tuple(reversed(hist))
            signatures.append(("signed-t", min((hist, rev), key=repr)))
        else:
            signatures.append(("t", hist))
    return tuple(signatures)


def _proof(
    status,
    coset,
    *,
    root_n,
    domain_size,
    exact,
    cost,
    bound,
    terminal,
    accounting,
    reason,
    v,
    k,
    t,
    image_degree=0,
    image_order=0,
    kernel_order=0,
    image_si_order=0,
    preimage_order=0,
    relation_rank=0,
    complement=False,
    strict=False,
    determines=False,
    nodes=0,
    image_generators=(),
    image_coset=None,
):
    return SignedJohnsonComplementSafeImageProof(
        status,
        coset,
        "signed_johnson_complement_safe_relation_image",
        root_n,
        domain_size,
        True,
        exact,
        cost,
        bound,
        terminal,
        (),
        accounting,
        nodes,
        reason,
        ground_size=v,
        subset_size=k,
        relation_arity=t,
        image_degree=image_degree,
        image_order=image_order,
        kernel_order=kernel_order,
        image_si_order=image_si_order,
        preimage_filter_order=preimage_order,
        relation_rank=relation_rank,
        complement_in_image=complement,
        strict_image_progress=strict,
        relation_determines_string=determines,
        image_search_nodes=nodes,
        image_generators=tuple(tuple(q) for q in image_generators),
        image_coset=image_coset,
    )


def signed_johnson_complement_safe_relation_image_si(
    group,
    source_values,
    target_values,
    *,
    relation_arity: int = 2,
    root_n: int | None = None,
    max_recognition_nodes: int = 500000,
    image_si_poly_power: int = 4,
    max_image_si_nodes: int = 200000,
):
    """W1R-H2: solve a strictly smaller complement-safe relation image exactly.

    The current colored Johnson instance is first put in a certified standard
    J(v,k) coordinate gauge.  Its t-local complement-safe relation is then treated
    as an ordinary string on the strictly smaller t-subset image action.  Exact
    image string isomorphism is computed by intersecting that action group with
    the complete value-preserving Young coset.  A successful image RightCoset is
    lifted back to the original J(v,k) domain by rev179's paired Schreier preimage.

    The returned nonempty coset is an exact *relation* filter.  It is promoted to
    an exact original-string SI result only when the relation coordinates contain
    the original colors pointwise (t=k with no complement).  Empty image SI is an
    exact original emptiness certificate because every original isomorphism must
    preserve every canonical t-local signature.  Resource exhaustion fails closed.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    m = group.degree
    if len(source) != m or len(target) != m:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = m
    if root_n < m or image_si_poly_power < 1 or max_image_si_nodes < 1:
        raise ValueError("invalid root/image-search parameters")

    lift = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=max_recognition_nodes,
    )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    t = int(relation_arity)
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, min(root_n, v or m)),
            operation_kind="signed_johnson_relation_image_unresolved",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason="certified strictly smaller Johnson ground lift unavailable",
        )
        return _proof(
            "undetermined_signed_johnson_relation_image_lift",
            None,
            root_n=root_n,
            domain_size=m,
            exact=False,
            cost=False,
            bound=0.0,
            terminal=False,
            accounting=accounting,
            reason=lift.reason,
            v=v,
            k=k,
            t=t,
        )
    if not (1 <= t <= k):
        raise ValueError("relation arity must lie in 1..k")

    complement = any(bool(g.complement) for g in lift.lifted_generators)
    source_tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    target_tokens = tuple(_color_token(x) for x in lift.target_on_standard_subsets)
    source_signatures = complement_safe_t_relation_signatures(
        v, k, source_tokens, t, complement_in_image=complement
    )
    target_signatures = complement_safe_t_relation_signatures(
        v, k, target_tokens, t, complement_in_image=complement
    )

    image_degree = comb(v, t)
    strict = image_degree < m
    labels = {
        sig: i
        for i, sig in enumerate(
            sorted(set(source_signatures).union(target_signatures), key=repr)
        )
    }
    source_state = tuple(labels[sig] for sig in source_signatures)
    target_state = tuple(labels[sig] for sig in target_signatures)
    relation_rank = len(labels)

    scan_units = max(
        1,
        2 * image_degree * max(1, m) * max(1, t + 1) * max(1, k),
    )
    base_bound = log2(scan_units) + 48.0 * log2(max(2, root_n)) + 64.0

    if Counter(source_state) != Counter(target_state):
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, image_degree),
            operation_kind="signed_johnson_relation_image_invariant_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=base_bound,
            children=(),
            terminal_certified=True,
            reason="complement-safe t-local relation color multiplicities differ",
        )
        return _proof(
            "exact_empty_signed_johnson_relation_image_invariant",
            None,
            root_n=root_n,
            domain_size=m,
            exact=True,
            cost=True,
            bound=base_bound,
            terminal=True,
            accounting=accounting,
            reason="every signed Johnson isomorphism induces a permutation of t-local relation coordinates",
            v=v,
            k=k,
            t=t,
            image_degree=image_degree,
            relation_rank=relation_rank,
            complement=complement,
            strict=strict,
        )

    coords, image_gens, _ = complement_safe_t_subset_image_generators(
        lift.lifted_generators, v, t
    )
    if len(coords) != image_degree:
        raise AssertionError("t-subset image degree mismatch")
    if not image_gens:
        image_gens = (identity(image_degree),)
    image = schreier_stabilizer_chain(image_gens)

    value_coset = _all_value_preserving_maps(source_state, target_state)
    if value_coset is None:
        raise AssertionError("equal relation multiplicities did not produce a value-preserving coset")
    allowed_nodes = min(
        max_image_si_nodes,
        max(1, int(root_n) ** int(image_si_poly_power)),
    )
    intersection = right_coset_intersection_recursive(
        RightCoset(image, identity(image_degree)),
        value_coset,
        max_nodes=allowed_nodes,
    )
    if intersection.status == "undetermined_node_limit":
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, image_degree),
            operation_kind="signed_johnson_relation_image_unresolved",
            canonical=True,
            cost_certified=False,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=False,
            reason="exact smaller-image string intersection exhausted its polynomial node cap",
        )
        return _proof(
            "undetermined_signed_johnson_relation_image_node_limit",
            None,
            root_n=root_n,
            domain_size=m,
            exact=False,
            cost=False,
            bound=0.0,
            terminal=False,
            accounting=accounting,
            reason=intersection.reason,
            v=v,
            k=k,
            t=t,
            image_degree=image_degree,
            image_order=image.order,
            relation_rank=relation_rank,
            complement=complement,
            strict=strict,
            nodes=intersection.search_nodes,
        )

    work_units = max(
        1,
        scan_units
        + intersection.search_nodes * max(2, image_degree + m + v) ** 6,
    )
    local_bound = log2(work_units) + 64.0 * log2(max(2, root_n)) + 96.0

    if intersection.status == "empty_intersection":
        accounting = RecurrenceAccountingNode(
            n=root_n,
            m=max(1, image_degree),
            operation_kind="signed_johnson_relation_image_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason="exact t-subset image SI is empty",
        )
        return _proof(
            "exact_empty_signed_johnson_relation_image",
            None,
            root_n=root_n,
            domain_size=m,
            exact=True,
            cost=True,
            bound=local_bound,
            terminal=True,
            accounting=accounting,
            reason="no element of the certified signed-Johnson relation image maps the source t-local relation to the target",
            v=v,
            k=k,
            t=t,
            image_degree=image_degree,
            image_order=image.order,
            relation_rank=relation_rank,
            complement=complement,
            strict=strict,
            nodes=intersection.search_nodes,
        )
    if intersection.status != "exact_intersection_coset" or intersection.coset is None:
        raise AssertionError("unexpected exact image intersection status")

    preimage = build_paired_action_preimage_artifact(
        group, image_gens, intersection.coset
    )
    if preimage.status != "exact_paired_action_coset_preimage" or preimage.coset is None:
        raise AssertionError("certified image intersection failed generic exact preimage reconstruction")

    determines = (t == k and not complement)
    terminal = bool(determines)
    exact = bool(determines)
    status = (
        "exact_signed_johnson_relation_image_coset"
        if determines
        else "verified_signed_johnson_relation_image_filter"
    )
    operation_kind = (
        "signed_johnson_relation_image_terminal"
        if determines
        else "signed_johnson_relation_image_filter"
    )
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, image_degree),
        operation_kind=operation_kind,
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=terminal,
        reason=(
            "exact smaller-image SI was lifted through the complete paired-action preimage; "
            + (
                "the t-local relation contains every original color pointwise"
                if determines
                else "the result is an exact relation filter and the remaining full k-subset color restriction stays open"
            )
        ),
    )
    return _proof(
        status,
        preimage.coset,
        root_n=root_n,
        domain_size=m,
        exact=exact,
        cost=True,
        bound=local_bound,
        terminal=terminal,
        accounting=accounting,
        reason=accounting.reason,
        v=v,
        k=k,
        t=t,
        image_degree=image_degree,
        image_order=image.order,
        kernel_order=preimage.kernel_order,
        image_si_order=intersection.intersection_order,
        preimage_order=preimage.preimage_subgroup_order,
        relation_rank=relation_rank,
        complement=complement,
        strict=strict,
        determines=determines,
        nodes=intersection.search_nodes,
        image_generators=image_gens,
        image_coset=intersection.coset,
    )
