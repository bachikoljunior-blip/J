# AGI-GI rev256: bounded relation-image exact transporter coset

This revision directly attempts the unresolved CRX1 `k<=2` leaf in the bounded
case where the upstream action is supplied as a complete explicit finite group.

It encodes every named unary/binary relation as a Boolean string on a faithful
auxiliary action: a neutral point layer, every unary point slot, and every
ordered binary-pair slot.  Every original permutation induces one auxiliary
permutation.  The independent rev251 verifier then replays the whole induced
group, proves closure, compares the complete transporter set, and reconstructs
it as a right coset of the target stabilizer.

The complete group-composition and action-check multiplicities are checked
before the first candidate relation match.  Cap excess is `undetermined`, not
an exact answer.  Invalid or duplicate group enumerations fail closed; the
neutral point layer makes the action faithful even for an empty relation
signature.

The construction is the standard finite relational-structure-to-colored-graph
incidence reduction combined with exhaustive finite group action.  It contains
the already-main-reachable rev248 exact unary/binary witness and rev251 replay
verification ideas without treating either as a general quasipolynomial image-SI
algorithm.

Strict boundary: exactness is relative only to the explicitly enumerated input
group and the bounded auxiliary action.  This does not prove that an upstream
group is complete, does not eliminate enumeration for large groups, does not
close general CRX1, graph isomorphism, or AGI.  AGI remains `NOT_AGI`.
