from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_REV2000_SCHEMA = "homogeneous-block-joint-compatibility-proof-identity-v1"
_REV2000_SOLVER = ("homogeneous_block_joint_compatibility_proof_dag_v1", "proof_dag_accounting_v1", 2000)
_REV2100_SCHEMA = "homogeneous-block-original-domain-proof-v1"
_REV2100_SOLVER = ("rev2100", "homogeneous-block-quotient-original-domain", 1)
_REV2100_EXACT = "exact_homogeneous_block_original_domain_relation_isomorphism"
_REV2100_EMPTY = "exact_empty_homogeneous_block_original_domain_relation_isomorphism"
_QEXACT = "exact_homogeneous_block_quotient_string_isomorphism"
_QEMPTY = {"exact_empty_homogeneous_block_quotient_feature_inventory", "exact_empty_homogeneous_block_quotient_string_isomorphism"}
_SCHEMA = "homogeneous-block-structural-original-domain-coherence-v1"


@dataclass(frozen=True)
class HomogeneousBlockStructuralOriginalDomainCoherenceCertificate:
    schema: str
    relation_transcript_digest: str
    relation_structure_digest: str
    action_provenance_digest: str
    kernel_factorization_digest: str
    rev2000_solver_identity: tuple[str, str, int]
    rev2100_solver_identity: tuple[str, str, int]
    source_partition: tuple[tuple[int, ...], ...]
    target_partition: tuple[tuple[int, ...], ...]
    block_map: tuple[int, ...]
    domain_degree: int
    block_count: int
    block_size: int
    root_n: int
    outcome_kind: str
    quotient_status: str
    target_subgroup_order: int
    parent_representative: tuple[int, ...] | None
    quotient_relation_isomorphisms_checked: int
    structural_replay_certified: bool
    parent_semantic_exact: bool
    original_domain_lift_exact: bool
    coherence_identity: str


@dataclass(frozen=True)
class HomogeneousBlockStructuralOriginalDomainCoherenceResult:
    status: str
    certified: bool
    certificate: HomogeneousBlockStructuralOriginalDomainCoherenceCertificate | None
    reason: str


def _integer(v, minimum=0):
    if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
        raise ValueError(f"expected integer >= {minimum}")
    return int(v)


def _digest(v):
    return isinstance(v, str) and _SHA.fullmatch(v) is not None


def _relations(structure):
    n = _integer(getattr(structure, "domain_size", None), 1)
    raw = getattr(structure, "relations", None)
    if not isinstance(raw, (tuple, list)):
        raise ValueError("relations must be a literal tuple/list")
    out, seen = [], set()
    for rel in raw:
        name, arity, tuples = getattr(rel, "name", None), getattr(rel, "arity", None), getattr(rel, "tuples", None)
        if not isinstance(name, str) or not name or arity not in (1, 2) or (name, arity) in seen:
            raise ValueError("relation signature is not canonical unary/binary")
        seen.add((name, arity))
        if not isinstance(tuples, (tuple, list, set, frozenset)):
            raise ValueError("relation tuples must be finite and literal")
        frozen = []
        for item in tuples:
            if not isinstance(item, (tuple, list)) or len(item) != arity:
                raise ValueError("relation tuple arity drifted")
            item = tuple(_integer(x) for x in item)
            if any(x >= n for x in item):
                raise ValueError("relation tuple contains an out-of-domain point")
            frozen.append(item)
        out.append((name, arity, tuple(sorted(set(frozen)))))
    return n, tuple(out)


def _quotient(q):
    k = _integer(getattr(q, "block_count", None), 1)
    sizes = getattr(q, "block_sizes", None)
    rels = getattr(q, "relations", None)
    if not isinstance(sizes, (tuple, list)) or len(sizes) != k or not isinstance(rels, (tuple, list)):
        raise ValueError("quotient shape is malformed")
    sizes = tuple(_integer(x, 1) for x in sizes)
    frozen = []
    for rel in rels:
        name, arity, tuples = getattr(rel, "name", None), getattr(rel, "arity", None), getattr(rel, "tuples", None)
        if not isinstance(name, str) or not name or arity not in (1, 2) or not isinstance(tuples, (tuple, list, set, frozenset)):
            raise ValueError("quotient relation is malformed")
        items = []
        for item in tuples:
            if not isinstance(item, (tuple, list)) or len(item) != arity:
                raise ValueError("quotient tuple arity drifted")
            item = tuple(_integer(x) for x in item)
            if any(x >= k for x in item):
                raise ValueError("quotient tuple contains an out-of-domain block")
            items.append(item)
        frozen.append((name, arity, tuple(sorted(set(items)))))
    return k, sizes, tuple(frozen)


