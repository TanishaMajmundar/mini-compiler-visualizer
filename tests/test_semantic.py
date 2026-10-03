from compiler.lexer import tokenize
from compiler.parser import parse
from compiler.semantic import analyze


def run(source: str):
    tokens, _ = tokenize(source)
    return analyze(parse(tokens))


def errors_of(issues):
    return [i for i in issues if i.severity == "error"]


def warnings_of(issues):
    return [i for i in issues if i.severity == "warning"]


def test_valid_program_has_no_issues():
    symbols, issues = run("int x = 1;\nfloat y = 2.5;\nx = x + 1;")
    assert issues == []
    assert [(s.name, s.type, s.scope, s.line) for s in symbols] == [
        ("x", "int", "global", 1),
        ("y", "float", "global", 2),
    ]


def test_undeclared_variable_in_assignment():
    _, issues = run("int x;\ny = 1;")
    assert len(errors_of(issues)) == 1
    assert str(issues[0]) == "Semantic error: 'y' used before declaration (line 2)"


def test_undeclared_variable_in_expression():
    _, issues = run("int x = z + 1;")
    assert str(errors_of(issues)[0]) == "Semantic error: 'z' used before declaration (line 1)"


def test_duplicate_declaration_same_scope():
    _, issues = run("int x = 1;\nint x = 2;")
    assert len(errors_of(issues)) == 1
    assert "already declared" in issues[0].message
    assert issues[0].line == 2


def test_shadowing_in_inner_block_is_allowed():
    symbols, issues = run("int x = 1;\n{\n int x = 2;\n}")
    assert issues == []
    assert [s.scope for s in symbols] == ["global", "block 1"]


def test_variable_not_visible_after_block():
    _, issues = run("{\n int a = 1;\n}\na = 2;")
    assert len(errors_of(issues)) == 1
    assert issues[0].line == 4


def test_float_to_int_is_a_warning_not_an_error():
    _, issues = run("int x = 3.5;")
    assert errors_of(issues) == []
    assert len(warnings_of(issues)) == 1


def test_int_to_float_gives_no_warning():
    _, issues = run("float y = 3;")
    assert issues == []


def test_float_propagates_through_expression():
    _, issues = run("int a;\nfloat b = 1.5;\na = b + 1;")
    assert len(warnings_of(issues)) == 1


def test_initializer_cannot_use_the_variable_being_declared():
    _, issues = run("int x = x;")
    assert len(errors_of(issues)) == 1


def test_undeclared_in_condition_inside_while():
    _, issues = run("while (n < 3) {\n}")
    assert len(errors_of(issues)) == 1