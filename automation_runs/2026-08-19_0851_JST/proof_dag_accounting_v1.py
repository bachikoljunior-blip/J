from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log2
from numbers import Integral, Real

from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4
from s1_proof_identity_v1 import (
    _contains_opaque,
    _freeze_group,
    _freeze_identity_value,
)


@dataclass(frozen=True)
class CandidateSIProofIdentity:
    schema: str
    dispatcher_identity: tuple[str, str, int]
    candidate_group_identity: tuple
    candidate_representative: tuple[int, ...]
    source_identity: tuple[object, ...]
    target_identity: tuple[object, ...]
    root_n: int
    resource_identity: tuple[tuple[str, object], ...]
    replay_stable: bool


@dataclass(frozen=True)
class ProofDAGEdge:
    child_identity: object
    multiplicity: int


@dataclass(frozen=True)
class ProofDAGNode:
    identity: object
    payload_identity: tuple
    local_log2_cost_bound: float
    edges: tuple[ProofDAGEdge, ...]


@dataclass(frozen=True)
class ProofDAGArtifact:
    status: str
    root_identity: object | None
    nodes: tuple[ProofDAGNode, ...]
    reason: str


@dataclass(frozen=True)
class ProofDAGValidation:
    status: str
    certified: bool
    log2_work_bound: float
    allowed_log2_work: float
    unique_nodes: int
    execution_occurrences: int
    reused_occurrences: int
    max_depth: int
    reason: str


