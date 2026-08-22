from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "rev2300",
    HERE / "homogeneous_block_structural_quotient_coherence_v1.py",
)
rev2300 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
import sys
sys.modules[SPEC.name] = rev2300
SPEC.loader.exec_module(rev2300)

certify = rev2300.certify_homogeneous_block_structural_original_domain_coherence
replay = rev2300.replay_homogeneous_block_structural_original_domain_coherence


def relation(name, arity, tuples):
    return SimpleNamespace(name=name, arity=arity, tuples=frozenset(tuples))


def structures():
    source = SimpleNamespace(
        domain_size=4,
        relations=(
            relation("u", 1, ((0,), (2,))),
            relation("b", 2, ((0, 1), (2, 3))),
        ),
    )
    target = SimpleNamespace(
        domain_size=4,
        relations=(
            relation("u", 1, ((0,), (2,))),
            relation("b", 2, ((0, 1), (2, 3))),
        ),
    )
    source_q = SimpleNamespace(
        block_count=2,
        block_sizes=(2, 2),
        relations=(
            relation("u", 1, ((0,), (1,))),
            relation("b", 2, ((0, 0), (1, 1))),
        ),
    )
    target_q = SimpleNamespace(
        block_count=2,
        block_sizes=(2, 2),
        relations=(
            relation("u", 1, ((0,), (1,))),
            relation("b", 2, ((0, 0), (1, 1))),
        ),
    )
    certificate = SimpleNamespace(
        source_partition=((0, 1), (2, 3)),
        target_partition=((0, 1), (2, 3)),
        block_map=(0, 1),
        point_map=(0, 1, 2, 3),
        source_quotient=source_q,
        target_quotient=target_q,
    )
    relation_result = SimpleNamespace(exact=True, certificate=certificate, reason="exact homogeneous block transport")
    return source, target, certificate, relation_result


def make_fixture(*, empty=False):
    source, target, certificate, relation_result = structures()
    action = "sha256:" + "1" * 64
    kernel = "sha256:" + "2" * 64
    relation_digest = rev2300._relation_transcript_digest(source, target, relation_result)
    joint_identity = SimpleNamespace(
        schema="homogeneous-block-joint-compatibility-proof-identity-v1",
        solver_identity=(
            "homogeneous_block_joint_compatibility_proof_dag_v1",
            "proof_dag_accounting_v1",
            2000,
        ),
        relation_transcript_digest=relation_digest,
        action_provenance_digest=action,
        kernel_factorization_digest=kernel,
        source_partition=certificate.source_partition,
        target_partition=certificate.target_partition,
        block_map=certificate.block_map,
        domain_degree=4,
        block_count=2,
        block_size=2,
        root_n=8,
        replay_stable=True,
    )
    rev2000 = SimpleNamespace(
        certified=True,
        semantic_si_exactness_certified=False,
        proof=SimpleNamespace(proof_identity=joint_identity),
    )
    if empty:
        qstatus = "exact_empty_homogeneous_block_quotient_string_isomorphism"
        status = "exact_empty_homogeneous_block_original_domain_relation_isomorphism"
        parent_rep = None
        subgroup_order = 0
        checked = 0
        coset = None
    else:
        qstatus = "exact_homogeneous_block_quotient_string_isomorphism"
        status = "exact_homogeneous_block_original_domain_relation_isomorphism"
        parent_rep = (0, 1, 2, 3)
        subgroup_order = 2
        checked = 2
        coset = object()
    quotient_snapshot = SimpleNamespace(
        status=qstatus,
        exact=True,
        complete=True,
        block_count=2,
        target_stabilizer_order=0 if empty else 1,
        representative=None if empty else (0, 1),
        target_stabilizer_generators=(),
        provenance_digest=action,
        factorization_digest=kernel,
    )
    original_identity = SimpleNamespace(
        schema="homogeneous-block-original-domain-proof-v1",
        solver_identity=("rev2100", "homogeneous-block-quotient-original-domain", 1),
        provenance_digest=action,
        factorization_digest=kernel,
        source_structure=source,
        target_structure=target,
        relation_certificate=certificate,
        quotient_snapshot=quotient_snapshot,
        root_n=8,
        max_quotient_enumeration=4096,
        target_subgroup_order=subgroup_order,
        parent_representative=parent_rep,
        replay_stable=True,
    )
    rev2100 = SimpleNamespace(
        status=status,
        exact=True,
        complete=True,
        quotient_semantic_complete=True,
        parent_semantic_exact=True,
        coset=coset,
        proof=SimpleNamespace(proof_identity=original_identity),
        dag_validation=SimpleNamespace(certified=True),
        quotient_relation_isomorphisms_checked=checked,
        certified=True,
    )
    return rev2000, rev2100, source, target, relation_result


