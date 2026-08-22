from __future__ import annotations
import hashlib, json, math, re
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION=1
RESULT_STATUS="certified_johnson_recursive_result_accounting_binding"
CONSTRUCTION_STATUS="certified_johnson_ground_relational_reduction"
_SHA=re.compile(r"^sha256:[0-9a-f]{64}$")

@dataclass(frozen=True)
class RecursiveProductionTotalCostCoherence:
    schema_version:int; status:str; certified:bool; exact:bool; complete:bool
    outcome_kind:str; parent_action_degree:int; child_ground_size:int
    reduction_identity:str; accounting_binding_digest:str
    construction_cost_binding_identity:str
    construction_multiplicative_cost_bound:float
    charged_log2_reduction_cost:float; coherence_identity:str; reason:str

def _fail(reason:str)->RecursiveProductionTotalCostCoherence:
    return RecursiveProductionTotalCostCoherence(
        1,"recursive_production_total_cost_coherence_not_certified",False,False,False,
        "undetermined",0,0,"","","",0.0,0.0,"",reason)

def _f(o:Any,n:str)->Any:
    if not hasattr(o,n): raise ValueError(f"missing required field {n!r}")
    return getattr(o,n)

def _b(o:Any,n:str)->bool:
    v=_f(o,n)
    if type(v) is not bool: raise ValueError(f"{n} must be a strict boolean")
    return v

def _i(o:Any,n:str)->int:
    v=_f(o,n)
    if type(v) is not int: raise ValueError(f"{n} must be a strict integer")
    return v

def _num(v:Any,n:str,minimum:float=0.0)->float:
    if type(v) not in (int,float) or type(v) is bool:
        raise ValueError(f"{n} must be a finite real number")
    x=float(v)
    if not math.isfinite(x) or x<minimum:
        raise ValueError(f"{n} must be finite and at least {minimum}")
    return x

def _d(v:Any,n:str)->str:
    if not isinstance(v,str) or _SHA.fullmatch(v) is None:
        raise ValueError(f"{n} must be a canonical sha256 digest")
    return v