def build_candidate_si_proof_identity(
    candidate,
    source_values,
    target_values,
    *,
    root_n: int,
    dispatcher_identity: tuple[str, str, int],
    max_group_order: int,
):
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(candidate.subgroup.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("candidate proof identity requires full domain strings")
    if root_n < n:
        raise ValueError("root_n must dominate candidate proof identity degree")
    dispatcher_identity = tuple(dispatcher_identity)
    if (
        len(dispatcher_identity) != 3
        or not all(isinstance(part, str) for part in dispatcher_identity[:2])
        or not isinstance(dispatcher_identity[2], int)
    ):
        raise ValueError("candidate dispatcher identity must be a versioned stable triple")
    source_identity = tuple(_freeze_identity_value(x) for x in source)
    target_identity = tuple(_freeze_identity_value(x) for x in target)
    resources = (
        ("family_poly_power", 2),
        ("group_order_poly_power", 2),
        ("max_depth", 64),
        ("max_explicit_degree", 8),
        ("max_family_quotient_order", 4096),
        ("max_family_systems", 4096),
        ("max_group_order", int(max_group_order)),
        ("max_johnson_nodes", 500000),
        ("max_johnson_test_sets", 200000),
        ("max_partition_states", 4096),
        ("max_recognition_nodes", 500000),
        ("polylog_power", 2),
    )
    return CandidateSIProofIdentity(
        "candidate-si-proof-identity-v1",
        dispatcher_identity,
        _freeze_group(candidate.subgroup),
        tuple(candidate.representative),
        source_identity,
        target_identity,
        int(root_n),
        resources,
        not any(_contains_opaque(x) for x in source_identity + target_identity),
    )


def _identity_is_stable(identity):
    return bool(getattr(identity, "replay_stable", False))


def _payload_identity(proof, accounting):
    return (
        proof.status,
        proof.coset,
        proof.operation_kind,
        int(proof.root_n),
        int(proof.domain_size),
        bool(proof.canonical),
        bool(proof.exact),
        bool(proof.local_cost_certified),
        float(proof.local_log2_cost_bound),
        bool(proof.terminal_certified),
        int(proof.permutation_candidates_checked),
        proof.reason,
        int(accounting.n),
        int(accounting.m),
        accounting.operation_kind,
        bool(accounting.canonical),
        bool(accounting.cost_certified),
        float(accounting.local_log2_cost_bound),
        bool(accounting.terminal_certified),
        accounting.reason,
    )


def build_proof_dag_artifact(proof):
    """Deduplicate proof storage without deduplicating execution charge."""
    root_identity = getattr(proof, "proof_identity", None)
    if root_identity is None:
        return ProofDAGArtifact(
            "missing_root_proof_identity",
            None,
            (),
            "a shared proof DAG requires an execution-linked root identity",
        )
    if not _identity_is_stable(root_identity):
        return ProofDAGArtifact(
            "unstable_root_proof_identity",
            root_identity,
            (),
            "the root identity is opaque or not certified replay-stable",
        )
    try:
        hash(root_identity)
    except TypeError:
        return ProofDAGArtifact(
            "unhashable_root_proof_identity",
            root_identity,
            (),
            "proof DAG identities must be immutable and hashable",
        )

    nodes = {}
    order = []
    active = set()

    class Invalid(Exception):
        def __init__(self, status, reason):
            self.status = status
            self.reason = reason

    def visit(current, path):
        attached = getattr(current, "proof_identity", None)
        if attached is not None:
            if not _identity_is_stable(attached):
                raise Invalid(
                    "unstable_attached_proof_identity",
                    "an attached child identity is opaque or not replay-stable",
                )
            identity = ("attached", attached)
        else:
            # A proof without a mathematical identity is safe only as an
            # occurrence-local node.  It cannot be shared with another path.
            identity = ("path-scoped", root_identity, tuple(path))
        try:
            hash(identity)
        except TypeError as exc:
            raise Invalid(
                "unhashable_proof_identity",
                "a proof node identity is not immutable/hashable",
            ) from exc
        if identity in active:
            raise Invalid(
                "cyclic_proof_identity_graph",
                "a proof identity occurs again on its active ancestor path",
            )

        accounting = current.accounting
        if len(current.children) != len(accounting.children):
            raise Invalid(
                "proof_accounting_child_mismatch",
                "proof children and accounting edges are not one-to-one",
            )

        active.add(identity)
        edges = []
        for index, (child, accounting_edge) in enumerate(
            zip(current.children, accounting.children)
        ):
            if child.accounting != accounting_edge.node:
                raise Invalid(
                    "proof_accounting_payload_mismatch",
                    "an accounting edge does not carry its proof child's accounting object",
                )
            child_identity = visit(child, path + (index,))
            edges.append(ProofDAGEdge(child_identity, int(accounting_edge.multiplicity)))
        active.remove(identity)

        node = ProofDAGNode(
            identity,
            _payload_identity(current, accounting),
            float(accounting.local_log2_cost_bound),
            tuple(edges),
        )
        prior = nodes.get(identity)
        if prior is not None and prior != node:
            raise Invalid(
                "proof_identity_payload_collision",
                "one identity names different proof/accounting payloads or child edges",
            )
        if prior is None:
            nodes[identity] = node
            order.append(identity)
        return identity

    try:
        stored_root = visit(proof, ())
    except Invalid as exc:
        return ProofDAGArtifact(exc.status, root_identity, (), exc.reason)
    if stored_root != ("attached", root_identity):
        raise AssertionError("root proof identity was not stored as an attached identity")
    return ProofDAGArtifact(
        "constructed_execution_proof_dag",
        root_identity,
        tuple(nodes[identity] for identity in order),
        "proof storage is identity-deduplicated; execution occurrences remain represented by every incoming edge",
    )


def _log2_sum_exp(values):
    values = tuple(values)
    if not values:
        return 0.0
    top = max(values)
    return top + log2(sum(2.0 ** (value - top) for value in values))


def _strict_integral(value, *, minimum: int):
    if isinstance(value, bool) or not isinstance(value, Integral):
        return None
    normalized = int(value)
    if normalized < minimum:
        return None
    return normalized


def _finite_real(value, *, minimum: float):
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    normalized = float(value)
    if not isfinite(normalized) or normalized < minimum:
        return None
    return normalized


def validate_execution_proof_dag(
    proof,
    *,
    original_root_n: int,
    polynomial_lift_degree: int | None = None,
    external_log2_cost_bound: float = 0.0,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
):
    """Validate identity sharing while charging every execution occurrence.

    A repeated identity saves proof storage only.  Cost recursion deliberately
    does not memoize: every incoming edge contributes the full conservative child
    bound.  Thus cache reuse can never erase worst-case work.

    Envelope inputs are validated without coercion before recurrence replay or
    floating-point comparisons.  In particular, booleans, numeric strings,
    fractional integer fields, NaN, infinity, and overflowing envelope values
    fail closed instead of reaching comparisons where NaN could otherwise make
    both ``<`` and ``>`` tests false.
    """
    normalized_root_n = _strict_integral(original_root_n, minimum=1)
    normalized_external = _finite_real(external_log2_cost_bound, minimum=0.0)
    normalized_power = _strict_integral(quasipoly_power, minimum=0)
    normalized_constant = _finite_real(quasipoly_constant, minimum=0.0)
    if (
        normalized_root_n is None
        or normalized_external is None
        or normalized_power is None
        or normalized_constant is None
    ):
        return ProofDAGValidation(
            "invalid_proof_dag_envelope",
            False,
            0.0,
            0.0,
            0,
            0,
            0,
            0,
            "original root and quasipolynomial power must be strict integers; external cost and envelope constant must be finite nonnegative real numbers",
        )

    normalized_lift = None
    if polynomial_lift_degree is not None:
        normalized_lift = _strict_integral(polynomial_lift_degree, minimum=1)
        if normalized_lift is None:
            return ProofDAGValidation(
                "invalid_polynomial_root_lift",
                False,
                0.0,
                0.0,
                0,
                0,
                0,
                0,
                "an explicit polynomial lift degree must be a positive strict integer",
            )

    original_root_n = normalized_root_n
    external_log2_cost_bound = normalized_external
    quasipoly_power = normalized_power
    quasipoly_constant = normalized_constant
    try:
        allowed = quasipoly_constant * (
            log2(max(2, original_root_n)) ** quasipoly_power
        )
    except (OverflowError, ValueError):
        return ProofDAGValidation(
            "invalid_proof_dag_envelope",
            False,
            0.0,
            0.0,
            0,
            0,
            0,
            0,
            "quasipolynomial envelope arithmetic overflowed or was not finite",
        )
    if not isfinite(allowed):
        return ProofDAGValidation(
            "invalid_proof_dag_envelope",
            False,
            0.0,
            0.0,
            0,
            0,
            0,
            0,
            "quasipolynomial envelope arithmetic must remain finite",
        )

    tree = validate_quasipoly_recurrence_tree_v4(proof.accounting)
    if not tree.certified:
        return ProofDAGValidation(
            "accounting_" + tree.status, False, 0.0, allowed, 0, 0, 0,
            tree.max_depth, tree.reason,
        )
    if _finite_real(tree.log2_work_bound, minimum=0.0) is None:
        return ProofDAGValidation(
            "accounting_nonfinite_work_bound",
            False,
            0.0,
            allowed,
            0,
            0,
            0,
            tree.max_depth,
            "the independently validated recurrence returned a non-finite work bound",
        )

    execution_root = int(proof.accounting.n)
    if execution_root > original_root_n:
        if (
            normalized_lift != execution_root
            or normalized_lift > original_root_n + original_root_n ** 2
        ):
            return ProofDAGValidation(
                "invalid_polynomial_root_lift", False, 0.0, allowed, 0, 0, 0, 0,
                "a larger execution root must equal an explicit degree bounded by n+n^2",
            )

    artifact = build_proof_dag_artifact(proof)
    if artifact.status != "constructed_execution_proof_dag":
        return ProofDAGValidation(
            artifact.status, False, 0.0, allowed, len(artifact.nodes), 0, 0, 0,
            artifact.reason,
        )
    node_map = {node.identity: node for node in artifact.nodes}
    root_identity = ("attached", artifact.root_identity)
    occurrences = 0
    max_depth = 0

    class Cycle(Exception):
        pass

    def charge(identity, active, depth, path_multiplicity):
        nonlocal occurrences, max_depth
        if identity in active:
            raise Cycle
        node = node_map.get(identity)
        if node is None:
            raise AssertionError("DAG edge points to an unstored identity")
        # One stored edge can represent several executed branches.  Storage is
        # visited once, while this metric counts every represented occurrence,
        # including all descendants repeated by an ancestor multiplicity.
        occurrences += int(path_multiplicity)
        max_depth = max(max_depth, depth)
        next_active = active | {identity}
        terms = []
        for edge in node.edges:
            if edge.multiplicity <= 0:
                raise AssertionError("validated accounting edge lost positive multiplicity")
            terms.append(
                log2(edge.multiplicity)
                + charge(
                    edge.child_identity,
                    next_active,
                    depth + 1,
                    int(path_multiplicity) * int(edge.multiplicity),
                )
            )
        return node.local_log2_cost_bound + _log2_sum_exp(terms)

    try:
        dag_work = charge(root_identity, frozenset(), 0, 1)
    except Cycle:
        return ProofDAGValidation(
            "cyclic_proof_dag", False, 0.0, allowed, len(node_map), occurrences,
            max(0, occurrences - len(node_map)), max_depth,
            "the stored proof DAG contains a charge cycle",
        )
    if not isfinite(dag_work):
        return ProofDAGValidation(
            "nonfinite_proof_dag_charge",
            False,
            0.0,
            allowed,
            len(node_map),
            occurrences,
            max(0, occurrences - len(node_map)),
            max_depth,
            "execution proof-DAG occurrence charging produced a non-finite value",
        )
    if abs(dag_work - float(tree.log2_work_bound)) > 1e-8:
        return ProofDAGValidation(
            "tree_dag_charge_mismatch", False, dag_work, allowed, len(node_map),
            occurrences, max(0, occurrences - len(node_map)), max_depth,
            "identity-DAG occurrence charge differs from the independently validated accounting tree",
        )
    total = external_log2_cost_bound + dag_work
    if not isfinite(total):
        return ProofDAGValidation(
            "invalid_proof_dag_envelope",
            False,
            0.0,
            allowed,
            len(node_map),
            occurrences,
            max(0, occurrences - len(node_map)),
            max_depth,
            "external plus execution proof-DAG work must remain finite",
        )
    if total > allowed + 1e-9:
        return ProofDAGValidation(
            "proof_dag_quasipolynomial_envelope_exceeded", False, total, allowed,
            len(node_map), occurrences, max(0, occurrences - len(node_map)),
            max_depth, "conservative occurrence charge exceeds the original-root envelope",
        )
    return ProofDAGValidation(
        "certified_execution_proof_dag", True, total, allowed, len(node_map),
        occurrences, max(0, occurrences - len(node_map)), max_depth,
        "identities have no collisions/cycles, recurrence validation agrees, and every incoming execution occurrence is charged in the original-root envelope",
    )


__all__ = [
    "CandidateSIProofIdentity",
    "ProofDAGArtifact",
    "ProofDAGEdge",
    "ProofDAGNode",
    "ProofDAGValidation",
    "build_candidate_si_proof_identity",
    "build_proof_dag_artifact",
    "validate_execution_proof_dag",
]
