from __future__ import annotations
import hashlib, json, math, re
from dataclasses import dataclass
from typing import Any
SCHEMA_VERSION=1
REV3100_STATUS='certified_parent_filtered_execution_proof_accounting_coherence'
OUTPUT_STATUS='certified_parent_filtered_result_identity_equivalence'
PARENT_NONEMPTY_STATUS='exact_parent_filtered_ground_coset'
PARENT_EMPTY_STATUS='exact_empty_parent_filtered_ground_coset'
_SHA=re.compile(r'^sha256:[0-9a-f]{64}$')

@dataclass(frozen=True)
class ParentResultIdentityEquivalence:
    schema_version:int; status:str; certified:bool; exact:bool; complete:bool
    parent_outcome_kind:str; source_status:str; reduction_identity:str; semantic_binding_identity:str
    child_instance_identity:str; child_result_identity:str; parent_result_identity:str
    representative:tuple[int,...]|None; parent_stabilizer_elements:tuple[tuple[int,...],...]
    parent_action_degree:int; child_ground_size:int; candidate_count:int; accepted_count:int
    parent_filter_work_bound:int; rev3100_coherence_identity:str
    parent_result_identity_equivalence_certified:bool; equivalence_identity:str; reason:str

def _fail(reason:str):
    return ParentResultIdentityEquivalence(1,'parent_filtered_result_identity_equivalence_not_certified',False,False,False,'undetermined','','','','','', '',None,(),0,0,0,0,0,'',False,'',reason)
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
def _hash(v,ascii=True):
    return 'sha256:'+hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=ascii,allow_nan=False).encode()).hexdigest()
def _seq(v,n):
    if type(v) not in (list,tuple): raise ValueError(f'{n} must be a literal list/tuple')
    return tuple(v)
def _perm(v,n,name):
    q=_seq(v,name)
    if len(q)!=n: raise ValueError(f'{name} has wrong degree')
    q=tuple(_int(x,f'{name}[{i}]') for i,x in enumerate(q))
    if any(x>=n for x in q) or len(set(q))!=n: raise ValueError(f'{name} is not a permutation')
    return q
def _id(n): return tuple(range(n))
def _compose(p,q): return tuple(q[p[i]] for i in range(len(p)))
def _inv(p):
    q=[0]*len(p)
    for i,j in enumerate(p): q[j]=i
    return tuple(q)
def _subgroup(elements,n):
    if not elements: raise ValueError('nonempty parent result requires stabilizer witnesses')
    if elements!=tuple(sorted(set(elements))): raise ValueError('parent_stabilizer_elements must be canonical sorted unique')
    s=set(elements)
    if _id(n) not in s: raise ValueError('parent_stabilizer_elements must contain identity')
    if any(_inv(g) not in s for g in elements): raise ValueError('parent_stabilizer_elements is not inverse closed')
    if any(_compose(g,h) not in s for g in elements for h in elements): raise ValueError('parent_stabilizer_elements is not composition closed')

