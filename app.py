"""Streamlit UI for the Mini Compiler.

Run with:  streamlit run app.py

This file only draws the interface. All compiler work happens in compiler/.
"""

from pathlib import Path

import streamlit as st

from compiler.pipeline import CompileResult, compile_source
from compiler.visualize import tree_to_dot, tree_to_text

EXAMPLES_DIR = Path(__file__).parent / "examples"

st.set_page_config(page_title="Mini Compiler", page_icon="🛠️", layout="wide")


def load_samples() -> dict[str, str]:
    """Read every examples/*.txt file: {display name: code}."""
    samples = {}
    for path in sorted(EXAMPLES_DIR.glob("*.txt")):
        name = path.stem.split("_", 1)[-1].replace("_", " ").title()
        samples[name] = path.read_text(encoding="utf-8")
    return samples


def show_errors(result: CompileResult) -> None:
    """Show each error with the offending source line."""
    lines = result.source.splitlines()
    for error in result.errors:
        st.error(str(error))
        if 1 <= error.line <= len(lines):
            st.code(f"{error.line} | {lines[error.line - 1]}", language=None)


def show_not_available(phase: str) -> None:
    st.info(f"Not available: the {phase} phase did not finish.")


def show_results(result: CompileResult) -> None:
    """Draw errors (if any) and one tab per phase."""
    if result.errors:
        show_errors(result)
    else:
        st.success("Compilation successful.")

    tab_tokens, tab_tree, tab_tac, tab_quads, tab_triples = st.tabs(
        ["Tokens", "Parse Tree", "TAC", "Quadruples", "Triples"]
    )

    with tab_tokens:
        rows = [
            {"Lexeme": t.lexeme, "Token Type": t.type, "Line": t.line}
            for t in result.tokens
            if t.type != "EOF"
        ]
        if rows:
            st.dataframe(rows, hide_index=True)
        else:
            st.info("No tokens (empty program).")

    with tab_tree:
        if result.tree is None:
            show_not_available("parsing")
        else:
            st.graphviz_chart(tree_to_dot(result.tree))
            with st.expander("Text view"):
                st.code(tree_to_text(result.tree), language=None)

    with tab_tac:
        if result.tree is None:
            show_not_available("parsing")
        else:
            st.code("\n".join(str(i) for i in result.tac) or "(empty)", language=None)

    with tab_quads:
        if result.tree is None:
            show_not_available("parsing")
        else:
            rows = [
                {
                    "#": i,
                    "op": ins.op,
                    "arg1": ins.arg1,
                    "arg2": ins.arg2 or "",
                    "result": ins.result,
                }
                for i, ins in enumerate(result.tac)
            ]
            st.dataframe(rows, hide_index=True)

    with tab_triples:
        if result.tree is None:
            show_not_available("parsing")
        else:
            rows = [
                {"#": t.index, "op": t.op, "arg1": t.arg1, "arg2": t.arg2 or ""}
                for t in result.triples
            ]
            st.dataframe(rows, hide_index=True)


# ----------------------------- page layout -------------------------------

st.title("End-to-End Mini Compiler with Compiler Phase Visualization")
st.caption("Source → Lexer → Parser → TAC → Quadruples / Triples")

samples = load_samples()
choice = st.selectbox("Sample program", list(samples.keys()))

# The key includes the sample name, so picking a new sample resets the editor.
code = st.text_area("Source code", value=samples[choice], height=220, key=f"editor_{choice}")

if st.button("Compile", type="primary"):
    st.session_state["result"] = compile_source(code)

if "result" in st.session_state:
    show_results(st.session_state["result"])
