from __future__ import annotations

from dataclasses import dataclass


def _freeze_identity_value(value):
    """Take an immutable identity snapshot without claiming semantic equality."""
    if isinstance(value, tuple):
        return ("tuple", tuple(_freeze_identity_value(x) for x in value))
    if isinstance(value, list):
        return ("list", tuple(_freeze_identity_value(x) for x in value))
    if isinstance(value, dict):
        items = (
            (_freeze_identity_value(k), _freeze_identity_value(v))
            for k, v in value.items()
        )
        return ("dict", tuple(sorted(items, key=repr)))
    if isinstance(value, (set, frozenset)):
        return (
            "set",
            tuple(sorted((_freeze_identity_value(x) for x in value), key=repr)),
        )
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return ("atom", value)
    return (
        "opaque",
        type(value).__module__,
        type(value).__qualname__,
        repr(value),
    )


def _contains_opaque(value):
    if isinstance(value, tuple):
        if value and value[0] == "opaque":
            return True
        return any(_contains_opaque(x) for x in value)
    return False


def _freeze_group(group):
    """Snapshot the full deterministic Schreier-chain representation."""
    return (
        int(group.degree),
        int(group.order),
        tuple(tuple(g) for g in group.original_generators),
        tuple(
            (
                int(level.base),
                tuple(level.orbit),
                tuple(tuple(g) for g in level.generators),
                tuple((int(point), tuple(perm)) for point, perm in level.transversal),
            )
            for level in group.levels
        ),
    )


@dataclass(frozen=True)
class S1ProofIdentity:
    schema: str
    dispatcher_identity: tuple[str, str, int]
    group_identity: tuple
    source_identity: tuple[object, ...]
    target_identity: tuple[object, ...]
    root_n: int
    domain_size: int
    recursion_depth: int
    resource_identity: tuple[tuple[str, object], ...]
    replay_stable: bool


@dataclass(frozen=True)
class S1ProofIdentityValidation:
    status: str
    certified: bool
    reason: str


def build_s1_proof_identity(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
    recursion_depth: int,
    polylog_power: int,
    max_explicit_degree: int,
    group_order_poly_power: int,
    max_group_order: int,
    max_partition_states: int,
    max_recognition_nodes: int,
    max_depth: int,
) -> S1ProofIdentity:
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("S1 proof identity requires full domain strings")
    if root_n < n:
        raise ValueError("root_n must dominate the S1 identity domain")
    if recursion_depth < 0 or max_depth < 0:
        raise ValueError("S1 depth parameters must be nonnegative")

    # The downstream values are fixed defaults inside u7 but still affect the
    # proof execution.  Recording them explicitly prevents a later default change
    # from silently reusing an older identity schema.
    resources = (
        ("family_poly_power", 2),
        ("group_order_poly_power", int(group_order_poly_power)),
        ("max_depth", int(max_depth)),
        ("max_explicit_degree", int(max_explicit_degree)),
        ("max_family_quotient_order", 4096),
        ("max_family_systems", 4096),
        ("max_group_order", int(max_group_order)),
        ("max_johnson_nodes", 500000),
        ("max_johnson_test_sets", 200000),
        ("max_partition_states", int(max_partition_states)),
        ("max_recognition_nodes", int(max_recognition_nodes)),
        ("polylog_power", int(polylog_power)),
    )
    source_identity = tuple(_freeze_identity_value(x) for x in source)
    target_identity = tuple(_freeze_identity_value(x) for x in target)
    return S1ProofIdentity(
        "s1-proof-identity-v1",
        ("s1_string_isomorphism_v4", "candidate_coset_string_isomorphism_u7", 4),
        _freeze_group(group),
        source_identity,
        target_identity,
        int(root_n),
        n,
        int(recursion_depth),
        resources,
        not any(_contains_opaque(x) for x in source_identity + target_identity),
    )


def validate_s1_proof_identity(proof, expected: S1ProofIdentity):
    actual = getattr(proof, "proof_identity", None)
    if actual is None:
        return S1ProofIdentityValidation(
            "missing_s1_proof_identity",
            False,
            "the proof has no execution-linked S1 mathematical identity",
        )
    if not isinstance(actual, S1ProofIdentity):
        return S1ProofIdentityValidation(
            "wrong_s1_proof_identity_type",
            False,
            "the attached identity is not an S1ProofIdentity v1 artifact",
        )
    if actual != expected:
        return S1ProofIdentityValidation(
            "mismatched_s1_proof_identity",
            False,
            "group/string orientation, root/depth, dispatcher, or a resource gate differs",
        )
    if not actual.replay_stable:
        return S1ProofIdentityValidation(
            "unstable_opaque_s1_identity",
            False,
            "an opaque value lacks a process-stable mathematical snapshot; DAG reuse must fail closed",
        )
    if proof.root_n != actual.root_n or proof.domain_size != actual.domain_size:
        return S1ProofIdentityValidation(
            "inconsistent_s1_proof_measure",
            False,
            "the proof's exposed recurrence measure differs from its frozen identity",
        )
    return S1ProofIdentityValidation(
        "verified_s1_proof_identity",
        True,
        "the execution-linked proof carries the complete expected S1 identity",
    )


__all__ = [
    "S1ProofIdentity",
    "S1ProofIdentityValidation",
    "build_s1_proof_identity",
    "validate_s1_proof_identity",
]