def _parent(s,replayed):
    if type(replayed) is not bool or replayed is not True: raise ValueError('rev2200-style parent result must be independently replay-verified')
    v=_dict(s,'parent_result_snapshot')
    if _get(v,'schema_version','parent')!=1: raise ValueError('parent.schema_version mismatch')
    status=_str(_get(v,'status','parent'),'parent.status')
    if status not in {PARENT_NONEMPTY_STATUS,PARENT_EMPTY_STATUS}: raise ValueError('parent.status mismatch')
    for k in ('certified','exact','complete'): _true(v,k,'parent')
    n={
      'reduction_identity':_dig(_get(v,'reduction_identity','parent'),'parent.reduction_identity'),
      'semantic_binding_identity':_dig(_get(v,'semantic_binding_identity','parent'),'parent.semantic_binding_identity'),
      'child_instance_identity':_dig(_get(v,'child_instance_identity','parent'),'parent.child_instance_identity'),
      'child_result_identity':_dig(_get(v,'child_result_identity','parent'),'parent.child_result_identity'),
      'action_degree':_int(_get(v,'action_degree','parent'),'parent.action_degree',1),
      'candidate_count':_int(_get(v,'candidate_count','parent'),'parent.candidate_count'),
      'accepted_count':_int(_get(v,'accepted_count','parent'),'parent.accepted_count'),
      'work_bound':_int(_get(v,'work_bound','parent'),'parent.work_bound')}
    if n['accepted_count']>n['candidate_count']: raise ValueError('parent.accepted_count exceeds candidate_count')
    rep=_get(v,'representative','parent'); raw=_seq(_get(v,'parent_stabilizer_elements','parent'),'parent.parent_stabilizer_elements')
    if status==PARENT_EMPTY_STATUS:
        if n['accepted_count']!=0 or rep is not None or raw!=(): raise ValueError('exact-empty parent result carries nonempty coset data')
        rep=None; stab=(); outcome='exact_empty'
    else:
        if n['accepted_count']<1 or rep is None: raise ValueError('nonempty parent result lacks accepted representative')
        rep=_perm(rep,n['action_degree'],'parent.representative')
        stab=tuple(_perm(x,n['action_degree'],f'parent.parent_stabilizer_elements[{i}]') for i,x in enumerate(raw)); _subgroup(stab,n['action_degree'])
        if n['accepted_count']!=len(stab): raise ValueError('nonempty parent accepted_count must equal exact right-coset size')
        outcome='nonempty'
    payload={'schema_version':1,'status':status,**n,'representative':rep,'parent_stabilizer_elements':stab}
    # Preserve rev2200's exact key order-independent identity payload; work_bound is already in n.
    rid=_dig(_get(v,'result_identity','parent'),'parent.result_identity')
    if _hash(payload,False)!=rid: raise ValueError('parent.result_identity replay failed')
    return payload|{'result_identity':rid,'outcome':outcome}

def _rev3100(s,replayed):
    if type(replayed) is not bool or replayed is not True: raise ValueError('rev3100 coherence must be independently replay-verified')
    v=_dict(s,'rev3100_snapshot')
    if _get(v,'schema_version','rev3100')!=1: raise ValueError('rev3100.schema_version mismatch')
    if _str(_get(v,'status','rev3100'),'rev3100.status')!=REV3100_STATUS: raise ValueError('rev3100.status mismatch')
    for k in ('certified','exact','complete','same_child_execution_certified'): _true(v,k,'rev3100')
    _false(v,'parent_result_identity_equivalence_certified','rev3100')
    po=_str(_get(v,'parent_outcome_kind','rev3100'),'rev3100.parent_outcome_kind'); co=_str(_get(v,'child_execution_outcome_kind','rev3100'),'rev3100.child_execution_outcome_kind')
    if po not in {'exact_empty','nonempty'} or co not in {'exact_empty','nonempty'}: raise ValueError('rev3100 outcome kind mismatch')
    if co=='exact_empty' and po!='exact_empty': raise ValueError('rev3100 exact-empty child cannot bind to nonempty parent')
    src=_str(_get(v,'source_status','rev3100'),'rev3100.source_status'); expected=PARENT_EMPTY_STATUS if po=='exact_empty' else PARENT_NONEMPTY_STATUS
    if src!=expected: raise ValueError('rev3100 source_status mismatch')
    dfs=('reduction_identity','semantic_binding_identity','child_instance_identity','child_result_identity','parent_result_identity','execution_binding_identity','execution_closure_identity','execution_result_lift_digest','execution_proof_identity_digest','child_proof_identity_digest','parent_result_proof_dag_identity','accounting_coherence_identity','handoff_digest')
    d={k:_dig(_get(v,k,'rev3100'),f'rev3100.{k}') for k in dfs}
    pd=_int(_get(v,'parent_action_degree','rev3100'),'rev3100.parent_action_degree',1); cg=_int(_get(v,'child_ground_size','rev3100'),'rev3100.child_ground_size',1)
    if cg>=pd: raise ValueError('rev3100 must retain strict parent-to-child shrink')
    cc=_int(_get(v,'candidate_count','rev3100'),'rev3100.candidate_count'); ac=_int(_get(v,'accepted_count','rev3100'),'rev3100.accepted_count')
    if ac>cc or (po=='exact_empty' and ac!=0) or (po=='nonempty' and ac<1): raise ValueError('rev3100 candidate/accepted count mismatch')
    wb=_int(_get(v,'parent_filter_work_bound','rev3100'),'rev3100.parent_filter_work_bound',1); charge=_real(_get(v,'charged_log2_reduction_cost','rev3100'),'rev3100.charged_log2_reduction_cost')
    payload={'schema_version':1,'status':REV3100_STATUS,'parent_outcome_kind':po,'child_execution_outcome_kind':co,'source_status':src,**d,'parent_action_degree':pd,'child_ground_size':cg,'candidate_count':cc,'accepted_count':ac,'parent_filter_work_bound':wb,'charged_log2_reduction_cost':charge,'same_child_execution_certified':True,'parent_result_identity_equivalence_certified':False}
    cid=_dig(_get(v,'coherence_identity','rev3100'),'rev3100.coherence_identity')
    if _hash(payload)!=cid: raise ValueError('rev3100.coherence_identity replay failed')
    return payload|{'coherence_identity':cid}