def _hash(p:dict[str,Any])->str:
    raw=json.dumps(p,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
    return "sha256:"+hashlib.sha256(raw).hexdigest()

def _result(c:Any,replayed:bool)->dict[str,Any]:
    if type(replayed) is not bool or not replayed:
        raise ValueError("rev340 result/accounting binding must be replay-verified independently")
    if _i(c,"schema_version")!=1 or str(_f(c,"status"))!=RESULT_STATUS:
        raise ValueError("unexpected rev340 result/accounting contract")
    for n in ("certified","exact","complete"):
        if not _b(c,n): raise ValueError(f"rev340 {n} must be true")
    outcome=str(_f(c,"outcome_kind"))
    if outcome not in {"exact_empty","nonempty"}:
        raise ValueError("rev340 outcome_kind must preserve exact-empty versus nonempty")
    parent=_i(c,"parent_action_degree"); child=_i(c,"child_ground_size")
    if parent<=0 or child<=0 or child>=parent:
        raise ValueError("rev340 measures must certify strict positive shrink")
    p={
      "schema_version":1,"status":RESULT_STATUS,"outcome_kind":outcome,
      "parent_action_degree":parent,"child_ground_size":child,
      "reduction_identity":_d(_f(c,"reduction_identity"),"rev340.reduction_identity"),
      "handoff_digest":_d(_f(c,"handoff_digest"),"rev340.handoff_digest"),
      "child_result_identity":_d(_f(c,"child_result_identity"),"rev340.child_result_identity"),
      "result_lift_digest":_d(_f(c,"result_lift_digest"),"rev340.result_lift_digest"),
      "charged_log2_reduction_cost":_num(_f(c,"charged_log2_reduction_cost"),"rev340.charged_log2_reduction_cost"),
    }
    digest=_d(_f(c,"binding_digest"),"rev340.binding_digest")
    if _hash(p)!=digest: raise ValueError("rev340 binding_digest replay failed")
    p["binding_digest"]=digest
    return p

def _construction(c:Any,replayed:bool)->dict[str,Any]:
    if type(replayed) is not bool or not replayed:
        raise ValueError("rev360 construction-cost binding must be replay-verified independently")
    if _i(c,"schema_version")!=1 or str(_f(c,"status"))!=CONSTRUCTION_STATUS:
        raise ValueError("unexpected rev360 construction-cost contract")
    for n in ("certified","canonical","exact","progress_certified",
              "solution_transport_certified","ambient_membership_transport_certified",
              "complement_ambiguity_handled","source_replay_verified"):
        if not _b(c,n): raise ValueError(f"rev360 {n} must be true")
    source=_i(c,"source_action_degree"); ground=_i(c,"johnson_ground_size")
    subset=_i(c,"johnson_subset_size"); child=_i(c,"child_ground_size")
    work=_i(c,"source_construction_work_bound")
    if source<=0 or ground<=0 or child!=ground or child>=source or not 0<subset<ground or work<=0:
        raise ValueError("rev360 dimension/work data are malformed")
    rid=_d(_f(c,"reduction_identity"),"rev360.reduction_identity")
    conservative=_num(_f(c,"conservative_construction_cost_bound"),"rev360.conservative_construction_cost_bound",1.0)
    cost=_num(_f(c,"multiplicative_cost"),"rev360.multiplicative_cost",1.0)
    maxcost=_num(_f(c,"max_multiplicative_cost"),"rev360.max_multiplicative_cost",1.0)
    if cost!=maxcost or cost!=conservative:
        raise ValueError("rev360 exposed construction cost bounds must agree exactly")
    if not cost.is_integer():
        raise ValueError("rev360 construction cost bound must be an integral power of two")
    ci=int(cost)
    if ci<1 or ci & (ci-1):
        raise ValueError("rev360 construction cost bound must be a power of two")
    identity=_d(_f(c,"cost_binding_identity"),"rev360.cost_binding_identity")
    expected=_hash({
      "schema_version":1,"source_schema_version":1,"source_status":CONSTRUCTION_STATUS,
      "source_replay_verified":True,"source_reduction_identity":rid,
      "source_action_degree":source,"johnson_ground_size":ground,
      "johnson_subset_size":subset,"child_ground_size":child,
      "source_construction_work_bound":work,"source_multiplicative_cost":1.0,
      "source_max_multiplicative_cost":1.0,
      "conservative_construction_cost_bound":conservative,
      "handoff_max_multiplicative_cost":maxcost,
    })
    if expected!=identity: raise ValueError("rev360 cost_binding_identity replay failed")
    return {"source_action_degree":source,"child_ground_size":child,
            "reduction_identity":rid,"construction_cost_bound":cost,
            "construction_log2_charge":float(ci.bit_length()-1),
            "cost_binding_identity":identity}

def certify_recursive_production_total_cost_coherence(
    result_accounting:Any, construction_cost:Any, *,
    result_accounting_replay_verified:bool, construction_cost_replay_verified:bool
)->RecursiveProductionTotalCostCoherence:
    """Prove that rev360 construction work is represented exactly once by rev340's handoff charge."""
    try:
        r=_result(result_accounting,result_accounting_replay_verified)
        c=_construction(construction_cost,construction_cost_replay_verified)
    except (TypeError,ValueError) as exc:
        return _fail(str(exc))
    if r["reduction_identity"]!=c["reduction_identity"]:
        return _fail("rev340 and rev360 reduction identities differ")
    if r["parent_action_degree"]!=c["source_action_degree"]:
        return _fail("rev340 parent degree differs from rev360 source degree")
    if r["child_ground_size"]!=c["child_ground_size"]:
        return _fail("rev340 child ground differs from rev360 child ground")
    if r["charged_log2_reduction_cost"]!=c["construction_log2_charge"]:
        return _fail("rev340 handoff charge is not exactly log2 of rev360 construction bound")
    p={
      "schema_version":1,"status":"certified_recursive_production_total_cost_coherence",
      "outcome_kind":r["outcome_kind"],"parent_action_degree":r["parent_action_degree"],
      "child_ground_size":r["child_ground_size"],"reduction_identity":r["reduction_identity"],
      "accounting_binding_digest":r["binding_digest"],
      "construction_cost_binding_identity":c["cost_binding_identity"],
      "construction_multiplicative_cost_bound":c["construction_cost_bound"],
      "charged_log2_reduction_cost":r["charged_log2_reduction_cost"],
    }
    ident=_hash(p)
    return RecursiveProductionTotalCostCoherence(
      1,p["status"],True,True,True,p["outcome_kind"],p["parent_action_degree"],
      p["child_ground_size"],p["reduction_identity"],p["accounting_binding_digest"],
      p["construction_cost_binding_identity"],p["construction_multiplicative_cost_bound"],
      p["charged_log2_reduction_cost"],ident,
      "replayed rev340 accounting and rev360 construction-cost bindings agree on one reduction/measure identity and charge the conservative construction bound exactly once")

def replay_recursive_production_total_cost_coherence(
    certificate:RecursiveProductionTotalCostCoherence,
    result_accounting:Any, construction_cost:Any, *,
    result_accounting_replay_verified:bool, construction_cost_replay_verified:bool
)->bool:
    if not isinstance(certificate,RecursiveProductionTotalCostCoherence) or not certificate.certified:
        return False
    replay=certify_recursive_production_total_cost_coherence(
      result_accounting,construction_cost,
      result_accounting_replay_verified=result_accounting_replay_verified,
      construction_cost_replay_verified=construction_cost_replay_verified)
    return bool(replay.certified and replay==certificate and replay.coherence_identity==certificate.coherence_identity)

__all__=["RecursiveProductionTotalCostCoherence",
"certify_recursive_production_total_cost_coherence",
"replay_recursive_production_total_cost_coherence"]