def _certificate(c):
    fields = [getattr(c, name, None) for name in ("source_partition", "target_partition", "block_map", "point_map")]
    if not all(isinstance(v, (tuple, list)) for v in fields):
        raise ValueError("relation certificate map fields are malformed")
    sp = tuple(tuple(_integer(x) for x in block) for block in fields[0])
    tp = tuple(tuple(_integer(x) for x in block) for block in fields[1])
    bm = tuple(_integer(x) for x in fields[2])
    pm = tuple(_integer(x) for x in fields[3])
    return sp, tp, bm, pm, _quotient(getattr(c, "source_quotient", None)), _quotient(getattr(c, "target_quotient", None))


def _relation_transcript_digest(source, target, relation_result):
    if getattr(relation_result, "exact", None) is not True or getattr(relation_result, "certificate", None) is None:
        raise ValueError("relation result is not exact with certificate")
    reason = getattr(relation_result, "reason", None)
    if not isinstance(reason, str):
        raise ValueError("relation result reason must be a string")
    payload = (_relations(source), _relations(target), reason, _certificate(relation_result.certificate))
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=False).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _canonical_partition(value, n):
    if not isinstance(value, (tuple, list)):
        raise ValueError("partition is malformed")
    blocks = tuple(tuple(_integer(x) for x in block) for block in value)
    if not blocks or any(not block or tuple(sorted(block)) != block for block in blocks):
        raise ValueError("partition blocks are not canonical")
    flat = tuple(x for block in blocks for x in block)
    if tuple(sorted(flat)) != tuple(range(n)) or tuple(sorted(blocks)) != blocks:
        raise ValueError("partition does not canonically cover the domain")
    return blocks


