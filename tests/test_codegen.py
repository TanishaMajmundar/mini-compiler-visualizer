from compiler.codegen import generate, to_triples
from compiler.lexer import tokenize
from compiler.parser import parse


def tac_lines(source):
    tokens, _ = tokenize(source)
    return [str(i) for i in generate(parse(tokens))]


def triples_of(source):
    tokens, _ = tokenize(source)
    return [(t.op, t.arg1, t.arg2) for t in to_triples(generate(parse(tokens)))]


def test_simple_copy():
    assert tac_lines("x = 5;") == ["x = 5"]


def test_precedence_in_tac():
    assert tac_lines("x = a + b * c;") == ["t1 = b * c", "t2 = a + t1", "x = t2"]


def test_parentheses_in_tac():
    assert tac_lines("x = (a + b) * c;") == ["t1 = a + b", "t2 = t1 * c", "x = t2"]


def test_temp_counter_continues_across_statements():
    assert tac_lines("a = b + c; d = e * f;") == [
        "t1 = b + c", "a = t1", "t2 = e * f", "d = t2",
    ]


def test_temp_name_does_not_clash_with_user_variable():
    assert tac_lines("t1 = a + b;") == ["t2 = a + b", "t1 = t2"]


def test_quadruple_fields():
    tokens, _ = tokenize("x = a + b;")
    quad = generate(parse(tokens))[0]
    assert (quad.op, quad.arg1, quad.arg2, quad.result) == ("+", "a", "b", "t1")


def test_triples_use_index_references():
    assert triples_of("x = a + b * c;") == [
        ("*", "b", "c"),
        ("+", "a", "(0)"),
        ("=", "x", "(1)"),
    ]
