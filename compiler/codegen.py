"""Phase 4: Intermediate code generation (Three Address Code).

Input : Node (the tree from the parser)
Output: list of TACInstruction

Three Address Code (TAC): every instruction has at most 3 addresses
(two operands and one result).   t1 = b * c

Instructions we generate:
    t1 = a + b          binary operation (op is + - * / < > <= >= == !=)
    x  = t1             copy (op is "=")
    L1:                 label       (a named position in the code)
    goto L1             unconditional jump
    ifFalse t1 goto L2  jump only if t1 is false (0)

Other views of the same instructions:
    Quadruples: (op, arg1, arg2, result)
    Triples   : (op, arg1, arg2); a later instruction refers to an earlier
                one by its index, e.g. (0)

How if / while become jumps:

    if (c) { A }              if (c) { A } else { B }       while (c) { A }
    -------------             -----------------------       ---------------
        <code for c>              <code for c>              L1:
        ifFalse c goto L1         ifFalse c goto L1             <code for c>
        <A>                       <A>                           ifFalse c goto L2
    L1:                           goto L2                       <A>
                              L1:                               goto L1
                                  <B>                       L2:
                              L2:
"""

from dataclasses import dataclass

from compiler.parser import Node


@dataclass
class TACInstruction:
    """One quadruple: (op, arg1, arg2, result).

    For control-flow instructions the label name is stored in `result`:
        label  -> op="label",   result="L1"
        goto   -> op="goto",    result="L1"
        ifFalse-> op="ifFalse", arg1=condition, result="L1" (the jump target)
    """

    op: str
    arg1: str = ""
    arg2: str | None = None
    result: str = ""

    def __str__(self) -> str:
        if self.op == "=":
            return f"{self.result} = {self.arg1}"
        if self.op == "label":
            return f"{self.result}:"
        if self.op == "goto":
            return f"goto {self.result}"
        if self.op == "ifFalse":
            return f"ifFalse {self.arg1} goto {self.result}"
        return f"{self.result} = {self.arg1} {self.op} {self.arg2}"


@dataclass
class Triple:
    """One triple: (op, arg1, arg2). Its position in the list is its name."""

    index: int
    op: str
    arg1: str
    arg2: str | None = None


def _collect_names(node: Node, names: set[str]) -> None:
    """Gather every variable name used in the program."""
    if node.kind == "Id":
        names.add(node.label)
    for child in node.children:
        _collect_names(child, names)


class CodeGenerator:
    """Walks the tree and emits TAC instructions."""

    def __init__(self, user_names: set[str]) -> None:
        self.code: list[TACInstruction] = []
        self.temp_count = 0
        self.label_count = 0
        self.user_names = user_names  # temp names must not clash with these

    # ---------- helpers -------------------------------------------------

    def new_temp(self) -> str:
        """Return a fresh temporary name: t1, t2, t3, ..."""
        while True:
            self.temp_count += 1
            name = f"t{self.temp_count}"
            if name not in self.user_names:  # skip if the user has a variable 't1'
                return name

    def new_label(self) -> str:
        """Return a fresh label name: L1, L2, L3, ..."""
        self.label_count += 1
        return f"L{self.label_count}"

    def emit(self, op: str, arg1: str, arg2: str | None, result: str) -> None:
        self.code.append(TACInstruction(op, arg1, arg2, result))

    def emit_label(self, label: str) -> None:
        self.emit("label", "", None, label)

    def emit_goto(self, label: str) -> None:
        self.emit("goto", "", None, label)

    def emit_if_false(self, condition: str, label: str) -> None:
        self.emit("ifFalse", condition, None, label)

    # ---------- statements ----------------------------------------------

    def gen_program(self, node: Node) -> None:
        for statement in node.children:
            self.gen_stmt(statement)

    def gen_stmt(self, node: Node) -> None:
        if node.kind == "Decl":
            # "int x;" needs no code. "int x = e;" is just an assignment.
            if len(node.children) > 1:
                value = self.gen_expr(node.children[1])
                self.emit("=", value, None, node.children[0].label)
        elif node.kind == "Assign":
            value = self.gen_expr(node.children[1])
            self.emit("=", value, None, node.children[0].label)
        elif node.kind == "If":
            self.gen_if(node)
        elif node.kind == "While":
            self.gen_while(node)
        elif node.kind == "Block":
            for statement in node.children:
                self.gen_stmt(statement)

    def gen_if(self, node: Node) -> None:
        condition = self.gen_expr(node.children[0])
        else_label = self.new_label()
        self.emit_if_false(condition, else_label)
        self.gen_stmt(node.children[1])                 # then-block
        if len(node.children) == 3:                      # there is an else-block
            end_label = self.new_label()
            self.emit_goto(end_label)                    # skip the else part
            self.emit_label(else_label)
            self.gen_stmt(node.children[2])
            self.emit_label(end_label)
        else:
            self.emit_label(else_label)

    def gen_while(self, node: Node) -> None:
        start_label = self.new_label()
        end_label = self.new_label()
        self.emit_label(start_label)
        condition = self.gen_expr(node.children[0])
        self.emit_if_false(condition, end_label)
        self.gen_stmt(node.children[1])
        self.emit_goto(start_label)                      # go back and test again
        self.emit_label(end_label)

    # ---------- expressions ---------------------------------------------

    def gen_expr(self, node: Node) -> str:
        """Generate code for an expression and return where its value lives.

        Leaves (Id, Num) need no code: their "address" is the name or number.
        A BinOp or Cond generates code for the left side, then the right side,
        then one instruction that combines them into a new temporary.
        """
        if node.kind in ("Id", "Num"):
            return node.label
        left = self.gen_expr(node.children[0])
        right = self.gen_expr(node.children[1])
        temp = self.new_temp()
        self.emit(node.label, left, right, temp)
        return temp


def generate(tree: Node) -> list[TACInstruction]:
    """Generate TAC for a whole program tree."""
    names: set[str] = set()
    _collect_names(tree, names)
    generator = CodeGenerator(names)
    generator.gen_program(tree)
    return generator.code


def to_triples(code: list[TACInstruction]) -> list[Triple]:
    """Convert quadruples into triples.

    A triple has no result field, so wherever a temporary was used as an
    operand we write the index of the instruction that produced it, e.g. (0).
    Only binary operations (including comparisons) produce temporaries.
    Jumps keep the label NAME as their target (see README limitations).
    """
    temp_to_index: dict[str, int] = {}
    triples: list[Triple] = []

    def ref(arg: str | None) -> str | None:
        if arg is not None and arg in temp_to_index:
            return f"({temp_to_index[arg]})"
        return arg

    for i, ins in enumerate(code):
        if ins.op == "=":
            triples.append(Triple(i, "=", ins.result, ref(ins.arg1)))
        elif ins.op == "ifFalse":
            triples.append(Triple(i, "ifFalse", ref(ins.arg1), ins.result))
        elif ins.op in ("goto", "label"):
            triples.append(Triple(i, ins.op, ins.result, None))
        else:
            triples.append(Triple(i, ins.op, ref(ins.arg1), ref(ins.arg2)))
            temp_to_index[ins.result] = i
    return triples