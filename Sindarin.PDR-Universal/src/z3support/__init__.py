
from z3 import Z3_get_ast_id

def get_id(f):
    return Z3_get_ast_id(f.ctx.ref(), f.as_ast())
