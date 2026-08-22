from __future__ import annotations
import hashlib, json, math, re
from dataclasses import dataclass
from typing import Any
SCHEMA_VERSION=1
EXECUTION_STATUS='certified_parent_filtered_child_execution_proof_dag_binding'
PROOF_ACCOUNTING_STATUS='certified_parent_filtered_proof_accounting_coherence'
OUTPUT_STATUS='certified_parent_filtered_execution_proof_accounting_coherence'
PARENT_NONEMPTY_STATUS='exact_parent_filtered_ground_coset'
PARENT_EMPTY_STATUS='exact_empty_parent_filtered_ground_coset'
_SHA=re.compile(r'^sha256:[0-9a-f]{64}$')
@dataclass(frozen=True)
class ParentFilteredExecutionProofAccountingCoherence:
    schema_version:int; status:str; certified:bool; exact:bool; complete:bool
    parent_outcome_kind:str; child_execution_outcome_kind:str; source_status:str
    reduction_identity:str; semantic_binding_identity:str; child_instance_identity:str; child_result_identity:str; parent_result_identity:str
    execution_binding_identity:str; execution_closure_identity:str; execution_result_lift_digest:str; execution_proof_identity_digest:str; child_proof_identity_digest:str
    parent_result_proof_dag_identity:str; accounting_coherence_identity:str; handoff_digest:str
    parent_action_degree:int; child_ground_size:int; candidate_count:int; accepted_count:int; parent_filter_work_bound:int; charged_log2_reduction_cost:float
    same_child_execution_certified:bool; parent_result_identity_equivalence_certified:bool; coherence_identity:str; reason:str

def _fail(reason:str):
    return ParentFilteredExecutionProofAccountingCoherence(
        schema_version=1, status='parent_filtered_execution_proof_accounting_coherence_not_certified',
        certified=False, exact=False, complete=False, parent_outcome_kind='undetermined',
        child_execution_outcome_kind='undetermined', source_status='', reduction_identity='',
        semantic_binding_identity='', child_instance_identity='', child_result_identity='', parent_result_identity='',
        execution_binding_identity='', execution_closure_identity='', execution_result_lift_digest='',
        execution_proof_identity_digest='', child_proof_identity_digest='', parent_result_proof_dag_identity='',
        accounting_coherence_identity='', handoff_digest='', parent_action_degree=0, child_ground_size=0,
        candidate_count=0, accepted_count=0, parent_filter_work_bound=0, charged_log2_reduction_cost=0.0,
        same_child_execution_certified=False, parent_result_identity_equivalence_certified=False,
        coherence_identity='', reason=reason,
    )
def _dict(v,n):
    if type(v) is not dict or any(type(k) is not str for k in v): raise ValueError(f'{n} must be a literal dict snapshot')
    return v
def _get(v,k,p):
    if k not in v: raise ValueError(f'missing required field {p}.{k}')
    return v[k]
def _true(v,k,p):
    x=_get(v,k,p)
    if type(x) is not bool or x is not True: raise ValueError(f'{p}.{k} must be literal true')
def _false(v,k,p):
    x=_get(v,k,p)
    if type(x) is not bool or x is not False: raise ValueError(f'{p}.{k} must be literal false')
def _str(x,n):
    if type(x) is not str: raise ValueError(f'{n} must be a literal string')
    return x
def _dig(x,n):
    x=_str(x,n)
    if not _SHA.fullmatch(x): raise ValueError(f'{n} must be lowercase sha256:<64 hex>')
    return x
def _int(x,n,m=0):
    if type(x) is not int or x<m: raise ValueError(f'{n} must be a strict integer >= {m}')
    return x
def _real(x,n):
    if type(x) not in (int,float): raise ValueError(f'{n} must be a finite nonnegative real')
    y=float(x)
    if not math.isfinite(y) or y<0: raise ValueError(f'{n} must be a finite nonnegative real')
    return y
def _hash(v):
    return 'sha256:'+hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()
