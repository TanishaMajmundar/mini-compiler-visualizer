import pytest

from compiler.errors import CompileError
from compiler.lexer import tokenize
from compiler.parser import parse


def tree(source: str):
    tokens, _ = tokenize(source)
    return parse(tokens)


def syntax_error(source: str) -> CompileError:
    with pytest.raises(CompileError) as info:
        tree(source)
    return info.value


def test_declaration_with_initializer():
    decl = tree("int x = 5;").children[0]
    assert decl.kind == "Decl" and decl.label == "int"
    assert [c.kind for c in decl.children] == ["Id", "Num"]


def test_declaration_without_initializer():
    decl = tree("float y;").children[0]
    assert decl.label == "float" and len(decl.children) == 1


def test_if_without_else():
    node = tree("if (a < b) { a = 1; }").children[0]
    assert node.kind == "If"
    assert [c.kind for c in node.children] == ["Cond", "Block"]
    assert node.children[0].label == "<"


def test_if_with_else():
    node = tree("if (a == b) { a = 1; } else { a = 2; }").children[0]
    assert [c.kind for c in node.children] == ["Cond", "Block", "Block"]


def test_while_loop():
    node = tree("while (i != 0) { i = i - 1; }").children[0]
    assert node.kind == "While"
    assert [c.kind for c in node.children] == ["Cond", "Block"]


def test_nested_blocks():
    outer = tree("{ { x = 1; } }").children[0]
    assert outer.kind == "Block" and outer.children[0].kind == "Block"


def test_condition_needs_relational_operator():
    error = syntax_error("if (x) { }")
    assert "relational operator" in error.message


def test_missing_closing_brace():
    error = syntax_error("while (a < b) { a = 1;")
    assert "'}'" in error.message and "end of file" in error.message


def test_missing_semicolon_after_declaration_reports_previous_line():
    error = syntax_error("int x = 5\nint y = 2;")
    assert error.line == 1
    assert str(error) == "Syntax error: expected ';' but found 'int' (line 1)"


def test_if_body_must_be_a_block():
    error = syntax_error("if (a < b) a = 1;")
    assert "'{'" in error.message


def test_stray_else():
    error = syntax_error("else { }")
    assert "a statement" in error.message