from jagi.learning.program_synthesis import Affine, Field, StringPrefix, synthesize_programs


def test_two_examples_synthesize_affine_program():
    programs = synthesize_programs([(2, 5), (4, 9)])
    affine = [p for p in programs if isinstance(p, Affine)]
    assert len(affine) == 1
    assert affine[0].execute(10) == 21


def test_mapping_examples_synthesize_field_projection():
    programs = synthesize_programs([
        ({"name": "A", "age": 7}, "A"),
        ({"name": "B", "age": 9}, "B"),
    ])
    fields = [p for p in programs if isinstance(p, Field)]
    assert len(fields) == 1
    assert fields[0].key == "name"
    assert fields[0].execute({"name": "C"}) == "C"


def test_string_examples_synthesize_prefix_rule():
    programs = synthesize_programs([("cat", "pre-cat"), ("dog", "pre-dog")])
    prefixes = [p for p in programs if isinstance(p, StringPrefix)]
    assert len(prefixes) == 1
    assert prefixes[0].execute("owl") == "pre-owl"


def test_single_example_can_remain_ambiguous():
    programs = synthesize_programs([(2, 4)])
    assert len(programs) >= 2
    predictions = {p.execute(3) for p in programs}
    assert len(predictions) >= 2
