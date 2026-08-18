from dataclasses import dataclass

from jagi.learning.version_space import Demonstration, VersionSpaceLearner


@dataclass(frozen=True)
class ArithmeticRule:
    hypothesis_id: str
    op: str
    k: int

    def predict(self, x):
        if self.op == "add":
            return x + self.k
        if self.op == "mul":
            return x * self.k
        raise ValueError(self.op)


def hypotheses():
    return [
        ArithmeticRule("add1", "add", 1),
        ArithmeticRule("add2", "add", 2),
        ArithmeticRule("mul2", "mul", 2),
        ArithmeticRule("mul3", "mul", 3),
    ]


def test_sparse_demonstrations_eliminate_inconsistent_executable_rules():
    learner = VersionSpaceLearner(hypotheses())
    assert learner.observe(Demonstration(2, 4)) == 2
    assert learner.observe(Demonstration(3, 5)) == 1
    prediction = learner.predict(10)
    assert prediction.resolved
    assert prediction.top == 12


def test_ambiguous_prediction_exposes_support_instead_of_fake_certainty():
    learner = VersionSpaceLearner(hypotheses())
    learner.observe(Demonstration(2, 4))
    prediction = learner.predict(4)
    assert not prediction.resolved
    assert dict(prediction.alternatives) == {6: 0.5, 8: 0.5}


def test_active_query_prefers_input_that_splits_remaining_rules():
    learner = VersionSpaceLearner(hypotheses())
    learner.observe(Demonstration(2, 4))
    assert learner.choose_disambiguating_query([2, 3, 4]) in {3, 4}


def test_contradictory_evidence_does_not_silently_replace_version_space():
    learner = VersionSpaceLearner(hypotheses())
    learner.observe(Demonstration(2, 4))
    remaining = tuple(h.hypothesis_id for h in learner.hypotheses)
    assert learner.observe(Demonstration(2, 999)) == 0
    assert tuple(h.hypothesis_id for h in learner.hypotheses) == remaining
    assert learner.contradictions == 1
