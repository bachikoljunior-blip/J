from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from permutation_group_schreier import Permutation, StabilizerChain, compose, identity, inverse, schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset


def enumerate_group(chain:StabilizerChain,*,max_elements:int=100000) -> Optional[Tuple[Permutation,...]]:
    if max_elements<1: raise ValueError('max_elements must be positive')
    if chain.order>max_elements: return None
    n=chain.degree; e=identity(n); gens=chain.original_generators or (e,); seen={e}; q=deque([e])
    while q:
        x=q.popleft()
        for g in gens:
            y=compose(x,g)
            if y not in seen:
                seen.add(y)
                if len(seen)>max_elements: return None
                q.append(y)
    if len(seen)!=chain.order: raise AssertionError('enumerated group size disagrees with stabilizer-chain order')
    return tuple(sorted(seen))


def act_string(values:Iterable[object],p:Permutation) -> Tuple[object,...]:
    values=tuple(values)
    if len(values)!=len(p): raise ValueError('degree mismatch')
    out=[None]*len(p)
    for i,v in enumerate(values): out[p[i]]=v
    return tuple(out)


@dataclass(frozen=True)
class TransporterResult:
    status: str
    coset: Optional[RightCoset]
    transporter_size: int
    reason: str


def bounded_string_transporter(chain:StabilizerChain,source:Iterable[object],target:Iterable[object],*,max_elements:int=100000) -> TransporterResult:
    source=tuple(source); target=tuple(target)
    if len(source)!=chain.degree or len(target)!=chain.degree: raise ValueError('degree mismatch')
    elements=enumerate_group(chain,max_elements=max_elements)
    if elements is None: return TransporterResult('undetermined_group_too_large',None,0,'group order exceeds explicit enumeration limit')
    hits=tuple(g for g in elements if act_string(source,g)==target)
    if not hits: return TransporterResult('empty_transporter',None,0,'no enumerated group element transports source string to target')
    rep=hits[0]
    # With act(source, p*q) = act(act(source,p),q), the transporter is rep*H_t
    # where H_t stabilizes the target string.
    stabilizer_elems=[g for g in elements if act_string(target,g)==target]
    stab=schreier_stabilizer_chain(stabilizer_elems or [identity(chain.degree)])
    cos=RightCoset(stab,rep)
    if stab.order!=len(hits) or not all(cos.contains(g) for g in hits):
        raise AssertionError('transporter coset construction failed internal consistency')
    return TransporterResult('exact_transporter_coset',cos,len(hits),'bounded exhaustive transporter represented as one exact right coset')


@dataclass(frozen=True)
class CosetIntersectionResult:
    status: str
    coset: Optional[RightCoset]
    intersection_size: int
    reason: str


def bounded_right_coset_intersection(a:RightCoset,b:RightCoset,*,max_elements:int=100000) -> CosetIntersectionResult:
    if a.subgroup.degree!=b.subgroup.degree: raise ValueError('degree mismatch')
    ea=enumerate_group(a.subgroup,max_elements=max_elements); eb=enumerate_group(b.subgroup,max_elements=max_elements)
    if ea is None or eb is None:
        return CosetIntersectionResult('undetermined_group_too_large',None,0,'one subgroup order exceeds explicit enumeration limit')
    sa={compose(a.representative,h) for h in ea}; sb={compose(b.representative,h) for h in eb}; inter=sa&sb
    if not inter: return CosetIntersectionResult('empty_intersection',None,0,'right cosets are disjoint')
    rep=min(inter); rel=[compose(inverse(rep),g) for g in inter]
    subgroup=schreier_stabilizer_chain(rel or [identity(a.subgroup.degree)])
    cos=RightCoset(subgroup,rep)
    if subgroup.order!=len(inter) or not all(cos.contains(g) for g in inter):
        raise AssertionError('intersection coset construction failed internal consistency')
    return CosetIntersectionResult('exact_intersection_coset',cos,len(inter),'bounded explicit intersection represented as one exact right coset')