class Rev2300Tests(unittest.TestCase):
    def test_nonempty_coherence(self):
        args = make_fixture()
        result = certify(*args)
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(result.certificate.outcome_kind, "nonempty")
        self.assertTrue(replay(result.certificate, *args))

    def test_exact_empty_coherence(self):
        args = make_fixture(empty=True)
        result = certify(*args)
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(result.certificate.outcome_kind, "exact_empty")
        self.assertTrue(replay(result.certificate, *args))

    def test_rejects_rev2000_not_certified(self):
        r2000, r2100, s, t, rr = make_fixture()
        r2000.certified = False
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_rejects_rev2000_semantic_promotion(self):
        r2000, r2100, s, t, rr = make_fixture()
        r2000.semantic_si_exactness_certified = True
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_rejects_rev2100_nonexact(self):
        r2000, r2100, s, t, rr = make_fixture()
        r2100.exact = False
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_rejects_relation_transcript_drift(self):
        r2000, r2100, s, t, rr = make_fixture()
        r2000.proof.proof_identity.relation_transcript_digest = "sha256:" + "3" * 64
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_rejects_source_structure_drift(self):
        r2000, r2100, s, t, rr = make_fixture()
        r2100.proof.proof_identity.source_structure = SimpleNamespace(
            domain_size=4,
            relations=(relation("u", 1, ((1,),)),),
        )
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_rejects_action_digest_drift(self):
        r2000, r2100, s, t, rr = make_fixture()
        r2100.proof.proof_identity.provenance_digest = "sha256:" + "4" * 64
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_rejects_kernel_digest_drift(self):
        r2000, r2100, s, t, rr = make_fixture()
        r2100.proof.proof_identity.factorization_digest = "sha256:" + "5" * 64
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_rejects_partition_drift(self):
        r2000, r2100, s, t, rr = make_fixture()
        r2000.proof.proof_identity.source_partition = ((0, 2), (1, 3))
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_rejects_root_drift(self):
        r2000, r2100, s, t, rr = make_fixture()
        r2100.proof.proof_identity.root_n = 9
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_rejects_quotient_status_parent_outcome_mismatch(self):
        r2000, r2100, s, t, rr = make_fixture()
        r2100.proof.proof_identity.quotient_snapshot.status = (
            "exact_empty_homogeneous_block_quotient_string_isomorphism"
        )
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_rejects_nonempty_without_coset(self):
        r2000, r2100, s, t, rr = make_fixture()
        r2100.coset = None
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_rejects_empty_with_parent_representative(self):
        r2000, r2100, s, t, rr = make_fixture(empty=True)
        r2100.proof.proof_identity.parent_representative = (0, 1, 2, 3)
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)

    def test_replay_detects_certificate_mutation(self):
        args = make_fixture()
        result = certify(*args)
        self.assertTrue(result.certified)
        mutated = replace(result.certificate, root_n=result.certificate.root_n + 1)
        self.assertFalse(replay(mutated, *args))

    def test_rejects_noncanonical_relation_point(self):
        r2000, r2100, s, t, rr = make_fixture()
        s.relations = (relation("u", 1, ((5,),)),)
        self.assertFalse(certify(r2000, r2100, s, t, rr).certified)


if __name__ == "__main__":
    unittest.main()
