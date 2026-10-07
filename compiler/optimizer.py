"""Phase 5: Optimizer.

Input : list of TACInstruction (from the code generator)
Output: (optimized list of TACInstruction, change_log)

Three optimizations, repeated until nothing changes:

1. Constant propagation: if we know x = 5, replace later uses of x by 5.
       a = 2            a = 2
       t1 = a + 3   ->  t1 = 2 + 3

2. Constant folding: if both operands are numbers, compute the result now.
       t1 = 2 + 3   ->  t1 = 5

3. Dead code elimination: remove instructions whose result is never needed.
       * a temporary (t1, t2, ...) that is never read
       * an assignment that is overwritten before anyone reads it
             x = 5
             x = 10      <- the first line is dead

Safety rules (so we never change what the program means):
  * Known constants are forgotten at every label, because a label can be
    reached by a jump from somewhere we know nothing about (loops, if/else).
  * Variables you declared are treated as "program results": their final
    value is kept. (The language has no print statement, so we cannot prove
    they are unused.) Only temporaries and overwritten assignments are removed.
  * Integer division is folded only when it divides exactly, and division by
    zero is never folded.
Instructions are only changed or removed, never moved or added, so every
instruction can be traced back to its index in the original TAC.
"""

from dataclasses import dataclass, replace

from compiler.codegen import TACInstruction

CONTROL_OPS = ("label", "goto", "ifFalse")
MAX_ROUNDS = 20   # safety limit; real programs settle in 2-3 rounds

COMPARE = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


@dataclass
class Change:
    """One entry of the change log."""

    kind: str            # "Constant propagation", "Constant folding", "Dead code elimination"
    index: int           # position of the instruction in the ORIGINAL TAC (0-based)
    before: str          # the instruction text before this change
    after: str | None    # the text after this change; None means it was removed
    note: str            # short explanation shown in the UI


@dataclass
class DiffRow:
    """One row of the before/after view (one per ORIGINAL instruction)."""

    index: int
    before: str
    after: str           # "" when the instruction was removed
    status: str          # "unchanged", "changed" or "removed"


@dataclass
class _Item:
    """An instruction together with its index in the original TAC."""

    origin: int
    ins: TACInstruction


# ---------------------------------------------------------------- numbers

def parse_number(text: str | None) -> int | float | None:
    """Return the numeric value of text, or None if it is a variable name.

    The first-character check matters: Python's float() accepts words like
    "inf" and "nan", which could also be variable names.
    """
    if not text:
        return None
    body = text[1:] if text[0] == "-" else text
    if not body or not body[0].isdigit():
        return None
    if any(ch not in "0123456789.e+-" for ch in body):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return None


def format_number(value: int | float) -> str:
    """Write a number the way the compiler writes literals."""
    if isinstance(value, int):
        return str(value)
    return repr(round(value, 10))   # 19.0 stays "19.0"; hides 0.30000000000000004


def fold(op: str, left: str, right: str) -> str | None:
    """Compute `left op right` if both are numbers. None means "cannot fold"."""
    a = parse_number(left)
    b = parse_number(right)
    if a is None or b is None:
        return None
    if op in COMPARE:
        return "1" if COMPARE[op](a, b) else "0"   # true = 1, false = 0
    if op == "+":
        value = a + b
    elif op == "-":
        value = a - b
    elif op == "*":
        value = a * b
    elif op == "/":
        if b == 0:
            return None                      # leave division by zero alone
        if isinstance(a, int) and isinstance(b, int):
            if a % b != 0:
                return None                  # 7 / 2: int/float meaning unclear
            value = a // b
        else:
            value = a / b
    else:
        return None
    return format_number(value)


def _reads(ins: TACInstruction) -> list[str]:
    """Names (or numbers) that an instruction reads."""
    if ins.op in ("label", "goto"):
        return []
    names = [ins.arg1]
    if ins.arg2 is not None:
        names.append(ins.arg2)
    return names


# ------------------------------------------------- pass 1: propagate + fold