def _exec(s,replayed):
    if type(replayed) is not bool or replayed is not True: raise ValueError('rev3000-style execution binding must be independently replay-verified')
    v=_dict(s,'execution_snapshot')
    if _get(v,'schema_version','execution')!=1: raise ValueError('execution.schema_version mismatch')
    if _str(_get(v,'status','execution'),'execution.status')!=EXECUTION_STATUS: raise ValueError('execution.status mismatch')
    for k in ('certified','exact','complete','same_child_execution_certified'): _true(v,k,'execution')
    _false(v,'parent_result_identity_equivalence_certified','execution')
    po=_str(_get(v,'parent_outcome_kind','execution'),'execution.parent_outcome_kind'); co=_str(_get(v,'proof_dag_outcome_kind','execution'),'execution.proof_dag_outcome_kind')
    if po not in {'exact_empty','nonempty'} or co not in {'exact_empty','nonempty'}: raise ValueError('execution outcome mismatch')
    if co=='exact_empty' and po!='exact_empty': raise ValueError('exact-empty child execution cannot bind to nonempty parent result')
    n={'parent_outcome_kind':po,'child_execution_outcome_kind':co,'reduction_identity':_dig(_get(v,'reduction_identity','execution'),'execution.reduction_identity'),'child_result_identity':_dig(_get(v,'child_result_identity','execution'),'execution.child_result_identity'),'parent_result_identity':_dig(_get(v,'parent_filtered_result_identity','execution'),'execution.parent_filtered_result_identity'),'execution_closure_identity':_dig(_get(v,'execution_closure_identity','execution'),'execution.execution_closure_identity'),'execution_result_lift_digest':_dig(_get(v,'execution_result_lift_digest','execution'),'execution.execution_result_lift_digest'),'execution_proof_identity_digest':_dig(_get(v,'execution_proof_identity_digest','execution'),'execution.execution_proof_identity_digest'),'child_proof_identity_digest':_dig(_get(v,'child_proof_identity_digest','execution'),'execution.child_proof_identity_digest'),'child_ground_size':_int(_get(v,'child_ground_size','execution'),'execution.child_ground_size',1)}
    payload={'schema_version':1,'status':EXECUTION_STATUS,'parent_outcome_kind':po,'proof_dag_outcome_kind':co,'reduction_identity':n['reduction_identity'],'child_result_identity':n['child_result_identity'],'parent_filtered_result_identity':n['parent_result_identity'],'execution_closure_identity':n['execution_closure_identity'],'execution_result_lift_digest':n['execution_result_lift_digest'],'execution_proof_identity_digest':n['execution_proof_identity_digest'],'child_proof_identity_digest':n['child_proof_identity_digest'],'child_ground_size':n['child_ground_size'],'same_child_execution_certified':True,'parent_result_identity_equivalence_certified':False}
    b=_dig(_get(v,'binding_identity','execution'),'execution.binding_identity')
    if _hash(payload)!=b: raise ValueError('execution.binding_identity replay failed')
    n['execution_binding_identity']=b; return n
def _pa(s,replayed):
    if type(replayed) is not bool or replayed is not True: raise ValueError('rev2800-style proof/accounting certificate must be independently replay-verified')
    v=_dict(s,'proof_accounting_snapshot')
    if _get(v,'schema_version','proof_accounting')!=1: raise ValueError('proof_accounting.schema_version mismatch')
    if _str(_get(v,'status','proof_accounting'),'proof_accounting.status')!=PROOF_ACCOUNTING_STATUS: raise ValueError('proof_accounting.status mismatch')
    for k in ('certified','exact','complete'): _true(v,k,'proof_accounting')
    out=_str(_get(v,'outcome_kind','proof_accounting'),'proof_accounting.outcome_kind'); src=_str(_get(v,'source_status','proof_accounting'),'proof_accounting.source_status')
    expected=PARENT_EMPTY_STATUS if out=='exact_empty' else PARENT_NONEMPTY_STATUS if out=='nonempty' else None
    if expected is None or src!=expected: raise ValueError('proof_accounting outcome/source_status mismatch')
    n={'parent_outcome_kind':out,'source_status':src,'reduction_identity':_dig(_get(v,'reduction_identity','proof_accounting'),'proof_accounting.reduction_identity'),'semantic_binding_identity':_dig(_get(v,'semantic_binding_identity','proof_accounting'),'proof_accounting.semantic_binding_identity'),'child_instance_identity':_dig(_get(v,'child_instance_identity','proof_accounting'),'proof_accounting.child_instance_identity'),'child_result_identity':_dig(_get(v,'child_result_identity','proof_accounting'),'proof_accounting.child_result_identity'),'parent_result_identity':_dig(_get(v,'parent_result_identity','proof_accounting'),'proof_accounting.parent_result_identity'),'parent_result_proof_dag_identity':_dig(_get(v,'proof_dag_identity','proof_accounting'),'proof_accounting.proof_dag_identity'),'accounting_coherence_identity':_dig(_get(v,'accounting_coherence_identity','proof_accounting'),'proof_accounting.accounting_coherence_identity'),'handoff_digest':_dig(_get(v,'handoff_digest','proof_accounting'),'proof_accounting.handoff_digest'),'parent_action_degree':_int(_get(v,'parent_action_degree','proof_accounting'),'proof_accounting.parent_action_degree',1),'child_ground_size':_int(_get(v,'child_ground_size','proof_accounting'),'proof_accounting.child_ground_size',1),'candidate_count':_int(_get(v,'candidate_count','proof_accounting'),'proof_accounting.candidate_count'),'accepted_count':_int(_get(v,'accepted_count','proof_accounting'),'proof_accounting.accepted_count'),'parent_filter_work_bound':_int(_get(v,'parent_filter_work_bound','proof_accounting'),'proof_accounting.parent_filter_work_bound',1),'charged_log2_reduction_cost':_real(_get(v,'charged_log2_reduction_cost','proof_accounting'),'proof_accounting.charged_log2_reduction_cost')}
    if n['child_ground_size']>=n['parent_action_degree']: raise ValueError('proof_accounting must retain strict parent-to-child shrink')
    if n['accepted_count']>n['candidate_count']: raise ValueError('proof_accounting accepted_count exceeds candidate_count')
    if out=='exact_empty' and n['accepted_count']!=0: raise ValueError('exact-empty proof_accounting must have accepted_count == 0')
    if out=='nonempty' and n['accepted_count']<1: raise ValueError('nonempty proof_accounting must have accepted_count >= 1')
    payload={'schema_version':1,'status':PROOF_ACCOUNTING_STATUS,'outcome_kind':out,'source_status':src,'reduction_identity':n['reduction_identity'],'semantic_binding_identity':n['semantic_binding_identity'],'child_instance_identity':n['child_instance_identity'],'child_result_identity':n['child_result_identity'],'parent_result_identity':n['parent_result_identity'],'proof_dag_identity':n['parent_result_proof_dag_identity'],'accounting_coherence_identity':n['accounting_coherence_identity'],'handoff_digest':n['handoff_digest'],'parent_action_degree':n['parent_action_degree'],'child_ground_size':n['child_ground_size'],'candidate_count':n['candidate_count'],'accepted_count':n['accepted_count'],'parent_filter_work_bound':n['parent_filter_work_bound'],'charged_log2_reduction_cost':n['charged_log2_reduction_cost']}
    c=_dig(_get(v,'coherence_identity','proof_accounting'),'proof_accounting.coherence_identity')
    if _hash(payload)!=c: raise ValueError('proof_accounting.coherence_identity replay failed')
    n['proof_accounting_coherence_identity']=c; return n
