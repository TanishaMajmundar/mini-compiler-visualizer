"""Streamlit UI for the Mini Compiler.

Run with:  streamlit run app.py

This file only draws the interface. All compiler work happens in compiler/.
"""

from pathlib import Path

import streamlit as st

from compiler.optimizer import side_by_side
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


def show_issues(result: CompileResult) -> None:
    """Show each error (red) and warning (yellow) with the offending source line."""
    lines = result.source.splitlines()
    for issue in result.errors + result.warnings:
        if issue.severity == "error":
            st.error(str(issue))
        else:
            st.warning(str(issue))
        if 1 <= issue.line <= len(lines):
            st.code(f"{issue.line} | {lines[issue.line - 1]}", language=None)


def show_not_available(phase: str) -> None:
    st.info(f"Not available: the {phase} phase did not finish.")


def show_optimization(result: CompileResult) -> None:
    """Before/after side by side, then the change log."""
    if not result.tac:
        st.info("No code was generated, so there is nothing to optimize.")
        return

    rows = side_by_side(result.tac, result.optimized, result.changes)
    before_lines, after_lines = [], []
    for row in rows:
        if row.status == "removed":
            before_lines.append(f"- {row.before}")
            after_lines.append("  (removed)")
        elif row.status == "changed":
            before_lines.append(f"- {row.before}")
            after_lines.append(f"+ {row.after}")
        else:
            before_lines.append(f"  {row.before}")
            after_lines.append(f"  {row.after}")

    st.caption(
        f"{len(result.tac)} instructions → {len(result.optimized)} instructions "
        f"({len(result.changes)} changes).  "
        "Red '-' = changed or removed line, green '+' = its new version."
    )
    left, right = st.columns(2)
    with left:
        st.markdown("**Before**")
        st.code("\n".join(before_lines), language="diff")
    with right:
        st.markdown("**After**")
        st.code("\n".join(after_lines), language="diff")

    if not result.changes:
        st.info("Nothing to optimize in this program.")
        return

    st.markdown("**Change log**")
    log_rows = [
        {
            "#": c.index,
            "Optimization": c.kind,
            "Before": c.before,
            "After": c.after if c.after is not None else "(removed)",
            "Why": c.note,
        }
        for c in result.changes
    ]
    st.dataframe(log_rows, hide_index=True)


def show_results(result: CompileResult) -> None:
    """Draw errors/warnings (if any) and one tab per phase."""
    if result.ok:
        st.success("Compilation successful.")
    show_issues(result)

    tab_tokens, tab_tree, tab_symbols, tab_tac, tab_quads, tab_triples, tab_opt = st.tabs(
        ["Tokens", "Parse Tree", "Symbol Table", "TAC", "Quadruples", "Triples", "Optimized"]
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

    with tab_symbols:
        if result.tree is None:
            show_not_available("parsing")
        elif not result.symbols:
            st.info("No variables declared.")
        else:
            rows = [
                {"Name": s.name, "Type": s.type, "Scope": s.scope, "Line": s.line}
                for s in result.symbols
            ]
            st.dataframe(rows, hide_index=True)

    # TAC / quadruples / triples / optimized exist only if semantic analysis passed.
    codegen_done = result.ok and result.tree is not None

    with tab_tac:
        if not codegen_done:
            show_not_available("code generation")
        else:
            st.code("\n".join(str(i) for i in result.tac) or "(empty)", language=None)

    with tab_quads:
        if not codegen_done:
            show_not_available("code generation")
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
        if not codegen_done:
            show_not_available("code generation")
        else:
            rows = [
                {"#": t.index, "op": t.op, "arg1": t.arg1, "arg2": t.arg2 or ""}
                for t in result.triples
            ]
            st.dataframe(rows, hide_index=True)

    with tab_opt:
        if not codegen_done:
            show_not_available("code generation")
        else:
            show_optimization(result)


# ----------------------------- page layout -------------------------------

st.title("End-to-End Mini Compiler with Compiler Phase Visualization")
st.caption("Source → Lexer → Parser → Semantic Analyzer → TAC → Optimizer")

samples = load_samples()
choice = st.selectbox("Sample program", list(samples.keys()))

# The key includes the sample name, so picking a new sample resets the editor.
code = st.text_area("Source code", value=samples[choice], height=260, key=f"editor_{choice}")

if st.button("Compile", type="primary"):
    st.session_state["result"] = compile_source(code)

if "result" in st.session_state:
    show_results(st.session_state["result"])