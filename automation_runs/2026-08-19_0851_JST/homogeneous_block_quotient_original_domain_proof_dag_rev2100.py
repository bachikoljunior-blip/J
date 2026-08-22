from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log2
from types import SimpleNamespace
from typing import Iterable, Optional, Sequence

from block_action_preimage_coset_v1 import (
    lift_prepared_block_action_preimage,
    prepare_block_action_preimage,
)
from coset_stabilizer_primitives import RightCoset
from homogeneous_block_action_provenance_v1 import (
    BlockActionProvenance,
    replay_group_block_action_equivariance,
)
from homogeneous_block_relation_provenance_v1 import (
    HomogeneousBlockTransportCertificate,
    QuotientStructure,
    RelationStructure,
    certify_homogeneous_block_transport,
)
from permutation_group_schreier import (
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
    validate_perm,
)
from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode

REV1800_STATUS_EXACT = "exact_homogeneous_block_quotient_string_isomorphism"
REV1800_EMPTY_STATUSES = frozenset(
    {
        "exact_empty_homogeneous_block_quotient_feature_inventory",
        "exact_empty_homogeneous_block_quotient_string_isomorphism",
    }
)
REV1800_EXACT_STATUSES = frozenset({REV1800_STATUS_EXACT, *REV1800_EMPTY_STATUSES})

STATUS_EXACT = "exact_homogeneous_block_original_domain_relation_isomorphism"
STATUS_EXACT_EMPTY = "exact_empty_homogeneous_block_original_domain_relation_isomorphism"
STATUS_FAIL = "fail_closed_homogeneous_block_original_domain_relation_isomorphism"


@dataclass(frozen=True)
class Rev1800PublicSnapshot:
    status: str
    exact: bool
    complete: bool
    block_count: int
    target_stabilizer_order: int
    representative: Optional[tuple[int, ...]]
    target_stabilizer_generators: tuple[tuple[int, ...], ...]
    provenance_digest: str
    factorization_digest: str


@dataclass(frozen=True)
class HomogeneousBlockOriginalDomainProofIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    provenance_digest: str
    factorization_digest: str
    source_structure: RelationStructure
    target_structure: RelationStructure
    relation_certificate: HomogeneousBlockTransportCertificate
    quotient_snapshot: Rev1800PublicSnapshot
    root_n: int
    max_quotient_enumeration: int
    target_subgroup_order: int
    parent_representative: Optional[tuple[int, ...]]
    replay_stable: bool


@dataclass(frozen=True)
class HomogeneousBlockOriginalDomainTerminalProof:
    status: str
    coset: RightCoset | None
    operation_kind: str
    root_n: int
    domain_size: int
    canonical: bool
    exact: bool
    local_cost_certified: bool
    local_log2_cost_bound: float
    terminal_certified: bool
    permutation_candidates_checked: int
    reason: str
    children: tuple
    accounting: RecurrenceAccountingNode
    proof_identity: HomogeneousBlockOriginalDomainProofIdentity


@dataclass(frozen=True)
class HomogeneousBlockOriginalDomainResult:
    status: str
    exact: bool
    complete: bool
    quotient_semantic_complete: bool
    parent_semantic_exact: bool
    coset: RightCoset | None
    proof: HomogeneousBlockOriginalDomainTerminalProof | None
    dag_validation: ProofDAGValidation | None
    quotient_relation_isomorphisms_checked: int
    reason: str

    @property
    def certified(self) -> bool:
        return bool(
            self.parent_semantic_exact
            and self.dag_validation is not None
            and self.dag_validation.certified
        )


