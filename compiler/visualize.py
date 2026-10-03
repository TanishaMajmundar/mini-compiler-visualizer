"""Turn the tree into things we can show: a text view and a Graphviz DOT string.

st.graphviz_chart() accepts a DOT string directly, so the user does not need
to install Graphviz on their computer.
"""

from compiler.parser import Node

# Fill colour for each kind of node in the drawing.
COLORS = {
    "Program": "#E8EAF6",
    "Assign": "#FFE0B2",
    "BinOp": "#C8E6C9",
    "Id": "#BBDEFB",
    "Num": "#FFF9C4",
}


def _describe(node: Node) -> str:
    """Text for one node in the text view, e.g. BinOp(+)."""
    if node.kind == "Program":
        return "Program"
    return f"{node.kind}({node.label})"


def tree_to_text(root: Node) -> str:
    """Indented text drawing of the tree, like the `tree` command."""
    lines = [_describe(root)]

    def walk(node: Node, prefix: str) -> None:
        for i, child in enumerate(node.children):
            is_last = i == len(node.children) - 1
            lines.append(prefix + ("└── " if is_last else "├── ") + _describe(child))
            walk(child, prefix + ("    " if is_last else "│   "))

    walk(root, "")
    return "\n".join(lines)


def _escape(text: str) -> str:
    """Make text safe inside a DOT double-quoted label."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def tree_to_dot(root: Node) -> str:
    """Return a Graphviz DOT description of the tree."""
    lines = [
        "digraph AST {",
        "  rankdir=TB;",
        '  node [fontname="Helvetica", shape=box, style="rounded,filled"];',
    ]
    counter = [0]  # list so the inner function can change it

    def walk(node: Node) -> str:
        node_id = f"n{counter[0]}"
        counter[0] += 1
        color = COLORS.get(node.kind, "white")
        lines.append(f'  {node_id} [label="{_escape(node.label)}", fillcolor="{color}"];')
        for child in node.children:
            child_id = walk(child)
            lines.append(f"  {node_id} -> {child_id};")
        return node_id

    walk(root)
    lines.append("}")
    return "\n".join(lines)