def _propagate_and_fold(items: list[_Item], log: list[Change]) -> bool:
    """One forward scan doing constant propagation and constant folding.

    `known` maps a name to the constant it currently holds, e.g. {"a": "2"}.
    """
    known: dict[str, str] = {}
    changed = False

    for item in items:
        ins = item.ins

        if ins.op == "label":
            known.clear()        # a jump may arrive here: forget everything
            continue
        if ins.op == "goto":
            continue

        # --- constant propagation: replace known names by their value ---
        new1 = known.get(ins.arg1, ins.arg1)
        new2 = known.get(ins.arg2, ins.arg2) if ins.arg2 is not None else None
        if (new1, new2) != (ins.arg1, ins.arg2):
            before = str(ins)
            pairs = [(old, new) for old, new in ((ins.arg1, new1), (ins.arg2, new2)) if old != new]
            note = ", ".join(f"{old} is known to be {new}" for old, new in pairs)
            ins = replace(ins, arg1=new1, arg2=new2)
            item.ins = ins
            log.append(Change("Constant propagation", item.origin, before, str(ins), note))
            changed = True

        if ins.op == "ifFalse":
            continue

        # --- copy instruction: "x = 5" makes x a known constant ---
        if ins.op == "=":
            if parse_number(ins.arg1) is not None:
                known[ins.result] = ins.arg1
            else:
                known.pop(ins.result, None)
            continue

        # --- binary operation: try to fold ---
        folded = fold(ins.op, ins.arg1, ins.arg2)
        if folded is None:
            known.pop(ins.result, None)
            continue
        before = str(ins)
        note = f"{ins.arg1} {ins.op} {ins.arg2} = {folded}"
        ins = TACInstruction("=", folded, None, ins.result)
        item.ins = ins
        log.append(Change("Constant folding", item.origin, before, str(ins), note))
        known[ins.result] = folded
        changed = True

    return changed


# ------------------------------------------------ pass 2: dead code removal

def _eliminate_dead_code(items: list[_Item], temps: set[str], log: list[Change]) -> bool:
    """Remove useless instructions. Returns True if anything was removed."""
    removed: dict[int, str] = {}   # position in items -> reason

    # Rule 1: a temporary that nobody reads is useless.
    read: set[str] = set()
    for item in items:
        read.update(_reads(item.ins))
    for pos, item in enumerate(items):
        ins = item.ins
        if ins.op not in CONTROL_OPS and ins.result in temps and ins.result not in read:
            removed[pos] = f"temporary '{ins.result}' is never used"

    # Rule 2: an assignment overwritten before it is read is useless.
    # Scan BACKWARDS keeping `overwritten`: names that will be assigned again
    # before anyone reads them. Any jump or label clears it (we cannot know
    # what the other path reads), so this only works inside straight-line code.
    overwritten: set[str] = set()
    for pos in range(len(items) - 1, -1, -1):
        if pos in removed:
            continue
        ins = items[pos].ins
        if ins.op in CONTROL_OPS:
            overwritten.clear()
            continue
        if ins.result in overwritten:
            removed[pos] = f"'{ins.result}' is overwritten before it is read"
            continue
        overwritten.add(ins.result)
        for name in _reads(ins):
            overwritten.discard(name)

    if not removed:
        return False
    for pos, reason in sorted(removed.items()):
        item = items[pos]
        log.append(Change("Dead code elimination", item.origin, str(item.ins), None, reason))
    items[:] = [item for pos, item in enumerate(items) if pos not in removed]
    return True


# ------------------------------------------------------------ public API

def optimize(tac: list[TACInstruction]) -> tuple[list[TACInstruction], list[Change]]:
    """Optimize TAC. The input list is not modified."""
    items = [_Item(i, replace(ins)) for i, ins in enumerate(tac)]

    # Temporaries are exactly the results of binary operations (the code
    # generator creates a temp for nothing else), so even a user variable
    # called "t1" is never mistaken for one.
    temps = {ins.result for ins in tac if ins.op not in CONTROL_OPS and ins.op != "="}

    log: list[Change] = []
    for _ in range(MAX_ROUNDS):
        did_fold = _propagate_and_fold(items, log)
        did_remove = _eliminate_dead_code(items, temps, log)
        if not (did_fold or did_remove):
            break
    return [item.ins for item in items], log


def side_by_side(
    original: list[TACInstruction],
    optimized: list[TACInstruction],
    changes: list[Change],
) -> list[DiffRow]:
    """Pair every original instruction with its optimized version.

    Removed instructions are known from the change log; the survivors appear
    in the optimized list in the same order as in the original.
    """
    removed = {c.index for c in changes if c.after is None}
    rows: list[DiffRow] = []
    k = 0   # position in the optimized list
    for i, ins in enumerate(original):
        if i in removed:
            rows.append(DiffRow(i, str(ins), "", "removed"))
        else:
            after = str(optimized[k])
            k += 1
            status = "unchanged" if after == str(ins) else "changed"
            rows.append(DiffRow(i, str(ins), after, status))
    return rows