def _valid_digest(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        return False
    suffix = value[7:]
    return suffix == suffix.lower() and all(ch in "0123456789abcdef" for ch in suffix)


def _strict_positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return int(value)


def _group_elements(chain, *, cap: int) -> tuple[tuple[int, ...], ...]:
    if chain.order > cap:
        raise ValueError("quotient group order exceeds max_quotient_enumeration")
    degree = chain.degree
    ident = identity(degree)
    generators = tuple(chain.original_generators) or (ident,)
    seen = {ident}
    frontier = [ident]
    while frontier:
        current = frontier.pop()
        for generator in generators:
            nxt = compose(current, generator)
            if nxt in seen:
                continue
            seen.add(nxt)
            if len(seen) > cap:
                raise ValueError("quotient group enumeration exceeded max_quotient_enumeration")
            frontier.append(nxt)
    if len(seen) != chain.order:
        raise ValueError("enumerated quotient group cardinality disagrees with Schreier order")
    return tuple(sorted(seen))


def _transport_relation_tuples(tuples, permutation):
    return frozenset(tuple(permutation[x] for x in item) for item in tuples)


def _relation_structure_transported(
    source: RelationStructure,
    target: RelationStructure,
    permutation: Sequence[int],
) -> bool:
    try:
        perm = validate_perm(permutation)
    except ValueError:
        return False
    if source.domain_size != target.domain_size or len(perm) != source.domain_size:
        return False
    source_index = {(r.name, r.arity): r.tuples for r in source.relations}
    target_index = {(r.name, r.arity): r.tuples for r in target.relations}
    if source_index.keys() != target_index.keys():
        return False
    return all(
        _transport_relation_tuples(tuples, perm) == target_index[key]
        for key, tuples in source_index.items()
    )


def _quotient_transported(
    source: QuotientStructure,
    target: QuotientStructure,
    permutation: Sequence[int],
) -> bool:
    if source.block_count != target.block_count:
        return False
    try:
        perm = validate_perm(permutation)
    except ValueError:
        return False
    if len(perm) != source.block_count:
        return False
    source_index = {(r.name, r.arity): r.tuples for r in source.relations}
    target_index = {(r.name, r.arity): r.tuples for r in target.relations}
    if source_index.keys() != target_index.keys():
        return False
    return all(
        _transport_relation_tuples(tuples, perm) == target_index[key]
        for key, tuples in source_index.items()
    )


def _maps_blocks(
    permutation: Sequence[int],
    source_blocks: Sequence[Sequence[int]],
    target_blocks: Sequence[Sequence[int]],
    quotient_permutation: Sequence[int],
) -> bool:
    try:
        perm = validate_perm(permutation)
        qperm = validate_perm(quotient_permutation)
    except ValueError:
        return False
    if len(source_blocks) != len(target_blocks) or len(qperm) != len(source_blocks):
        return False
    for i, block in enumerate(source_blocks):
        if {perm[x] for x in block} != set(target_blocks[qperm[i]]):
            return False
    return True


def _snapshot_rev1800(result: object) -> Rev1800PublicSnapshot:
    if getattr(result, "certified", None) is not True:
        raise ValueError("rev1800 public result must be literally certified=True")
    snapshot = getattr(result, "snapshot", None)
    if snapshot is None:
        raise ValueError("rev1800 public result omitted its exact snapshot")
    status = getattr(snapshot, "status", None)
    if status not in REV1800_EXACT_STATUSES:
        raise ValueError("rev1800 snapshot status is not an exact complete quotient outcome")
    if getattr(snapshot, "exact", None) is not True or getattr(snapshot, "complete", None) is not True:
        raise ValueError("rev1800 snapshot must be literally exact=True and complete=True")
    block_count = _strict_positive_int(getattr(snapshot, "block_count", None))
    target_order = getattr(snapshot, "target_stabilizer_order", None)
    if block_count is None or isinstance(target_order, bool) or not isinstance(target_order, int) or target_order < 0:
        raise ValueError("rev1800 snapshot has invalid quotient measures")
    provenance_digest = getattr(snapshot, "provenance_digest", None)
    factorization_digest = getattr(snapshot, "factorization_digest", None)
    if not _valid_digest(provenance_digest) or not _valid_digest(factorization_digest):
        raise ValueError("rev1800 snapshot digests are malformed")
    representative = getattr(snapshot, "representative", None)
    raw_generators = getattr(snapshot, "target_stabilizer_generators", ())
    generators = tuple(tuple(validate_perm(g)) for g in raw_generators)
    if status == REV1800_STATUS_EXACT:
        if representative is None:
            raise ValueError("nonempty rev1800 snapshot omitted its quotient representative")
        representative = tuple(validate_perm(representative))
        if len(representative) != block_count:
            raise ValueError("rev1800 quotient representative has the wrong degree")
        qstab = schreier_stabilizer_chain(generators or (identity(block_count),))
        if qstab.order != target_order:
            raise ValueError("rev1800 target stabilizer order disagrees with its generators")
    else:
        if representative is not None or target_order != 0 or generators:
            raise ValueError("exact-empty rev1800 snapshot carries nonempty coset data")
    return Rev1800PublicSnapshot(
        status=status,
        exact=True,
        complete=True,
        block_count=block_count,
        target_stabilizer_order=int(target_order),
        representative=representative,
        target_stabilizer_generators=generators,
        provenance_digest=provenance_digest,
        factorization_digest=factorization_digest,
    )


def _replay_relation_certificate(
    source: RelationStructure,
    target: RelationStructure,
    certificate: HomogeneousBlockTransportCertificate,
) -> bool:
    replay = certify_homogeneous_block_transport(
        source,
        target,
        certificate.source_partition,
        certificate.target_partition,
        certificate.block_map,
    )
    return replay.exact is True and replay.certificate == certificate


def _quotient_semantic_isomorphisms(
    provenance: BlockActionProvenance,
    certificate: HomogeneousBlockTransportCertificate,
    *,
    cap: int,
) -> tuple[tuple[int, ...], ...]:
    source_group = schreier_stabilizer_chain(
        provenance.source_quotient_generators or (identity(provenance.block_count),)
    )
    source_elements = _group_elements(source_group, cap=cap)
    block_map = tuple(certificate.block_map)
    out = []
    for source_element in source_elements:
        cross = compose(source_element, block_map)
        if _quotient_transported(certificate.source_quotient, certificate.target_quotient, cross):
            out.append(cross)
    return tuple(sorted(out))


def _rev1800_coset_elements(snapshot: Rev1800PublicSnapshot, *, cap: int):
    if snapshot.status in REV1800_EMPTY_STATUSES:
        return ()
    qstab = schreier_stabilizer_chain(
        snapshot.target_stabilizer_generators or (identity(snapshot.block_count),)
    )
    elements = _group_elements(qstab, cap=cap)
    return tuple(sorted(compose(snapshot.representative, element) for element in elements))


def _conjugates_source_group_to_target(
    provenance: BlockActionProvenance,
    point_map: tuple[int, ...],
) -> bool:
    n = provenance.domain_degree
    source = schreier_stabilizer_chain(provenance.source_generators or (identity(n),))
    target = schreier_stabilizer_chain(provenance.target_generators or (identity(n),))
    if source.order != target.order:
        return False
    pinv = inverse(point_map)
    for generator in source.original_generators or (identity(n),):
        conjugate = compose(pinv, compose(generator, point_map))
        if not target.contains(conjugate):
            return False
    return True


def _build_target_preimage_subgroup(
    provenance: BlockActionProvenance,
    snapshot: Rev1800PublicSnapshot,
):
    n = provenance.domain_degree
    target_group = schreier_stabilizer_chain(provenance.target_generators or (identity(n),))
    prepared = prepare_block_action_preimage(target_group, provenance.target_blocks)
    quotient_stabilizer = schreier_stabilizer_chain(
        snapshot.target_stabilizer_generators or (identity(provenance.block_count),)
    )
    generators = list(prepared.kernel.original_generators)
    for quotient_generator in quotient_stabilizer.original_generators:
        lifted = lift_prepared_block_action_preimage(prepared, quotient_generator)
        if (
            lifted.status != "exact_block_action_preimage_coset"
            or lifted.representative is None
            or lifted.coset is None
        ):
            raise ValueError("target quotient stabilizer generator did not lift exactly")
        generators.append(tuple(lifted.representative))
    subgroup = schreier_stabilizer_chain(tuple(generators) or (identity(n),))
    expected = prepared.kernel.order * quotient_stabilizer.order
    if subgroup.order != expected:
        raise ValueError("target original-domain preimage subgroup order is incomplete")
    return prepared, quotient_stabilizer, subgroup


def _local_cost_bound(
    *,
    domain_degree: int,
    block_count: int,
    max_quotient_enumeration: int,
    source_generator_count: int,
    target_generator_count: int,
) -> float:
    units = (
        max_quotient_enumeration
        * max(1, block_count * block_count)
        * max(1, domain_degree * domain_degree)
        * max(1, source_generator_count + target_generator_count)
        * 512
    )
    value = log2(max(2, units)) + 48.0
    if not isfinite(value):
        raise ValueError("rev2100 local cost bound is not finite")
    return value


def _terminal_proof(
    *,
    status: str,
    coset: RightCoset | None,
    identity_value: HomogeneousBlockOriginalDomainProofIdentity,
    local_cost: float,
    candidates_checked: int,
    reason: str,
):
    operation = "homogeneous_block_quotient_original_domain_exact_terminal"
    accounting = RecurrenceAccountingNode(
        n=identity_value.root_n,
        m=identity_value.source_structure.domain_size,
        operation_kind=operation,
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_cost,
        children=(),
        terminal_certified=True,
        reason=reason,
    )
    return HomogeneousBlockOriginalDomainTerminalProof(
        status=status,
        coset=coset,
        operation_kind=operation,
        root_n=identity_value.root_n,
        domain_size=identity_value.source_structure.domain_size,
        canonical=True,
        exact=True,
        local_cost_certified=True,
        local_log2_cost_bound=local_cost,
        terminal_certified=True,
        permutation_candidates_checked=candidates_checked,
        reason=reason,
        children=(),
        accounting=accounting,
        proof_identity=identity_value,
    )


def homogeneous_block_quotient_original_domain_proof_dag_consumer(
    provenance: BlockActionProvenance,
    source_structure: RelationStructure,
    target_structure: RelationStructure,
    relation_certificate: HomogeneousBlockTransportCertificate,
    rev1800_result: object,
    *,
    root_n: int,
    max_quotient_enumeration: int = 4096,
    external_log2_cost_bound: float = 0.0,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> HomogeneousBlockOriginalDomainResult:
    """Lift an exact complete quotient relation-SI coset to the original domain.

    The rev1800 object is consumed structurally; this module imports no rev1800
    or rev278 branch implementation.  Exact parent promotion is allowed only
    after independently enumerating the certified quotient image (under the
    explicit cap) and proving that the rev1800 quotient coset is *exactly* the
    complete quotient relation-isomorphism set.  The main-integrated rev273
    canonical point lift must conjugate the paired rev274 source group onto the
    target group.  Original-domain source/target preimages are then reconstructed
    with the already-main-integrated generic block-action preimage primitive.
    """
    try:
        cap = _strict_positive_int(max_quotient_enumeration)
        root = _strict_positive_int(root_n)
        if cap is None or cap > 1_000_000:
            raise ValueError("max_quotient_enumeration must be a positive integer at most 1,000,000")
        if root is None or root < source_structure.domain_size:
            raise ValueError("root_n must be a positive integer dominating the original domain")
        if not isinstance(provenance, BlockActionProvenance) or not replay_group_block_action_equivariance(provenance):
            raise ValueError("main-integrated rev274 block-action provenance did not replay exactly")
        if not isinstance(relation_certificate, HomogeneousBlockTransportCertificate):
            raise ValueError("relation_certificate must be a main rev273 homogeneous transport certificate")
        if not _replay_relation_certificate(source_structure, target_structure, relation_certificate):
            raise ValueError("main-integrated rev273 relation provenance did not replay exactly")
        if tuple(provenance.source_blocks) != tuple(relation_certificate.source_partition):
            raise ValueError("rev273/rev274 source partitions disagree")
        if tuple(provenance.target_blocks) != tuple(relation_certificate.target_partition):
            raise ValueError("rev273/rev274 target partitions disagree")
        if tuple(provenance.block_bijection) != tuple(relation_certificate.block_map):
            raise ValueError("rev273/rev274 block bijections disagree")
        if source_structure.domain_size != provenance.domain_degree or target_structure.domain_size != provenance.domain_degree:
            raise ValueError("relation/provenance domain degrees disagree")

        snapshot = _snapshot_rev1800(rev1800_result)
        if snapshot.block_count != provenance.block_count:
            raise ValueError("rev1800 quotient degree disagrees with rev274")
        if snapshot.provenance_digest != provenance.certificate_digest:
            raise ValueError("rev1800 provenance digest disagrees with replayed rev274")

        semantic = _quotient_semantic_isomorphisms(provenance, relation_certificate, cap=cap)
        reported = _rev1800_coset_elements(snapshot, cap=cap)
        if semantic != reported:
            raise ValueError("rev1800 quotient coset is not exactly the complete quotient relation-isomorphism set")

        local = _local_cost_bound(
            domain_degree=provenance.domain_degree,
            block_count=provenance.block_count,
            max_quotient_enumeration=cap,
            source_generator_count=len(provenance.source_generators),
            target_generator_count=len(provenance.target_generators),
        )

        if not semantic:
            identity_value = HomogeneousBlockOriginalDomainProofIdentity(
                "homogeneous-block-original-domain-proof-v1",
                ("rev2100", "homogeneous-block-quotient-original-domain", 1),
                provenance.certificate_digest,
                snapshot.factorization_digest,
                source_structure,
                target_structure,
                relation_certificate,
                snapshot,
                root,
                cap,
                0,
                None,
                True,
            )
            proof = _terminal_proof(
                status=STATUS_EXACT_EMPTY,
                coset=None,
                identity_value=identity_value,
                local_cost=local,
                candidates_checked=0,
                reason="bounded complete quotient enumeration independently proves no quotient relation isomorphism exists",
            )
            dag = validate_execution_proof_dag(
                proof,
                original_root_n=root,
                external_log2_cost_bound=external_log2_cost_bound,
                quasipoly_power=quasipoly_power,
                quasipoly_constant=quasipoly_constant,
            )
            return HomogeneousBlockOriginalDomainResult(
                STATUS_EXACT_EMPTY,
                True,
                True,
                True,
                dag.certified,
                None,
                proof,
                dag,
                0,
                dag.reason,
            )

        if snapshot.status != REV1800_STATUS_EXACT or snapshot.representative is None:
            raise ValueError("nonempty semantic quotient isomorphisms require a nonempty rev1800 quotient coset")
        if not _conjugates_source_group_to_target(provenance, relation_certificate.point_map):
            raise ValueError("rev273 canonical point lift does not conjugate the paired rev274 source group onto the target group")

        block_map = tuple(relation_certificate.block_map)
        source_witness = compose(snapshot.representative, inverse(block_map))
        source_qgroup = schreier_stabilizer_chain(
            provenance.source_quotient_generators or (identity(provenance.block_count),)
        )
        if not source_qgroup.contains(source_witness):
            raise ValueError("rev1800 cross-coordinate representative does not decompose through the certified block bijection")

        source_group = schreier_stabilizer_chain(
            provenance.source_generators or (identity(provenance.domain_degree),)
        )
        source_prepared = prepare_block_action_preimage(source_group, provenance.source_blocks)
        source_lift = lift_prepared_block_action_preimage(source_prepared, source_witness)
        if source_lift.status != "exact_block_action_preimage_coset" or source_lift.representative is None:
            raise ValueError("source quotient witness did not lift exactly to the original domain")

        target_prepared, quotient_stabilizer, target_subgroup = _build_target_preimage_subgroup(
            provenance,
            snapshot,
        )
        parent_representative = compose(tuple(source_lift.representative), tuple(relation_certificate.point_map))
        if not _maps_blocks(
            parent_representative,
            provenance.source_blocks,
            provenance.target_blocks,
            snapshot.representative,
        ):
            raise ValueError("original-domain representative does not induce the rev1800 quotient representative")
        if not _relation_structure_transported(source_structure, target_structure, parent_representative):
            raise ValueError("original-domain representative does not transport the complete named relation structure")
        for generator in target_subgroup.original_generators or (identity(provenance.domain_degree),):
            if not _relation_structure_transported(target_structure, target_structure, generator):
                raise ValueError("lifted target subgroup generator does not stabilize the complete target relation structure")

        expected_subgroup_order = target_prepared.kernel.order * quotient_stabilizer.order
        if target_subgroup.order != expected_subgroup_order:
            raise ValueError("original-domain target subgroup is not the complete quotient-stabilizer preimage")
        coset = RightCoset(target_subgroup, parent_representative)
        identity_value = HomogeneousBlockOriginalDomainProofIdentity(
            "homogeneous-block-original-domain-proof-v1",
            ("rev2100", "homogeneous-block-quotient-original-domain", 1),
            provenance.certificate_digest,
            snapshot.factorization_digest,
            source_structure,
            target_structure,
            relation_certificate,
            snapshot,
            root,
            cap,
            target_subgroup.order,
            parent_representative,
            True,
        )
        proof = _terminal_proof(
            status=STATUS_EXACT,
            coset=coset,
            identity_value=identity_value,
            local_cost=local,
            candidates_checked=len(semantic),
            reason="complete bounded quotient relation-SI equality plus exact source/target block-action preimages yields the complete original-domain relation-isomorphism right coset",
        )
        dag = validate_execution_proof_dag(
            proof,
            original_root_n=root,
            external_log2_cost_bound=external_log2_cost_bound,
            quasipoly_power=quasipoly_power,
            quasipoly_constant=quasipoly_constant,
        )
        return HomogeneousBlockOriginalDomainResult(
            STATUS_EXACT,
            True,
            True,
            True,
            dag.certified,
            coset,
            proof,
            dag,
            len(semantic),
            dag.reason,
        )
    except (TypeError, ValueError, AssertionError, OverflowError) as exc:
        return HomogeneousBlockOriginalDomainResult(
            STATUS_FAIL,
            False,
            False,
            False,
            False,
            None,
            None,
            None,
            0,
            str(exc),
        )


__all__ = [
    "HomogeneousBlockOriginalDomainProofIdentity",
    "HomogeneousBlockOriginalDomainResult",
    "HomogeneousBlockOriginalDomainTerminalProof",
    "Rev1800PublicSnapshot",
    "STATUS_EXACT",
    "STATUS_EXACT_EMPTY",
    "STATUS_FAIL",
    "homogeneous_block_quotient_original_domain_proof_dag_consumer",
]
