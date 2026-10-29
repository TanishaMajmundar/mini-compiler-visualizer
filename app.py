"""Streamlit UI for the Mini Compiler.

Run with:  streamlit run app.py

This file only draws the interface. All compiler work happens in compiler/.
Edit the PROJECT INFO block below to change the names shown on the page.

Design idea: every compiler phase has its own colour. The same colour is used
in the five stage boxes and on the matching result tab, so the page itself
shows which phase produced what.
"""

from html import escape
from pathlib import Path

import streamlit as st

from compiler.optimizer import side_by_side
from compiler.parser import Node
from compiler.pipeline import CompileResult, compile_source
from compiler.visualize import tree_to_dot, tree_to_text

# ======================= PROJECT INFO (edit these) ==========================
COURSE = "Compiler Design"
PROGRAM = "B.Tech CSE-AIML, Semester VII"
UNIVERSITY = "UnitedWorld Institute of Technology, Karnavati University"
GUIDE_NAME = "Ms Neha Minocha"
GUIDE_TITLE = "Assistant Professor"
TEAM = [
    # name, enrollment number, what this person built
    ("Tanisha Majmundar", "Enrollment No.: 202307020117", "Team lead: architecture, lexer, parser, semantic analysis, code generation"),
    ("Abhi Tiwari", "Enrollment No.: 202307020120", "User interface, screenshots and documentation"),
    ("Vanshika Mehta", "Enrollment No.: 202307020122", "Optimizer, tests and sample programs"),
]
# ===========================================================================

EXAMPLES_DIR = Path(__file__).parent / "examples"

st.set_page_config(
    page_title="Mini Compiler",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&family=Source+Sans+3:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  color-scheme: light;
  --ink: #2E2420;
  --muted: #75685F;
  --page: #F8F4EE;
  --panel: #FFFFFF;
  --line: #D3C2B1;
  --band: #3A2A22;
  --band-text: #F6ECE0;
  --band-muted: #CDB9A5;
  --mocha: #7A4E32;
  --mocha-dark: #5E3B25;
  --idle: #EEE7DD;
  --err: #9B2C20;
  --err-bg: #F6DAD3;
  --warn: #7A5A1C;
  --warn-bg: #F3E5C2;
  /* one colour pair (soft fill, strong text) per phase */
  --lex-bg: #DCE6EC;  --lex: #33566B;
  --syn-bg: #DFE8D6;  --syn: #43603A;
  --sem-bg: #F0E2C3;  --sem: #7A5A1C;
  --gen-bg: #E6D9E3;  --gen: #6B466A;
  --opt-bg: #F0D8D0;  --opt: #8C4B3A;
}

html, body, .stApp, [class*="css"] { font-family: 'Source Sans 3', system-ui, sans-serif; color: var(--ink); }
html { font-size: 87.5%; }
.stApp { background: var(--page); }
.stApp p, .stApp label, .stApp li { font-size: 1.08rem; }
header[data-testid="stHeader"] { display: none; }
#MainMenu, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; visibility: hidden; }
[data-testid="stMain"], section.main, .stApp { overflow-x: hidden; }
.block-container { padding-top: 0; padding-bottom: 4rem; max-width: 1260px; }

/* ---------- hero band: letterhead + title on deep espresso ---------- */
.hero {
  background: var(--band); box-shadow: 0 0 0 100vmax var(--band); clip-path: inset(0 -100vmax);
  margin-bottom: 2.4rem;
}
.letterhead {
  display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
  padding: 1.2rem 0 1rem 0; border-bottom: 1px solid rgba(246,236,224,0.22);
  font-size: 1rem; color: var(--band-muted);
}
.letterhead b { color: var(--band-text); font-weight: 600; }
.masthead { padding: 1.6rem 0 2rem 0; }
.masthead h1 {
  font-family: 'Source Serif 4', Georgia, serif; font-weight: 600;
  font-size: clamp(1.4rem, 2.7vw, 2.5rem); line-height: 1.15; white-space: nowrap;
  letter-spacing: -0.015em; margin: 0 0 0.7rem 0; padding: 0; color: var(--band-text);
}
.masthead p.sub { color: var(--band-muted); font-size: 1.28rem; line-height: 1.55; max-width: 44rem; margin: 0; }