def certify_parent_result_identity_equivalence(parent_result_snapshot:Any,rev3100_snapshot:Any,*,parent_result_replay_verified:bool,rev3100_replay_verified:bool):
    try:
        p=_parent(parent_result_snapshot,parent_result_replay_verified); c=_rev3100(rev3100_snapshot,rev3100_replay_verified)
        checks={'outcome':(p['outcome'],c['parent_outcome_kind']),'source_status':(p['status'],c['source_status']),'reduction_identity':(p['reduction_identity'],c['reduction_identity']),'semantic_binding_identity':(p['semantic_binding_identity'],c['semantic_binding_identity']),'child_instance_identity':(p['child_instance_identity'],c['child_instance_identity']),'child_result_identity':(p['child_result_identity'],c['child_result_identity']),'parent_result_identity':(p['result_identity'],c['parent_result_identity']),'child_ground_size':(p['action_degree'],c['child_ground_size']),'candidate_count':(p['candidate_count'],c['candidate_count']),'accepted_count':(p['accepted_count'],c['accepted_count']),'parent_filter_work_bound':(p['work_bound'],c['parent_filter_work_bound'])}
        for k,(a,b) in checks.items():
            if type(a) is not type(b) or a!=b: raise ValueError(f'parent/rev3100 {k} mismatch')
        if c['child_execution_outcome_kind']=='exact_empty' and p['outcome']!='exact_empty': raise ValueError('exact-empty child execution disagrees with replayed parent result')
        payload={'schema_version':1,'status':OUTPUT_STATUS,'parent_outcome_kind':p['outcome'],'source_status':p['status'],'reduction_identity':p['reduction_identity'],'semantic_binding_identity':p['semantic_binding_identity'],'child_instance_identity':p['child_instance_identity'],'child_result_identity':p['child_result_identity'],'parent_result_identity':p['result_identity'],'representative':p['representative'],'parent_stabilizer_elements':p['parent_stabilizer_elements'],'parent_action_degree':c['parent_action_degree'],'child_ground_size':p['action_degree'],'candidate_count':p['candidate_count'],'accepted_count':p['accepted_count'],'parent_filter_work_bound':p['work_bound'],'rev3100_coherence_identity':c['coherence_identity'],'parent_result_identity_equivalence_certified':True}
        eid=_hash(payload)
        return ParentResultIdentityEquivalence(1,OUTPUT_STATUS,True,True,True,p['outcome'],p['status'],p['reduction_identity'],p['semantic_binding_identity'],p['child_instance_identity'],p['child_result_identity'],p['result_identity'],p['representative'],p['parent_stabilizer_elements'],c['parent_action_degree'],p['action_degree'],p['candidate_count'],p['accepted_count'],p['work_bound'],c['coherence_identity'],True,eid,'one independently replayed rev2200 exact parent-filtered result is exactly the parent-result identity carried by the independently replayed rev3100 chain; identity equivalence is certified only on the Johnson-ground parent-filter boundary')
    except (TypeError,ValueError,OverflowError,KeyError) as exc: return _fail(str(exc))
def replay_parent_result_identity_equivalence(cert,parent_result_snapshot,rev3100_snapshot,*,parent_result_replay_verified:bool,rev3100_replay_verified:bool):
    if type(cert) is not ParentResultIdentityEquivalence: return False
    r=certify_parent_result_identity_equivalence(parent_result_snapshot,rev3100_snapshot,parent_result_replay_verified=parent_result_replay_verified,rev3100_replay_verified=rev3100_replay_verified)
    return bool(r.certified and r==cert)
