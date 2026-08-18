from jagi.core import Action, CognitiveCore, CognitiveState, Feedback, Goal, Observation, Transition


class TinyCore:
    def initialize(self, episode_id, goals, tools):
        return CognitiveState(episode_id=episode_id, step=0, active_goal_ids=tuple(g.goal_id for g in goals))

    def act(self, state, observations, goals, tools):
        return Action("a1", "respond", "user", {"text": "ok"}, "satisfy the active goal")

    def learn(self, state, transition):
        return transition.current

    def snapshot(self):
        return b"tiny"


def test_structural_core_protocol_is_runtime_checkable():
    assert isinstance(TinyCore(), CognitiveCore)


def test_transition_must_advance_one_step_and_preserve_episode():
    before = CognitiveState("e", 0, ("g",))
    after = CognitiveState("e", 1, ("g",), uncertainty=0.5)
    transition = Transition(
        before,
        (Observation("text", "hello", "user"),),
        Action("a", "respond", "user", {}, "answer"),
        Feedback("evaluator", {"utility": 1.0}, True),
        after,
    )
    assert transition.current.step == 1


def test_goal_requires_explicit_success_criteria():
    try:
        Goal("g", "do something", ())
    except ValueError:
        pass
    else:
        raise AssertionError("goal without success criteria must be rejected")


def test_candidate_package_does_not_import_evaluation_package():
    import inspect
    import jagi.core as core
    assert "jagi_eval" not in inspect.getsource(core)
