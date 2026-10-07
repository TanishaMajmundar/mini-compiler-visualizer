from compiler.codegen import generate
from compiler.lexer import tokenize
from compiler.optimizer import optimize, side_by_side
from compiler.parser import parse
from compiler.pipeline import compile_source


def run(source: str):
    """Source -> (original TAC, optimized TAC, change log). Skips semantic checks."""
    tokens, _ = tokenize(source)
    tac = generate(parse(tokens))
    optimized, changes = optimize(tac)
    return tac, optimized, changes


def texts(code) -> list[str]:
    return [str(i) for i in code]


def test_folding_and_propagation_chain():
    _, optimized, _ = run("int a = 2;\nint x = a + 3 * 4;")
    assert texts(optimized) == ["a = 2", "x = 14"]


def test_overwritten_assignment_is_removed():
    _, optimized, _ = run("int x = 5;\nx = 10;\nint y = x * 2;")
    assert texts(optimized) == ["x = 10", "y = 20"]


def test_loop_variable_is_not_propagated():
    tac, optimized, changes = run("int i = 0;\nwhile (i < 3) { i = i + 1; }")
    assert texts(optimized) == texts(tac)
    assert changes == []


def test_constants_are_forgotten_at_a_label():
    _, optimized, _ = run("int x = 1;\nif (x < 2) { x = 5; }\nint y = x + 1;")
    assert texts(optimized) == [
        "x = 1",
        "ifFalse 1 goto L1",
        "x = 5",
        "L1:",
        "t2 = x + 1",      # x is NOT replaced: x may be 1 or 5 here
        "y = t2",
    ]


def test_constants_inside_loop_body_are_folded():
    _, optimized, _ = run(
        "int i = 0;\nint total = 0;\nwhile (i < 3) {\n int k = 2 * 5;\n total = total + k;\n i = i + 1;\n}"
    )
    assert texts(optimized) == [
        "i = 0", "total = 0", "L1:", "t1 = i < 3", "ifFalse t1 goto L2",
        "k = 10", "t3 = total + 10", "total = t3", "t4 = i + 1", "i = t4",
        "goto L1", "L2:",
    ]


def test_exact_int_division_is_folded():
    _, optimized, _ = run("int a = 8 / 2;")
    assert texts(optimized) == ["a = 4"]


def test_inexact_int_division_is_not_folded():
    _, optimized, changes = run("int a = 7 / 2;")
    assert texts(optimized) == ["t1 = 7 / 2", "a = t1"]
    assert changes == []


def test_division_by_zero_is_not_folded():
    _, optimized, _ = run("int a = 5 / 0;")
    assert texts(optimized) == ["t1 = 5 / 0", "a = t1"]


def test_float_folding():
    _, optimized, _ = run("float price = 9.5;\nfloat total = price * 2;")
    assert texts(optimized) == ["price = 9.5", "total = 19.0"]


def test_user_variable_named_like_a_temp_is_kept():
    _, optimized, _ = run("int t1 = 5;\nint y = t1 + 1;")
    assert texts(optimized) == ["t1 = 5", "y = 6"]


def test_unused_user_variable_is_kept():
    _, optimized, _ = run("int a = 1;")
    assert texts(optimized) == ["a = 1"]


def test_relational_operator_is_folded():
    _, optimized, _ = run("while (1 < 2) {\n}")
    assert texts(optimized) == ["L1:", "ifFalse 1 goto L2", "goto L1", "L2:"]


def test_change_log_contains_all_three_kinds():
    _, _, changes = run("int a = 2;\nint x = a + 3 * 4;")
    assert {c.kind for c in changes} == {
        "Constant propagation",
        "Constant folding",
        "Dead code elimination",
    }


def test_side_by_side_marks_removed_and_changed_lines():
    tac, optimized, changes = run("int a = 2;\nint x = a + 3 * 4;")
    rows = side_by_side(tac, optimized, changes)
    assert [r.status for r in rows] == ["unchanged", "removed", "removed", "changed"]
    assert rows[3].before == "x = t2" and rows[3].after == "x = 14"


def test_input_tac_is_not_modified():
    tokens, _ = tokenize("int a = 2;\nint x = a + 3 * 4;")
    tac = generate(parse(tokens))
    before = texts(tac)
    optimize(tac)
    assert texts(tac) == before


def test_pipeline_runs_the_optimizer():
    result = compile_source("int a = 2;\nint x = a + 3 * 4;")
    assert texts(result.optimized) == ["a = 2", "x = 14"]
    assert len(result.tac) == 4          # the original TAC is kept
    assert result.changes


def test_pipeline_skips_optimizer_when_compilation_fails():
    result = compile_source("int x = 1;\ny = 2;")
    assert result.optimized == [] and result.changes == []