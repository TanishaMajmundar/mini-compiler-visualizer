from compiler.pipeline import compile_source


def test_valid_program_runs_all_phases():
    result = compile_source("int a = 2;\nint x = a + 3 * 4;")
    assert result.ok and result.failed_phase is None
    assert [str(i) for i in result.tac] == ["a = 2", "t1 = 3 * 4", "t2 = a + t1", "x = t2"]
    assert len(result.symbols) == 2
    assert len(result.triples) == len(result.tac)


def test_lexical_error_stops_early_but_keeps_tokens():
    result = compile_source("int x = 5 $ 2;")
    assert result.failed_phase == "Lexical"
    assert result.tokens and result.tree is None
    assert str(result.errors[0]) == "Lexical error: invalid character '$' (line 1)"


def test_syntax_error_keeps_tokens_but_no_tree():
    result = compile_source("int x = 5\nint y = 1;")
    assert result.failed_phase == "Syntax"
    assert result.tokens and result.tree is None
    assert result.errors[0].line == 1


def test_semantic_error_keeps_tree_and_symbols_but_no_tac():
    result = compile_source("int x = 10;\ny = x + 1;")
    assert result.failed_phase == "Semantic"
    assert result.tree is not None and len(result.symbols) == 1
    assert result.tac == []
    assert str(result.errors[0]) == "Semantic error: 'y' used before declaration (line 2)"


def test_warning_does_not_stop_compilation():
    result = compile_source("float p = 9.5;\nint t = p * 2;")
    assert result.ok
    assert len(result.warnings) == 1 and result.tac