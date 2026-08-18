from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jagi_eval.evidence import public_key_b64, replication_consensus, sign_report, verify_report


def report(team: str, fresh: bool = False):
    h = lambda ch: ch * 64
    return {
        "evaluator_team": team,
        "candidate_sha256": h("a"),
        "harness_sha256": h("b"),
        "environment_sha256": h("c"),
        "suite_sha256": h("d" if fresh else "e"),
        "preregistration_sha256": h("f"),
        "metrics_sha256": h("1"),
        "exclusions_sha256": h("2"),
        "fresh_sealed_suite": fresh,
        "gate_decisions": {f"G{i}": True for i in range(8)},
    }


def envelope(team: str, key: Ed25519PrivateKey, fresh: bool = False):
    r = report(team, fresh)
    return {"report": r, "signature": sign_report(r, key)}


def test_signed_report_verifies_and_tamper_fails():
    key = Ed25519PrivateKey.generate()
    r = report("team-a")
    signature = sign_report(r, key)
    assert verify_report(r, signature, public_key_b64(key)).valid
    r["gate_decisions"]["G3"] = False
    assert not verify_report(r, signature, public_key_b64(key)).valid


def test_two_independent_teams_with_fresh_suite_reach_consensus():
    a = Ed25519PrivateKey.generate()
    b = Ed25519PrivateKey.generate()
    registry = {
        "team-a": {"independent": True, "public_key_b64": public_key_b64(a)},
        "team-b": {"independent": True, "public_key_b64": public_key_b64(b)},
    }
    decision = replication_consensus([envelope("team-a", a), envelope("team-b", b, fresh=True)], registry)
    assert decision.passed, decision.reasons


def test_one_team_cannot_self_replicate_twice():
    a = Ed25519PrivateKey.generate()
    registry = {"team-a": {"independent": True, "public_key_b64": public_key_b64(a)}}
    decision = replication_consensus([envelope("team-a", a), envelope("team-a", a, fresh=True)], registry)
    assert not decision.passed


def test_nonindependent_team_is_rejected():
    a = Ed25519PrivateKey.generate()
    b = Ed25519PrivateKey.generate()
    registry = {
        "team-a": {"independent": True, "public_key_b64": public_key_b64(a)},
        "team-b": {"independent": False, "public_key_b64": public_key_b64(b)},
    }
    decision = replication_consensus([envelope("team-a", a), envelope("team-b", b, fresh=True)], registry)
    assert not decision.passed
