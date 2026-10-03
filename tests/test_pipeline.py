from compiler.pipeline import compile_source


def test_successful_compile():
    result = compile_source("a = 1;\nb = a + 2 * 3;")
    assert result.ok
    assert result.failed_phase is None
    assert result.tree is not None
    assert [str(i) for i in result.tac][-1] == "b = t2"
    assert len(result.triples) == len(result.tac)


def test_lexical_error_keeps_tokens_but_stops():
    result = compile_source("x = 5 $ 3;")
    assert result.failed_phase == "Lexical"
    assert result.tokens            # lexer output still available
    assert result.tree is None      # parser never ran
    assert result.tac == []
    assert str(result.errors[0]) == "Lexical error: invalid character '$' (line 1)"


def test_syntax_error_keeps_tokens_but_stops():
    result = compile_source("a = 5;\nb = (a + 3;\n")
    assert result.failed_phase == "Syntax"
    assert result.tokens
    assert result.tree is None
    assert result.tac == []
    assert str(result.errors[0]) == "Syntax error: expected ')' but found ';' (line 2)"
