from compiler.lexer import tokenize


def types_and_lexemes(source):
    tokens, errors = tokenize(source)
    return [(t.type, t.lexeme) for t in tokens], errors


def test_simple_assignment():
    toks, errors = types_and_lexemes("x = 5;")
    assert errors == []
    assert toks == [
        ("ID", "x"), ("ASSIGN", "="), ("NUM", "5"), ("SEMI", ";"), ("EOF", ""),
    ]


def test_keywords_vs_identifiers():
    toks, _ = types_and_lexemes("int float if else while foo")
    assert [t for t, _ in toks[:5]] == ["KEYWORD"] * 5
    assert toks[5] == ("ID", "foo")


def test_relational_operators():
    toks, _ = types_and_lexemes("<= >= == != < >")
    assert [l for t, l in toks if t == "RELOP"] == ["<=", ">=", "==", "!=", "<", ">"]


def test_arithmetic_and_brackets():
    toks, _ = types_and_lexemes("(a+b)*c/d-e")
    assert [l for _, l in toks[:-1]] == list("(a+b)*c/d-e")


def test_float_number():
    toks, errors = types_and_lexemes("3.14")
    assert errors == []
    assert toks[0] == ("NUM", "3.14")


def test_line_numbers():
    tokens, _ = tokenize("a\nb\n\nc")
    assert [t.line for t in tokens if t.type == "ID"] == [1, 2, 4]


def test_comment_is_ignored():
    toks, _ = types_and_lexemes("x = 1; // this is ignored\ny = 2;")
    assert ("ID", "y") in toks
    assert all("ignored" not in l for _, l in toks)


def test_invalid_character_message_format():
    tokens, errors = tokenize("x = 5 $ 3;")
    assert len(errors) == 1
    assert str(errors[0]) == "Lexical error: invalid character '$' (line 1)"
    # the scan continues after the error
    assert [t.lexeme for t in tokens if t.type == "NUM"] == ["5", "3"]


def test_multiple_lexical_errors_reported():
    _, errors = tokenize("x = 5 $ 3;\ny = a # b;")
    assert [(e.message, e.line) for e in errors] == [
        ("invalid character '$'", 1),
        ("invalid character '#'", 2),
    ]


def test_malformed_number():
    _, errors = tokenize("x = 3.;")
    assert len(errors) == 1
    assert errors[0].message == "malformed number '3.'"
