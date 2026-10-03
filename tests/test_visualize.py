from compiler.lexer import tokenize
from compiler.parser import parse
from compiler.visualize import tree_to_dot, tree_to_text


def tree_of(source):
    tokens, _ = tokenize(source)
    return parse(tokens)


def test_text_view():
    assert tree_to_text(tree_of("x = 1;")) == "\n".join([
        "Program",
        "└── Assign(=)",
        "    ├── Id(x)",
        "    └── Num(1)",
    ])


def test_dot_output_has_nodes_and_edges():
    dot = tree_to_dot(tree_of("x = a + 1;"))
    assert dot.startswith("digraph AST {")
    assert dot.rstrip().endswith("}")
    assert 'label="+"' in dot
    assert "n0 -> n1;" in dot