def certify_parent_filtered_execution_proof_accounting_coherence(execution_snapshot:Any, proof_accounting_snapshot:Any, *, execution_replay_verified:bool, proof_accounting_replay_verified:bool):
    try:
        e=_exec(execution_snapshot,execution_replay_verified); p=_pa(proof_accounting_snapshot,proof_accounting_replay_verified)
        for k in ('parent_outcome_kind','reduction_identity','child_result_identity','parent_result_identity','child_ground_size'):
            if e[k]!=p[k] or type(e[k]) is not type(p[k]): raise ValueError(f'execution/proof_accounting {k} mismatch')
        payload={'schema_version':1,'status':OUTPUT_STATUS,'parent_outcome_kind':p['parent_outcome_kind'],'child_execution_outcome_kind':e['child_execution_outcome_kind'],'source_status':p['source_status'],'reduction_identity':p['reduction_identity'],'semantic_binding_identity':p['semantic_binding_identity'],'child_instance_identity':p['child_instance_identity'],'child_result_identity':p['child_result_identity'],'parent_result_identity':p['parent_result_identity'],'execution_binding_identity':e['execution_binding_identity'],'execution_closure_identity':e['execution_closure_identity'],'execution_result_lift_digest':e['execution_result_lift_digest'],'execution_proof_identity_digest':e['execution_proof_identity_digest'],'child_proof_identity_digest':e['child_proof_identity_digest'],'parent_result_proof_dag_identity':p['parent_result_proof_dag_identity'],'accounting_coherence_identity':p['accounting_coherence_identity'],'handoff_digest':p['handoff_digest'],'parent_action_degree':p['parent_action_degree'],'child_ground_size':p['child_ground_size'],'candidate_count':p['candidate_count'],'accepted_count':p['accepted_count'],'parent_filter_work_bound':p['parent_filter_work_bound'],'charged_log2_reduction_cost':p['charged_log2_reduction_cost'],'same_child_execution_certified':True,'parent_result_identity_equivalence_certified':False}
        return ParentFilteredExecutionProofAccountingCoherence(1,OUTPUT_STATUS,True,True,True,p['parent_outcome_kind'],e['child_execution_outcome_kind'],p['source_status'],p['reduction_identity'],p['semantic_binding_identity'],p['child_instance_identity'],p['child_result_identity'],p['parent_result_identity'],e['execution_binding_identity'],e['execution_closure_identity'],e['execution_result_lift_digest'],e['execution_proof_identity_digest'],e['child_proof_identity_digest'],p['parent_result_proof_dag_identity'],p['accounting_coherence_identity'],p['handoff_digest'],p['parent_action_degree'],p['child_ground_size'],p['candidate_count'],p['accepted_count'],p['parent_filter_work_bound'],p['charged_log2_reduction_cost'],True,False,_hash(payload),'replayed rev3000 child-execution lineage and rev2800 exact parent proof/accounting coherence bind to one parent-filtered result/reduction/child-result identity; child outcome and accounting units remain distinct')
    except (TypeError,ValueError,OverflowError,KeyError) as exc: return _fail(str(exc))
def replay_parent_filtered_execution_proof_accounting_coherence(certificate, execution_snapshot, proof_accounting_snapshot, *, execution_replay_verified:bool, proof_accounting_replay_verified:bool):
    if type(certificate) is not ParentFilteredExecutionProofAccountingCoherence: return False
    r=certify_parent_filtered_execution_proof_accounting_coherence(execution_snapshot,proof_accounting_snapshot,execution_replay_verified=execution_replay_verified,proof_accounting_replay_verified=proof_accounting_replay_verified)
    return bool(r.certified and r==certificate)
