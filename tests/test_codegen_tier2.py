from compiler.codegen import Triple, generate, to_triples
from compiler.lexer import tokenize
from compiler.parser import parse


def tac(source: str) -> list[str]:
    tokens, _ = tokenize(source)
    return [str(i) for i in generate(parse(tokens))]


def test_declaration_with_initializer():
    assert tac("int x = 2 + 3;") == ["t1 = 2 + 3", "x = t1"]


def test_declaration_without_initializer_makes_no_code():
    assert tac("int x;") == []


def test_if_without_else():
    assert tac("int x = 1;\nif (x < 2) { x = 5; }") == [
        "x = 1",
        "t1 = x < 2",
        "ifFalse t1 goto L1",
        "x = 5",
        "L1:",
    ]


def test_if_else():
    assert tac("int x = 1;\nif (x > 0) { x = 2; } else { x = 3; }") == [
        "x = 1",
        "t1 = x > 0",
        "ifFalse t1 goto L1",
        "x = 2",
        "goto L2",
        "L1:",
        "x = 3",
        "L2:",
    ]


def test_while_loop():
    assert tac("int i = 0;\nwhile (i < 3) { i = i + 1; }") == [
        "i = 0",
        "L1:",
        "t1 = i < 3",
        "ifFalse t1 goto L2",
        "t2 = i + 1",
        "i = t2",
        "goto L1",
        "L2:",
    ]


def test_nested_if_inside_while_uses_distinct_labels():
    code = tac("int i = 0;\nwhile (i < 3) {\n if (i == 1) { i = 5; }\n i = i + 1;\n}")
    labels = [line for line in code if line.endswith(":")]
    assert len(labels) == len(set(labels)) == 3


def test_triples_for_while_loop():
    tokens, _ = tokenize("int i = 0;\nwhile (i < 3) { i = i + 1; }")
    triples = to_triples(generate(parse(tokens)))
    assert triples[3] == Triple(3, "ifFalse", "(2)", "L2")
    assert triples[5] == Triple(5, "=", "i", "(4)")
    assert triples[6] == Triple(6, "goto", "L1", None)