def _build(r2000, r2100, source, target, relation_result):
    if getattr(r2000, "certified", None) is not True or getattr(r2000, "semantic_si_exactness_certified", None) is not False:
        raise ValueError("rev2000 must be certified structural evidence without semantic promotion")
    joint = getattr(getattr(r2000, "proof", None), "proof_identity", None)
    if joint is None or getattr(joint, "schema", None) != _REV2000_SCHEMA or tuple(getattr(joint, "solver_identity", ())) != _REV2000_SOLVER or getattr(joint, "replay_stable", None) is not True:
        raise ValueError("rev2000 proof identity drifted")
    for f in ("certified", "exact", "complete", "quotient_semantic_complete", "parent_semantic_exact"):
        if getattr(r2100, f, None) is not True:
            raise ValueError(f"rev2100 requires literal {f}=True")
    original = getattr(getattr(r2100, "proof", None), "proof_identity", None)
    if original is None or getattr(original, "schema", None) != _REV2100_SCHEMA or tuple(getattr(original, "solver_identity", ())) != _REV2100_SOLVER or getattr(original, "replay_stable", None) is not True:
        raise ValueError("rev2100 proof identity drifted")

    rr_cert = getattr(relation_result, "certificate", None)
    transcript = getattr(joint, "relation_transcript_digest", None)
    if not _digest(transcript) or transcript != _relation_transcript_digest(source, target, relation_result):
        raise ValueError("rev2000 relation transcript does not replay")
    if _relations(getattr(original, "source_structure", None)) != _relations(source) or _relations(getattr(original, "target_structure", None)) != _relations(target) or _certificate(getattr(original, "relation_certificate", None)) != _certificate(rr_cert):
        raise ValueError("rev2100 relation structures/certificate differ from the rev2000 replay input")

    action, kernel = getattr(joint, "action_provenance_digest", None), getattr(joint, "kernel_factorization_digest", None)
    if not _digest(action) or not _digest(kernel) or getattr(original, "provenance_digest", None) != action or getattr(original, "factorization_digest", None) != kernel:
        raise ValueError("rev2000/rev2100 action or kernel identity differs")
    n = _relations(source)[0]
    if _relations(target)[0] != n or _integer(getattr(joint, "domain_degree", None), 1) != n:
        raise ValueError("domain degree differs")
    sp0, tp0, bm0, pm, sq, tq = _certificate(rr_cert)
    sp, tp = _canonical_partition(sp0, n), _canonical_partition(tp0, n)
    k, b = _integer(getattr(joint, "block_count", None), 1), _integer(getattr(joint, "block_size", None), 1)
    bm = tuple(_integer(x) for x in bm0)
    if len(sp) != k or len(tp) != k or len(bm) != k or set(bm) != set(range(k)):
        raise ValueError("block reduction shape differs")
    if tuple(getattr(joint, "source_partition", ())) != sp or tuple(getattr(joint, "target_partition", ())) != tp or tuple(getattr(joint, "block_map", ())) != bm:
        raise ValueError("rev2000 canonical block reduction differs from rev2100")
    if any(len(block) != b for block in sp + tp) or sq[0] != k or tq[0] != k or any(x != b for x in sq[1] + tq[1]):
        raise ValueError("block size/count differs")
    if len(pm) != n or set(pm) != set(range(n)):
        raise ValueError("point map is not an original-domain permutation")
    root = _integer(getattr(joint, "root_n", None), n)
    if _integer(getattr(original, "root_n", None), n) != root:
        raise ValueError("original-root accounting context differs")

    qs = getattr(original, "quotient_snapshot", None)
    if qs is None or getattr(qs, "exact", None) is not True or getattr(qs, "complete", None) is not True or _integer(getattr(qs, "block_count", None), 1) != k or getattr(qs, "provenance_digest", None) != action or getattr(qs, "factorization_digest", None) != kernel:
        raise ValueError("rev2100 quotient snapshot differs from the structural proof")
    qstatus = getattr(qs, "status", None)
    status = getattr(r2100, "status", None)
    subgroup = _integer(getattr(original, "target_subgroup_order", None))
    checked = _integer(getattr(r2100, "quotient_relation_isomorphisms_checked", None))
    parent = getattr(original, "parent_representative", None)
    if status == _REV2100_EXACT:
        if qstatus != _QEXACT or parent is None or subgroup < 1 or checked < 1 or getattr(r2100, "coset", None) is None:
            raise ValueError("nonempty parent/quotient outcome data disagree")
        parent = tuple(_integer(x) for x in parent)
        if len(parent) != n or set(parent) != set(range(n)):
            raise ValueError("parent representative is not a permutation")
        outcome = "nonempty"
    elif status == _REV2100_EMPTY:
        if qstatus not in _QEMPTY or parent is not None or subgroup != 0 or checked != 0 or getattr(r2100, "coset", None) is not None:
            raise ValueError("exact-empty parent/quotient outcome data disagree")
        outcome = "exact_empty"
    else:
        raise ValueError("rev2100 status is not an exact parent outcome")

    structure_payload = {"schema": "rev2300-relation-structure-v1", "source": _relations(source), "target": _relations(target), "certificate": _certificate(rr_cert)}
    structure_digest = "sha256:" + hashlib.sha256(json.dumps(structure_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    payload = {
        "schema": _SCHEMA, "relation_transcript_digest": transcript, "relation_structure_digest": structure_digest,
        "action_provenance_digest": action, "kernel_factorization_digest": kernel, "source_partition": sp,
        "target_partition": tp, "block_map": bm, "domain_degree": n, "block_count": k, "block_size": b,
        "root_n": root, "outcome_kind": outcome, "quotient_status": qstatus, "target_subgroup_order": subgroup,
        "parent_representative": parent, "quotient_relation_isomorphisms_checked": checked,
    }
    coherence = "sha256:" + hashlib.sha256(json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    return HomogeneousBlockStructuralOriginalDomainCoherenceCertificate(
        _SCHEMA, transcript, structure_digest, action, kernel, _REV2000_SOLVER, _REV2100_SOLVER,
        sp, tp, bm, n, k, b, root, outcome, qstatus, subgroup, parent, checked, True, True, True, coherence,
    )


def certify_homogeneous_block_structural_original_domain_coherence(rev2000_result, rev2100_result, source_structure, target_structure, relation_result):
    try:
        cert = _build(rev2000_result, rev2100_result, source_structure, target_structure, relation_result)
    except (AttributeError, TypeError, ValueError) as exc:
        return HomogeneousBlockStructuralOriginalDomainCoherenceResult("rejected_homogeneous_block_structural_original_domain_coherence", False, None, str(exc))
    return HomogeneousBlockStructuralOriginalDomainCoherenceResult(
        "certified_homogeneous_block_structural_original_domain_coherence", True, cert,
        "rev2000 structural proof and rev2100 exact parent result replay one immutable homogeneous-block reduction and exact parent outcome",
    )


def replay_homogeneous_block_structural_original_domain_coherence(certificate, rev2000_result, rev2100_result, source_structure, target_structure, relation_result):
    if not isinstance(certificate, HomogeneousBlockStructuralOriginalDomainCoherenceCertificate) or not _digest(certificate.coherence_identity):
        return False
    replay = certify_homogeneous_block_structural_original_domain_coherence(rev2000_result, rev2100_result, source_structure, target_structure, relation_result)
    return replay.certified and replay.certificate == certificate


__all__ = [
    "HomogeneousBlockStructuralOriginalDomainCoherenceCertificate",
    "HomogeneousBlockStructuralOriginalDomainCoherenceResult",
    "certify_homogeneous_block_structural_original_domain_coherence",
    "replay_homogeneous_block_structural_original_domain_coherence",
]