/* ---------- editor ---------- */
.stSelectbox label p, .stTextArea label p { font-weight: 600; color: var(--ink); font-size: 1.1rem; }
div[data-baseweb="select"] > div {
  background: var(--panel); border: 1px solid #C4B09C; border-radius: 6px; min-height: 3.1rem;
}
div[data-baseweb="select"] *, div[data-baseweb="popover"] li, div[data-baseweb="popover"] li * { font-size: 1.1rem !important; }
.stTextArea textarea {
  font-family: 'JetBrains Mono', monospace !important; font-size: 1.02rem !important; line-height: 1.7 !important;
  background: var(--panel) !important; color: var(--ink) !important;
  border: 1px solid #C4B09C !important; border-radius: 6px !important; padding: 1.1rem 1.2rem !important;
}
.stTextArea textarea:focus { border-color: var(--mocha) !important; box-shadow: 0 0 0 2px #E6D6C8 !important; }
.stButton > button {
  background: var(--mocha); color: #FBF8F4; border: 0; border-radius: 6px;
  padding: 0.7rem 2.6rem; font-weight: 600; font-size: 1.12rem; font-family: 'Source Sans 3', sans-serif;
}
.stButton > button:hover { background: var(--mocha-dark); color: #fff; }
.stButton > button:focus-visible { outline: 3px solid #E6D6C8; outline-offset: 2px; }

/* ---------- guide and team (a ruled title block) ---------- */
.about { background: var(--panel); border: 1px solid #C4B09C; border-radius: 6px; }
.about .row { padding: 1rem 1.4rem; border-bottom: 1px solid var(--line); }
.about .row:last-child { border-bottom: 0; }
.about .label { color: var(--muted); font-size: 0.98rem; margin-bottom: 0.15rem; }
.about .guide { font-family: 'Source Serif 4', serif; font-size: 1.3rem; font-weight: 600; line-height: 1.3; }
.about .guide span { font-family: 'Source Sans 3', sans-serif; font-size: 1.02rem; font-weight: 400; color: var(--muted); }
.member { padding: 0.85rem 1.4rem; border-bottom: 1px solid var(--line); }
.member:last-child { border-bottom: 0; }
.member .nm { font-weight: 700; font-size: 1.15rem; line-height: 1.3; }
.member .nm i { font-style: normal; font-weight: 600; font-size: 0.85rem; margin-left: 0.55rem; padding: 0.1rem 0.55rem;
  border-radius: 4px; background: var(--mocha); color: var(--panel); vertical-align: 2px; }
.member .en { font-family: 'JetBrains Mono', monospace; font-size: 0.92rem; color: var(--muted); margin-top: 0.1rem; }
.member .rl { font-size: 1.02rem; color: var(--muted); line-height: 1.45; margin-top: 0.2rem; }

/* ---------- pipeline: five numbered stages ---------- */
.stages-title { font-family: 'Source Serif 4', serif; font-weight: 600; font-size: 1.6rem; margin: 2.6rem 0 1rem 0; }
.stages { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.8rem; }
.st { background: var(--panel); border: 1px solid #C4B09C; border-top: 5px solid #C4B09C; border-radius: 6px; padding: 0.9rem 1.1rem 1.1rem 1.1rem; }
.st .no { font-family: 'Source Serif 4', serif; font-size: 1.9rem; font-weight: 600; line-height: 1; color: #B9AB9B; }
.st .nm { font-weight: 700; font-size: 1.12rem; line-height: 1.25; margin-top: 0.55rem; }
.st .nt { font-size: 1rem; line-height: 1.4; margin-top: 0.25rem; color: var(--muted); }
.st.on.p-lex { background: var(--lex-bg); border-top-color: var(--lex); } .st.on.p-lex .no, .st.on.p-lex .nm { color: var(--lex); }
.st.on.p-syn { background: var(--syn-bg); border-top-color: var(--syn); } .st.on.p-syn .no, .st.on.p-syn .nm { color: var(--syn); }
.st.on.p-sem { background: var(--sem-bg); border-top-color: var(--sem); } .st.on.p-sem .no, .st.on.p-sem .nm { color: var(--sem); }
.st.on.p-gen { background: var(--gen-bg); border-top-color: var(--gen); } .st.on.p-gen .no, .st.on.p-gen .nm { color: var(--gen); }
.st.on.p-opt { background: var(--opt-bg); border-top-color: var(--opt); } .st.on.p-opt .no, .st.on.p-opt .nm { color: var(--opt); }
.st.on .nt { color: var(--ink); }
.st.fail { background: var(--err-bg); border-top-color: var(--err); }
.st.fail .no, .st.fail .nm, .st.fail .nt { color: var(--err); }
.st.fail .nt { font-weight: 700; }
.st.skip { background: var(--idle); border-top-color: var(--line); }
.st.skip .no, .st.skip .nm, .st.skip .nt { color: #A89B8D; }

/* ---------- messages ---------- */
.banner { border-radius: 6px; padding: 0.9rem 1.3rem; margin: 1.6rem 0 1rem 0; font-weight: 600; font-size: 1.12rem; background: var(--syn-bg); color: var(--syn); border: 1px solid #C5D4B8; }
.hint { color: var(--muted); padding: 1.4rem 0 0 0; font-size: 1.15rem; }
.issue { border-radius: 6px; margin: 1.3rem 0 0.8rem 0; overflow: hidden; background: var(--panel); border: 1px solid; }
.issue.error { border-color: #E3B4A9; }
.issue.warning { border-color: #E2CC8E; }
.issue .msg { padding: 0.8rem 1.2rem; font-weight: 700; font-size: 1.1rem; }
.issue.error .msg { background: var(--err-bg); color: var(--err); }
.issue.warning .msg { background: var(--warn-bg); color: var(--warn); }
.excerpt { font-family: 'JetBrains Mono', monospace; font-size: 0.98rem; padding: 0.5rem 0; }
.excerpt .ln { display: flex; white-space: pre; padding: 0.15rem 1.2rem; color: var(--muted); }
.excerpt .ln .no { flex: 0 0 2.6rem; text-align: right; padding-right: 1.1rem; user-select: none; }
.excerpt .ln.hit { background: var(--err-bg); color: var(--ink); font-weight: 500; }
.issue.warning .excerpt .ln.hit { background: var(--warn-bg); }

/* ---------- tabs: underline in the phase colour ---------- */
.stTabs { margin-top: 1.8rem; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-list"] { gap: 1.7rem; flex-wrap: wrap; border-bottom: 1px solid var(--line); }
.stTabs button[data-baseweb="tab"] {
  height: auto; padding: 0.7rem 0.1rem; background: transparent !important; border-radius: 0 !important;
  border: 0 solid transparent !important; border-bottom: 4px solid transparent !important;
  outline: none !important; box-shadow: none !important; margin-bottom: -1px;
}
.stTabs button[data-baseweb="tab"] p { font-weight: 600; font-size: 1.12rem; color: var(--muted) !important; }
.stTabs button[data-baseweb="tab"]:hover p { color: var(--ink) !important; }
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(1) { border-bottom-color: var(--lex) !important; }
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(1) p { color: var(--lex) !important; }
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(2) { border-bottom-color: var(--syn) !important; }
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(2) p { color: var(--syn) !important; }
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(3) { border-bottom-color: var(--sem) !important; }
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(3) p { color: var(--sem) !important; }
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(4),
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(5),
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(6) { border-bottom-color: var(--gen) !important; }
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(4) p,
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(5) p,
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(6) p { color: var(--gen) !important; }
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(7) { border-bottom-color: var(--opt) !important; }
.stTabs button[data-baseweb="tab"][aria-selected="true"]:nth-of-type(7) p { color: var(--opt) !important; }
[data-testid="stCode"] pre, [data-testid="stCode"] code { font-family: 'JetBrains Mono', monospace !important; font-size: 1rem !important; }

/* ---------- tables (drawn as HTML so the colours are ours) ---------- */
.tbl-wrap { background: var(--panel); border: 1px solid #C4B09C; border-radius: 6px; overflow: auto; max-height: 28rem; margin-top: 0.8rem; }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th { position: sticky; top: 0; text-align: left; padding: 0.8rem 1.1rem; font-weight: 700; font-size: 1.02rem; border-bottom: 2px solid #C4B09C; }
.tbl td { padding: 0.62rem 1.1rem; border-bottom: 1px solid #E8DDD1; font-family: 'JetBrains Mono', monospace; font-size: 0.98rem; color: var(--ink); }
.tbl tbody tr:nth-child(even) td { background: #FAF6F0; }
.tbl tbody tr:hover td { background: #F1E7DB; }
.tbl th.num, .tbl td.num { text-align: right; }
.tbl.p-lex th { background: var(--lex-bg); color: var(--lex); }
.tbl.p-syn th { background: var(--syn-bg); color: var(--syn); }
.tbl.p-sem th { background: var(--sem-bg); color: var(--sem); }
.tbl.p-gen th { background: var(--gen-bg); color: var(--gen); }
.tbl.p-opt th { background: var(--opt-bg); color: var(--opt); }

@media (max-width: 900px) {
  .masthead h1 { font-size: 1.7rem; white-space: normal; }
  .masthead { padding: 1.6rem 0 2rem 0; }
  .stages { grid-template-columns: 1fr; }
}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# ----------------------------- helpers -----------------------------------

def load_samples() -> dict[str, str]:
    """Read every examples/*.txt file: {display name: code}."""
    samples = {}
    for path in sorted(EXAMPLES_DIR.glob("*.txt")):
        name = path.stem.split("_", 1)[-1].replace("_", " ").title()
        samples[name] = path.read_text(encoding="utf-8")
    return samples


def count_nodes(node: Node) -> int:
    """Number of nodes in the tree."""
    return 1 + sum(count_nodes(child) for child in node.children)


def plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def show_table(rows: list[dict], phase: str) -> None:
    """Draw a table as HTML so we control its colours (the built-in table cannot be styled)."""
    if not rows:
        return
    nums = {k for k, v in rows[0].items() if isinstance(v, int)}
    head = "".join(
        f'<th class="{"num" if k in nums else ""}">{escape(str(k))}</th>' for k in rows[0]
    )
    body = ""
    for row in rows:
        cells = ""
        for k, v in row.items():
            text = escape(str(v)).replace("$", "&#36;")
            cells += f'<td class="{"num" if k in nums else ""}">{text}</td>'
        body += f"<tr>{cells}</tr>"
    st.markdown(
        f'<div class="tbl-wrap"><table class="tbl p-{phase}"><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )


# ----------------------------- team card ---------------------------------

def show_about() -> None:
    """Guide and team details, laid out like a ruled title block."""
    members = []
    for i, (name, enrollment, role) in enumerate(TEAM):
        tag = ""
        members.append(
            f'<div class="member"><div class="nm">{escape(name)}{tag}</div>'
            f'<div class="en">{escape(enrollment)}</div><div class="rl">{escape(role)}</div></div>'
        )
    st.markdown(
        f"""
        <div class="about">
          <div class="row"><div class="label">Guided by</div>
            <div class="guide">{escape(GUIDE_NAME)} <span>{escape(GUIDE_TITLE)}</span></div></div>
          <div class="row" style="padding-bottom:0.2rem"><div class="label">Project team</div></div>
          {''.join(members)}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------- pipeline ribbon ---------------------------

STAGES = [
    ("Lexical", "lex", "Lexical analysis"),
    ("Syntax", "syn", "Syntax analysis"),
    ("Semantic", "sem", "Semantic analysis"),
    ("Codegen", "gen", "Code generation"),
    ("Optimizer", "opt", "Optimization"),
]


def stage_info(result: CompileResult | None) -> list[tuple[str, str, str, str]]:
    """Return (phase code, state, name, note) for each phase.

    state is "idle" (not compiled yet), "on" (finished), "fail" or "skip".
    """
    if result is None:
        return [(code, "idle", name, "Ready") for _, code, name in STAGES]

    order = [key for key, _, _ in STAGES]
    failed = result.failed_phase
    failed_at = order.index(failed) if failed in order else None

    notes = {}
    tokens = [t for t in result.tokens if t.type != "EOF"]
    notes["Lexical"] = plural(len(tokens), "token")
    if result.tree is not None:
        notes["Syntax"] = plural(count_nodes(result.tree), "tree node")
    semantic = plural(len(result.symbols), "symbol")
    if result.warnings:
        semantic += f", {plural(len(result.warnings), 'warning')}"
    notes["Semantic"] = semantic
    notes["Codegen"] = plural(len(result.tac), "instruction")
    notes["Optimizer"] = (
        f"{len(result.tac)} to {len(result.optimized)} instructions, "
        f"{plural(len(result.changes), 'change')}"
    )

    rows = []
    for i, (key, code, name) in enumerate(STAGES):
        if failed_at is not None and i > failed_at:
            rows.append((code, "skip", name, "Not reached"))
        elif failed_at is not None and i == failed_at:
            rows.append((code, "fail", name, plural(len(result.errors), "error")))
        else:
            rows.append((code, "on", name, notes[key]))
    return rows


def show_pipeline(result: CompileResult | None) -> None:
    boxes = "".join(
        f'<div class="st p-{code} {state}"><div class="no">{i}</div><div class="nm">{escape(name)}</div>'
        f'<div class="nt">{escape(note)}</div></div>'
        for i, (code, state, name, note) in enumerate(stage_info(result), start=1)
    )
    st.markdown(
        f'<div class="stages-title">How far the program got</div><div class="stages">{boxes}</div>',
        unsafe_allow_html=True,
    )


# ----------------------------- issues ------------------------------------

def show_issues(result: CompileResult) -> None:
    """Each error or warning with the source lines around the problem."""
    lines = result.source.splitlines()
    for issue in result.errors + result.warnings:
        rows = ""
        if 1 <= issue.line <= len(lines):
            first = max(1, issue.line - 1)
            last = min(len(lines), issue.line + 1)
            for no in range(first, last + 1):
                hit = " hit" if no == issue.line else ""
                text = escape(lines[no - 1]) or " "
                rows += f'<div class="ln{hit}"><span class="no">{no}</span><span>{text}</span></div>'
        st.markdown(
            f'<div class="issue {issue.severity}"><div class="msg">{escape(str(issue))}</div>'
            f'<div class="excerpt">{rows}</div></div>',
            unsafe_allow_html=True,
        )


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
        f"{len(result.tac)} instructions became {len(result.optimized)} "
        f"({plural(len(result.changes), 'change')}). "
        "A line starting with '-' was changed or removed; '+' is its new version."
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
    show_table(log_rows, "opt")


def show_tabs(result: CompileResult) -> None:
    """One tab per phase. Tab order matters: the CSS colours tabs by position."""
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
            show_table(rows, "lex")
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
            show_table(rows, "sem")

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
                {"#": i, "op": ins.op, "arg1": ins.arg1, "arg2": ins.arg2 or "", "result": ins.result}
                for i, ins in enumerate(result.tac)
            ]
            show_table(rows, "gen")

    with tab_triples:
        if not codegen_done:
            show_not_available("code generation")
        else:
            rows = [
                {"#": t.index, "op": t.op, "arg1": t.arg1, "arg2": t.arg2 or ""}
                for t in result.triples
            ]
            show_table(rows, "gen")

    with tab_opt:
        if not codegen_done:
            show_not_available("code generation")
        else:
            show_optimization(result)


# ----------------------------- page layout -------------------------------

st.markdown(
    f"""
    <div class="hero">
      <div class="letterhead"><span><b>{escape(UNIVERSITY)}</b></span>
        <span>{escape(COURSE)} mini project, {escape(PROGRAM)}</span></div>
      <div class="masthead">
        <h1>End-to-End Mini Compiler with Compiler Phase Visualization</h1>
        <p class="sub">Write a small C-like program and compile it. Each phase shows its own result,
        and if something fails you can see exactly where it stopped.</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

samples = load_samples()
result: CompileResult | None = st.session_state.get("result")

editor_col, about_col = st.columns([3, 2], gap="large")

with editor_col:
    choice = st.selectbox("Sample program", list(samples.keys()))
    # The key includes the sample name, so picking a new sample resets the editor.
    code = st.text_area("Source code", value=samples[choice], height=300, key=f"editor_{choice}")
    if st.button("Compile", type="primary"):
        result = compile_source(code)
        st.session_state["result"] = result

with about_col:
    show_about()

show_pipeline(result)

if result is None:
    st.markdown(
        '<div class="hint">Pick a sample or type your own program, then press Compile.</div>',
        unsafe_allow_html=True,
    )
else:
    if result.ok:
        note = f" with {plural(len(result.warnings), 'warning')}" if result.warnings else ""
        st.markdown(f'<div class="banner">Compiled successfully{note}.</div>', unsafe_allow_html=True)
    show_issues(result)
    show_tabs(result)