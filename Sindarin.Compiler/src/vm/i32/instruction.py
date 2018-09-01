

class Instruction:
    """
    An instruction is a tuple of
        (m, t, (args...))
    where
        m - is the mnemonic (below)
        t - is a string of argument types (see Value)
        args - instruction arguments tuple, must be as long as t
    """
    ALLOC = "alloc"
    FREE = "free"
    VAL = "val"
    ADR = "adr"
    PTR = "ptr"
    MOV = "="
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    MOD = "%"
    CEQ = "=="
    CLT = "<"
    NOT = "!"
    LBL = "lbl"
    JUC = "juc" # unconditional jump
    JIF = "jif" # jump if nonzero
    EXT = "ext"
    CAL = "cal"
    RET = "ret"


class Value:
    IMMEDIATE = "i"
    MEMORY = "m"
    POINTER = "p"
