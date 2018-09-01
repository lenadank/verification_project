from compilation.codegen.c.ast import ProgramAst


class FormatCBlock(object):
    
    _ = ProgramAst.KINDS.by_tag
    ATOMIC = {_['x=y']: "%(x)s = %(y)s"}
    
    def __call__(self, ast):
        ops = [self.fmt_block, self.fmt_control_stmt, self.fmt_atomic_stmt]
        for op in ops:
            r = op(ast)
            if r != NotImplemented: return r
    
    def fmt_atomic_stmt(self, stmt):
        templ = self.ATOMIC[stmt.root]
        props = {k: self.fmt_leaf(v) for k,v in stmt.props._asdict().iteritems()}
        return [('', templ % props + ";")]
    
    def fmt_block(self, blk):
        if blk.root == self._["{...}"]:
            b = [('+', "{")] + sum((self(stmt) for stmt in blk.subtrees), [])
            b[-1] = ('-' + b[-1][0], b[-1][1])
            return b + [('', "}")]
        else:
            return NotImplemented
    
    def fmt_control_stmt(self, stmt):
        if stmt.root == ProgramAst.KINDS.ifthen:
            b = self.affine_block("if (%s)" % self.fmt_leaf(stmt.props.cond),
                                  self(stmt.props.cmd))
            return b
        else:
            return NotImplemented
    
    def fmt_symbol_decl(self, symbol):
        d = "%s %s;" % (symbol.name, self.fmt_type(symbol.type))
        return [('', d)]
    
    def fmt_type(self, type_):
        return str(type_)
    
    def fmt_leaf(self, leaf):
        if leaf.subtrees:
            raise ValueError, "expecting a leaf but found '%s'" % leaf
        return leaf.root
    
    def affine_block(self, header, body_lines):
        if body_lines and body_lines[0][0] == '+':
            _ = body_lines
            b = [(_[0][0], header + " " + _[0][1])] + _[1:]
        else:
            b = [('+', header)] + body_lines
        b[-1] = ('-' + b[-1][0], b[-1][1])
        return b
    
    def create_indentation(self, fmtd_lines, indent=0, tab="    "):
        def shft(indent):
            for nd, line in fmtd_lines:
                yield indent*tab + line
                for c in nd:
                    if c == '-': indent -= 1
                    if c == '+': indent += 1
            
        return '\n'.join(shft(indent))



if __name__ == '__main__':
    from logic.fol.syntax.parser import FolFormulaParser
    L = FolFormulaParser()
    ast = ProgramAst.reconstruct(L("[{...}]([x=y](c,k), [if (cond) cmd](c, [{...}]([x=y](d,h))))"))
    
    fmt = FormatCBlock()
    print fmt.create_indentation(fmt(ast))
    