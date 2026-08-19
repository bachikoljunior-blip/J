from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from permutation_group_schreier import Permutation, StabilizerChain, compose, identity, inverse, schreier_stabilizer_chain, validate_perm
from coset_stabilizer_primitives import RightCoset
from bounded_group_transport import act_string


@dataclass(frozen=True)
class StateOrbitTransporter:
    status: str
    stabilizer: Optional[StabilizerChain]
    transporter: Optional[RightCoset]
    orbit_size: int
    reason: str


def string_orbit_stabilizer_transporter(
    generators:Iterable[Iterable[int]], source:Iterable[object], target:Optional[Iterable[object]]=None,
    *, max_images:int=100000
) -> StateOrbitTransporter:
    """Schreier stabilizer/transporter on the orbit of a string, not group elements.

    Complexity is proportional to the number of distinct string images reached
    (times generator/action cost), which can be far smaller than |G|. The search
    is exact if the complete image orbit fits `max_images`; otherwise it returns
    fail-closed without a stabilizer or transporter certificate.
    """
    gens=tuple(validate_perm(g) for g in generators)
    if not gens: raise ValueError('at least one generator required')
    n=len(gens[0]); source=tuple(source); target=None if target is None else tuple(target)
    if len(source)!=n or (target is not None and len(target)!=n): raise ValueError('degree mismatch')
    if max_images<1: raise ValueError('max_images must be positive')

    e=identity(n); trans={source:e}; q=deque([source])
    while q:
        state=q.popleft(); ts=trans[state]
        for g in gens:
            nxt=act_string(state,g)
            if nxt not in trans:
                if len(trans)>=max_images:
                    return StateOrbitTransporter('undetermined_image_orbit_limit',None,None,len(trans),'string image orbit exceeds max_images')
                trans[nxt]=compose(ts,g); q.append(nxt)

    # Schreier generators for the stabilizer of `source` under the induced action.
    stab_gens=[]
    for state,ts in trans.items():
        for g in gens:
            nxt=act_string(state,g); tn=trans[nxt]
            h=compose(compose(ts,g),inverse(tn))
            if h!=e: stab_gens.append(h)
    source_stab=schreier_stabilizer_chain(stab_gens or [e])

    if target is None:
        return StateOrbitTransporter('exact_state_stabilizer',source_stab,None,len(trans),'complete string-image orbit and Schreier stabilizer')
    if target not in trans:
        return StateOrbitTransporter('empty_transporter',source_stab,None,len(trans),'target string is outside the complete source image orbit')

    rep=trans[target]
    # Target stabilizer is rep^-1 H_source rep under left-to-right composition.
    ht=[]
    for h in source_stab.original_generators:
        ht.append(compose(compose(inverse(rep),h),rep))
    target_stab=schreier_stabilizer_chain(ht or [e])
    cos=RightCoset(target_stab,rep)
    return StateOrbitTransporter('exact_transporter_coset',source_stab,cos,len(trans),'complete state orbit; exact source stabilizer and right transporter coset')
