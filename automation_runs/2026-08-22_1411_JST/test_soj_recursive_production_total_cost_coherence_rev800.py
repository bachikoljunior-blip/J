from dataclasses import replace
from types import SimpleNamespace
from soj_recursive_production_total_cost_coherence_v1 import (
    certify_recursive_production_total_cost_coherence,
    replay_recursive_production_total_cost_coherence,
    _hash,
)

RID="sha256:"+"1"*64
HD="sha256:"+"2"*64
CHILD="sha256:"+"3"*64
LIFT="sha256:"+"4"*64

def result_cert(charge=8.0, rid=RID, parent=70, child=8, outcome="nonempty"):
    p={"schema_version":1,"status":"certified_johnson_recursive_result_accounting_binding",
       "outcome_kind":outcome,"parent_action_degree":parent,"child_ground_size":child,
       "reduction_identity":rid,"handoff_digest":HD,"child_result_identity":CHILD,
       "result_lift_digest":LIFT,"charged_log2_reduction_cost":charge}
    return SimpleNamespace(**p,certified=True,exact=True,complete=True,binding_digest=_hash(p))

def cost_cert(cost=256.0, rid=RID, source=70, child=8, ground=8, subset=4, work=137):
    p={"schema_version":1,"source_schema_version":1,
       "source_status":"certified_johnson_ground_relational_reduction",
       "source_replay_verified":True,"source_reduction_identity":rid,
       "source_action_degree":source,"johnson_ground_size":ground,
       "johnson_subset_size":subset,"child_ground_size":child,
       "source_construction_work_bound":work,"source_multiplicative_cost":1.0,
       "source_max_multiplicative_cost":1.0,
       "conservative_construction_cost_bound":cost,
       "handoff_max_multiplicative_cost":cost}
    return SimpleNamespace(
      schema_version=1,status="certified_johnson_ground_relational_reduction",
      certified=True,canonical=True,exact=True,progress_certified=True,
      solution_transport_certified=True,ambient_membership_transport_certified=True,
      complement_ambiguity_handled=True,source_replay_verified=True,
      source_action_degree=source,johnson_ground_size=ground,johnson_subset_size=subset,
      child_ground_size=child,multiplicative_cost=cost,max_multiplicative_cost=cost,
      reduction_identity=rid,source_construction_work_bound=work,
      conservative_construction_cost_bound=cost,cost_binding_identity=_hash(p))

def certify(r=None,c=None,rr=True,cr=True):
    return certify_recursive_production_total_cost_coherence(
      r or result_cert(), c or cost_cert(),
      result_accounting_replay_verified=rr,
      construction_cost_replay_verified=cr)

def test_accepts_exact_once_cost_coherence():
    out=certify()
    assert out.certified and out.exact and out.complete
    assert out.construction_multiplicative_cost_bound==256.0
    assert out.charged_log2_reduction_cost==8.0
    assert out.coherence_identity.startswith("sha256:")

def test_replay_roundtrip_and_drift():
    r=result_cert(); c=cost_cert(); out=certify(r,c)
    assert replay_recursive_production_total_cost_coherence(
      out,r,c,result_accounting_replay_verified=True,construction_cost_replay_verified=True)
    assert not replay_recursive_production_total_cost_coherence(
      replace(out,reason="drift"),r,c,result_accounting_replay_verified=True,construction_cost_replay_verified=True)

def test_requires_both_replay_gates():
    assert not certify(rr=False).certified
    assert not certify(cr=False).certified

def test_rejects_reduction_identity_mismatch():
    assert not certify(c=cost_cert(rid="sha256:"+"9"*64)).certified

def test_rejects_parent_degree_mismatch():
    assert not certify(c=cost_cert(source=71)).certified

def test_rejects_child_ground_mismatch():
    assert not certify(c=cost_cert(child=7,ground=7)).certified

def test_rejects_missing_or_double_construction_charge():
    assert not certify(r=result_cert(charge=7.0)).certified
    assert not certify(r=result_cert(charge=9.0)).certified

def test_rejects_non_power_of_two_cost():
    assert not certify(c=cost_cert(cost=300.0)).certified

def test_rejects_rev340_digest_drift():
    r=result_cert(); r.binding_digest="sha256:"+"a"*64
    assert not certify(r=r).certified

def test_rejects_rev360_digest_drift():
    c=cost_cert(); c.cost_binding_identity="sha256:"+"b"*64
    assert not certify(c=c).certified

def test_preserves_exact_empty_distinction():
    out=certify(r=result_cert(outcome="exact_empty"))
    assert out.certified and out.outcome_kind=="exact_empty"

def test_rejects_coercible_booleans():
    r=result_cert(); r.certified=1
    assert not certify(r=r).certified
    c=cost_cert(); c.source_replay_verified=1
    assert not certify(c=c).certified

def test_rejects_noncanonical_digest():
    r=result_cert(rid="abc")
    assert not certify(r=r).certified

if __name__=="__main__":
    tests=[(n,v) for n,v in sorted(globals().items()) if n.startswith("test_") and callable(v)]
    for n,t in tests:
        t(); print("PASS",n)
    print(f"{len(tests)}/{len(tests)} passed")
