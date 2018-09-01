#encoding=utf-8
import copy
from pattern.collection.basics import OneToOne
from logic.fol.semantics.extensions.arith import FolIntegerArithmetic
from logic.fol.syntax import Identifier
from pattern.collection.assembly import SegmentedList



class SemanticError(Exception):
    pass


class ExpressionCompiler(object):
    
    SemanticError = SemanticError
    
    class Context(object):
        def __init__(self):
            self.args = []
            self.height = 0
        def __add__(self, offset):
            c = copy.copy(self)
            c.height += offset
            return c
            
    class CodeAddress(object):
        def __init__(self, value=None):
            self.value = value
        def __repr__(self):
            return '@%r' % self.value
    
    class AnonymousLabel(object): pass
    
    INLINES = {FolIntegerArithmetic.add: ['add'],
               FolIntegerArithmetic.sub: ['sub'],
               FolIntegerArithmetic.mul: ['mul'],
               
               '//': ['floordiv']}
    
    def __init__(self):
        self.symbol_table = OneToOne().of(self.CodeAddress)
        self.native_types = (int,)
    
    def __call__(self, formula, freevars=[]):
        ctx = self.Context()
        ctx.args = freevars
        return self._codegen(ctx, formula) + self._epilogue(ctx)
    
    def _codegen(self, ctx, t):
        r, s = t.root, t.subtrees
        
        if r == '?:' and len(s) == 3: # short circuiting - crucial for recursion
            cond, then_, else_ = (self._codegen(ctx, x) for x in s)
            t = self.AnonymousLabel()
            f = self.AnonymousLabel()
            CA = self.CodeAddress
            return (cond + ['push', CA(t), 'jump_if'] +
                    SegmentedList.promote(else_) + ['jump_fast', CA(f)] +
                    SegmentedList.promote(then_).labeled(t) + SegmentedList().labeled(f))
        
        asub = [el
                for i, x in enumerate(reversed(s)) for el in self._codegen(ctx + i, x)]
        if r in ctx.args and not s:
            # Note: args appear in the stack in reverse order (last argument is pushed first)
            return ['pick', ctx.height + ctx.args.index(r) + 1]
        elif isinstance(r, self.native_types):
            return ['push', r]
        elif isinstance(r, Identifier) and isinstance(r.literal, self.native_types):
            return ['push', r.literal]
        elif r in self.INLINES:
            return asub + self.INLINES[r]
        else:
            # Assume it is a function that would be defined later
            call_site = ['push', self.symbol_table[r],
                         'call']
            return asub + call_site
            #raise self.SemanticError(t)
        
    def _epilogue(self, ctx):
        return ['pick', 1, 
                'yank/2', len(ctx.args) + 1, 2,
                'jump']
        



class Linker(object):
    
    CodeAddress = ExpressionCompiler.CodeAddress
    
    def weld(self, minisegments_dict, entry_point=None):
        callees = [SegmentedList(v).labeled(k) for k,v in minisegments_dict.iteritems()
                   if k != entry_point]
        mainf = minisegments_dict.get(entry_point, [])
        if entry_point is not None: mainf = SegmentedList(mainf).labeled(entry_point)
        return sum(callees, mainf)
    
    def unresolved_symbols(self, code):
        return set([x.value for x in code if isinstance(x, self.CodeAddress)])
    
    def backpatch(self, segmented):
        if isinstance(segmented, SegmentedList):
            segmented = SegmentedList(segmented.labels[x.value] 
                                      if isinstance(x, self.CodeAddress) and 
                                         x.value in segmented.labels 
                                      else x
                                      for x in segmented)
        return segmented

    def __call__(self, code_to_link):
        linked = self.backpatch(code_to_link)

        # Check for any unresolved symbols
        us = self.unresolved_symbols(linked)
        if us:
            raise SemanticError("unresolved symbols remain: %s" % us)
        
        return linked



if __name__ == '__main__':
    from logic.fol.syntax.parser import FolFormulaParser
    
    c = ExpressionCompiler()
    
    L = FolFormulaParser()
    program = {'f': (["x", "y"], L * "[?:](x, f(x-1, y) + 1, g(y))"),
               'g': (["a"], L * "2 * a"),
               'main': (["x", "y"], L * "f(x,y)")}
    program = {'fib': (["i"], L * "[?:](i, [?:](i - 1, fib(i-1) + fib(i-2), 1), 1)"),
               'main': (['i', 'j'], L * "fib(i)")}
    asm = {name: c(body, argnames) for name,(argnames, body) in program.iteritems()}
    
    #raise SystemExit
    
    # Link the code with sample stub prefix
    prefix = ['push', 0x9, 'push', 0x4, 'push', -1]    # main(0x4, 0x9), retaddr=-1 (exit)
    
    l = Linker()
    asm = l.weld(asm, entry_point='main')
    lasm = l(prefix + asm)
    
    # Try it
    from vm.stack_machine.processor import Processor
    
    p = Processor()
    try:
        print p(lasm)
    except:
        print p._ss
        raise