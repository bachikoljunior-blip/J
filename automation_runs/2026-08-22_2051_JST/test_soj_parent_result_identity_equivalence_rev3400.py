from __future__ import annotations
import dataclasses, hashlib, json, math, unittest
from soj_parent_result_identity_equivalence_v1 import PARENT_EMPTY_STATUS,PARENT_NONEMPTY_STATUS,REV3100_STATUS,certify_parent_result_identity_equivalence,replay_parent_result_identity_equivalence

def h(tag): return 'sha256:'+hashlib.sha256(tag.encode()).hexdigest()
def digest(v,ascii=True): return 'sha256:'+hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=ascii,allow_nan=False).encode()).hexdigest()
def parent(empty=False):
    status=PARENT_EMPTY_STATUS if empty else PARENT_NONEMPTY_STATUS; rep=None if empty else (1,0,2); stab=() if empty else ((0,1,2),(1,0,2)); count=0 if empty else 2
    p={'schema_version':1,'status':status,'reduction_identity':h('reduction'),'semantic_binding_identity':h('semantic'),'child_instance_identity':h('child-instance'),'child_result_identity':h('child-result'),'action_degree':3,'candidate_count':count,'accepted_count':count,'representative':rep,'parent_stabilizer_elements':stab,'work_bound':17}
    return p|{'certified':True,'exact':True,'complete':True,'result_identity':digest(p,False)}
def rehash_parent(p):
    p=dict(p); keys=('schema_version','status','reduction_identity','semantic_binding_identity','child_instance_identity','child_result_identity','action_degree','candidate_count','accepted_count','representative','parent_stabilizer_elements','work_bound'); p['result_identity']=digest({k:p[k] for k in keys},False); return p
def coherence(p,child=None):
    po='exact_empty' if p['status']==PARENT_EMPTY_STATUS else 'nonempty'; child=child or po
    c={'schema_version':1,'status':REV3100_STATUS,'parent_outcome_kind':po,'child_execution_outcome_kind':child,'source_status':p['status'],'reduction_identity':p['reduction_identity'],'semantic_binding_identity':p['semantic_binding_identity'],'child_instance_identity':p['child_instance_identity'],'child_result_identity':p['child_result_identity'],'parent_result_identity':p['result_identity'],'execution_binding_identity':h('execution-binding'),'execution_closure_identity':h('closure'),'execution_result_lift_digest':h('lift'),'execution_proof_identity_digest':h('proof'),'child_proof_identity_digest':h('child-proof'),'parent_result_proof_dag_identity':h('parent-dag'),'accounting_coherence_identity':h('accounting'),'handoff_digest':h('handoff'),'parent_action_degree':6,'child_ground_size':p['action_degree'],'candidate_count':p['candidate_count'],'accepted_count':p['accepted_count'],'parent_filter_work_bound':p['work_bound'],'charged_log2_reduction_cost':3.0,'same_child_execution_certified':True,'parent_result_identity_equivalence_certified':False}
    return c|{'certified':True,'exact':True,'complete':True,'coherence_identity':digest(c)}
def rehash(c):
    c=dict(c); payload={k:v for k,v in c.items() if k not in {'certified','exact','complete','coherence_identity'}}
    if type(payload.get('charged_log2_reduction_cost')) in (int,float) and math.isfinite(float(payload['charged_log2_reduction_cost'])): payload['charged_log2_reduction_cost']=float(payload['charged_log2_reduction_cost'])
    c['coherence_identity']=digest(payload); return c
def certify(p=None,c=None,pg=True,cg=True):
    p=parent() if p is None else p; c=coherence(p) if c is None else c
    return certify_parent_result_identity_equivalence(p,c,parent_result_replay_verified=pg,rev3100_replay_verified=cg)

class Tests(unittest.TestCase):
    def test_nonempty_success_and_replay(self):
        p=parent(); c=coherence(p); r=certify(p,c); self.assertTrue(r.certified and r.parent_result_identity_equivalence_certified); self.assertEqual(r.parent_result_identity,p['result_identity']); self.assertTrue(replay_parent_result_identity_equivalence(r,p,c,parent_result_replay_verified=True,rev3100_replay_verified=True))
    def test_empty_success(self):
        p=parent(True); r=certify(p,coherence(p)); self.assertTrue(r.certified); self.assertEqual(r.parent_outcome_kind,'exact_empty'); self.assertIsNone(r.representative)
    def test_parent_replay_gate(self):
        p=parent(); self.assertFalse(certify(p,coherence(p),pg=False).certified)
    def test_rev3100_replay_gate(self):
        p=parent(); self.assertFalse(certify(p,coherence(p),cg=False).certified)
    def test_parent_identity_tamper(self):
        p=parent(); p['result_identity']=h('wrong'); self.assertFalse(certify(p,coherence(parent())).certified)
    def test_coherence_identity_tamper(self):
        p=parent(); c=coherence(p); c['coherence_identity']=h('wrong'); self.assertFalse(certify(p,c).certified)
    def test_reduction_mismatch(self): self._mutate('reduction_identity',h('other'))
    def test_semantic_mismatch(self): self._mutate('semantic_binding_identity',h('other'))
    def test_child_instance_mismatch(self): self._mutate('child_instance_identity',h('other'))
    def test_child_result_mismatch(self): self._mutate('child_result_identity',h('other'))
    def test_child_ground_mismatch(self): self._mutate('child_ground_size',2)
    def test_candidate_count_mismatch(self): self._mutate('candidate_count',3)
    def test_work_bound_mismatch(self): self._mutate('parent_filter_work_bound',18)
    def _mutate(self,key,value):
        p=parent(); c=coherence(p); c[key]=value; c=rehash(c); self.assertFalse(certify(p,c).certified)
    def test_noncanonical_stabilizer(self):
        p=parent(); p['parent_stabilizer_elements']=tuple(reversed(p['parent_stabilizer_elements'])); p=rehash_parent(p); self.assertFalse(certify(p,coherence(p)).certified)
    def test_nonclosed_stabilizer(self):
        p=parent(); p['parent_stabilizer_elements']=((0,1,2),(1,2,0)); p=rehash_parent(p); self.assertFalse(certify(p,coherence(p)).certified)
    def test_coset_size_count_mismatch(self):
        p=parent(); p['accepted_count']=1; p=rehash_parent(p); self.assertFalse(certify(p,coherence(p)).certified)
    def test_coercible_boolean_rejected(self):
        p=parent(); c=coherence(p); c['same_child_execution_certified']=1; c=rehash(c); self.assertFalse(certify(p,c).certified)
    def test_source_status_mismatch(self):
        p=parent(); c=coherence(p); c['source_status']=PARENT_EMPTY_STATUS; c=rehash(c); self.assertFalse(certify(p,c).certified)
    def test_nonfinite_cost_rejected(self):
        p=parent(); c=coherence(p); c['charged_log2_reduction_cost']=math.inf; self.assertFalse(certify(p,c).certified)
    def test_certificate_tamper_breaks_replay(self):
        p=parent(); c=coherence(p); r=certify(p,c); bad=dataclasses.replace(r,candidate_count=r.candidate_count+1); self.assertFalse(replay_parent_result_identity_equivalence(bad,p,c,parent_result_replay_verified=True,rev3100_replay_verified=True))

if __name__=='__main__': unittest.main(verbosity=2)
