"""Phase 4: Intermediate code generation (Three Address Code).

Input : Node (the tree from the parser)
Output: list of TACInstruction

Three Address Code (TAC) means every instruction has at most 3 addresses:
two operands and one result.   t1 = b * c

The same instructions can be shown in two other forms:
    Quadruples: (op, arg1, arg2, result)   -> result is a named temp/variable
    Triples   : (op, arg1, arg2)           -> no result field; a later
                instruction refers to an earlier one by its index, e.g. (0)

Tier 1 instructions:
    t1 = a + b      binary operation   (op is + - * /)
    x  = t1         copy               (op is "=")
"""

from dataclasses import dataclass

from compiler.parser import Node


@dataclass
class TACInstruction:
    """One quadruple: (op, arg1, arg2, result)."""

    op: str
    arg1: str
    arg2: str | None = None
    result: str = ""

    def __str__(self) -> str:
        if self.op == "=":
            return f"{self.result} = {self.arg1}"
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
        self.user_names = user_names  # temp names must not clash with these

    def new_temp(self) -> str:
        """Return a fresh temporary name: t1, t2, t3, ..."""
        while True:
            self.temp_count += 1
            name = f"t{self.temp_count}"
            if name not in self.user_names:  # skip if the user has a variable 't1'
                return name

    def emit(self, op: str, arg1: str, arg2: str | None, result: str) -> None:
        self.code.append(TACInstruction(op, arg1, arg2, result))

    def gen_program(self, node: Node) -> None:
        for statement in node.children:
            self.gen_stmt(statement)

    def gen_stmt(self, node: Node) -> None:
        if node.kind == "Assign":
            target = node.children[0].label
            value = self.gen_expr(node.children[1])
            self.emit("=", value, None, target)

    def gen_expr(self, node: Node) -> str:
        """Generate code for an expression and return where its value lives.

        Leaves (Id, Num) need no code: their "address" is the name or number.
        A BinOp generates code for the left side, then the right side, then
        one instruction that combines them into a new temporary.
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
    Every binary-operation result is a temporary; "=" results are variables.
    """
    temp_to_index: dict[str, int] = {}
    triples: list[Triple] = []

    def ref(arg: str | None) -> str | None:
        if arg is not None and arg in temp_to_index:
            return f"({temp_to_index[arg]})"
        return arg

    for i, ins in enumerate(code):
        if ins.op == "=":
            # x = t1  becomes  (=, x, (k))
            triples.append(Triple(i, "=", ins.result, ref(ins.arg1)))
        else:
            triples.append(Triple(i, ins.op, ref(ins.arg1), ref(ins.arg2)))
            temp_to_index[ins.result] = i
    return triples
