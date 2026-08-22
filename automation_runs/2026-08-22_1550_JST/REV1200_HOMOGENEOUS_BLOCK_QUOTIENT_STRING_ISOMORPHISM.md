# Rev1200: homogeneous-block quotient String-Isomorphism execution

Rev1200 closes one CRX3 algorithmic-consumer leaf after the main-integrated rev274 block-action provenance, rev275 exact kernel/image factorization, and rev950 proof-DAG consumer.

The executor accepts those exact certificates plus one string on the certified source quotient blocks and one string on the certified target quotient blocks. It first replays rev274 and rev275 and requires rev950 proof-DAG certification. The target string is pulled back through rev274's canonical block bijection, and the source quotient image is reconstructed from the certified quotient generators. Equal string values are encoded as ordered partition cells and solved with the main-integrated exact canonical partition transporter. A completed partition orbit with no witness is exact empty; exceeding the explicit state cap is undetermined and fail-closed.

When a witness exists, the source feature stabilizer is conjugated across the cross-coordinate representative into the certified target quotient image. The result is returned in the repository `RightCoset` convention as the complete quotient-level String-Isomorphism set. The implementation verifies that every target-stabilizer generator lies in the certified target quotient image and stabilizes the target string.

This leaf deliberately does **not** perform the original-domain preimage/transporter lift. That remains the independently owned rev278 scope. It also does not modify rev950, state-orbit proof-DAG work, corrected Split-or-Johnson work, shared coordination code, `MAIN.md`, or revision ledgers.

## Coordination validation

The first PR-head functional run passed compilation, all 12 inherited rev275 regressions, all 13 inherited rev950 regressions, all 12 focused rev1200 regressions, and the sibling/original-domain-lift dependency guard. Its canonical admission preview then failed only on a temporary `target_revision=1200` collision with a corrected Split-or-Johnson claim created one minute after this claim. That later lane has since marked its rev1200 claim superseded and moved to rev1300 while explicitly excluding this rev1200 quotient-SI PR. No sibling branch, claim, PR, or workflow was altered here. A normal documentation follow-up commit is used to let PR CI re-evaluate the now-current canonical main claim registry; no prior workflow is manually rerun or cancelled.

The result is an exact quotient-domain consumer only. It does not close CRX3, GI, or AGI. State remains `NOT_AGI`.
