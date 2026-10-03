import pytest

from compiler.errors import CompileError
from compiler.lexer import tokenize
from compiler.parser import Node, parse


def parse_src(source):
    tokens, errors = tokenize(source)
    assert errors == []
    return parse(tokens)


def sexpr(node: Node) -> str:
    """Compact text form of a tree, e.g. (+ a (* b c))"""
    if not node.children:
        return node.label
    return "(" + node.label + " " + " ".join(sexpr(c) for c in node.children) + ")"


def test_empty_program():
    assert parse_src("").children == []


def test_precedence_mul_before_add():
    tree = parse_src("x = 1 + 2 * 3;")
    assert sexpr(tree.children[0]) == "(= x (+ 1 (* 2 3)))"


def test_left_associativity():
    tree = parse_src("x = 8 - 3 - 2;")
    assert sexpr(tree.children[0]) == "(= x (- (- 8 3) 2))"


def test_parentheses_override_precedence():
    tree = parse_src("x = (1 + 2) * 3;")
    assert sexpr(tree.children[0]) == "(= x (* (+ 1 2) 3))"


def test_multiple_statements():
    tree = parse_src("a = 1;\nb = a;")
    assert len(tree.children) == 2


def fails_with(source):
    with pytest.raises(CompileError) as info:
        parse_src(source)
    return info.value


def test_missing_closing_paren():
    err = fails_with("x = (1 + 2;")
    assert str(err) == "Syntax error: expected ')' but found ';' (line 1)"


def test_missing_semicolon_reports_previous_line():
    err = fails_with("x = 5\ny = 6;")
    assert str(err) == "Syntax error: expected ';' but found 'y' (line 1)"


def test_missing_semicolon_at_end_of_file():
    err = fails_with("x = 5")
    assert str(err) == "Syntax error: expected ';' but found end of file (line 1)"


def test_missing_operand():
    err = fails_with("x = * 3;")
    assert err.message == "expected identifier, number or '(' but found '*'"


def test_statement_must_start_with_identifier():
    err = fails_with("= 5;")
    assert err.message == "expected identifier but found '='"
