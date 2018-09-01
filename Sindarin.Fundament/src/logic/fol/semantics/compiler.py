# encoding=utf-8

import string

from logic.fol.syntax.formula import FolFormula, Identifier
from logic.fol.semantics import FolSemanticError



class FolEvalCodegen(object):
    
    class Unit(object):
    
        def __init__(self):
            self.main = None
            self.preamble = ""
            self.ids = {}
            self.bindings = {}
            self.funcs = []
            
        def with_ids(self, ids):
            self.ids = ids
            return self
        
        def id_of(self, symbol):
            idof,_ = self._id(symbol)
            return idof
            
        def __str__(self):
            func_code = "\n".join(str(f) for f in self.funcs + [self.main])
            return self.preamble + "\n" + func_code

        def _id(self, symbol):
            if not isinstance(symbol, Identifier):
                raise FolSemanticError(symbol)
            try:
                return self.ids[symbol], True
            except KeyError:
                i = "%s%d" % ("".join(c for c in str(symbol)
                                      if c in string.letters + "_") or "i", 
                              len(self.ids))
                self.ids[symbol] = i = FolFormula.Identifier(i, symbol.kind)
                return i, True
                        
            
    class Code(object):

        def __init__(self, body, freevars=()):
            self.body = body
            self.freevars = freevars
            self.behavior = None
            self.name = ""

        def behave(self, behavior):
            self.behavior = behavior
            return self

        def __repr__(self):
            if self.behavior is None:
                return self.body
            else:
                return self % self.behavior
        
    class Block(Code):
        pass
    
    class Expr(Code):
        pass
    
    class Behavior(object):

        def __init__(self, istrue, isfalse, ret, header="", footer="", indent=""):
            self.values = {'istrue': istrue, 'isfalse': isfalse}
            self.ret = ret
            self.header = header
            self.footer = footer
            self.indent = indent

        def __rmod__(self, code):
            body = self._prefix(self.indent, self.body(code))
            fillin = self._fillin(code)
            if self.header:
                header = self.header % fillin + "\n"
            else:
                header = ""
            if self.footer:
                footer = "\n" + self.footer % fillin
            else:
                footer = ""
            return header + body + footer
        
        def body(self, code):
            if isinstance(code, FolEvalCodegen.Block):
                body = code.body % self.values
            else:
                body = self.ret % {'value': code.body}
            return body
        
        def _fillin(self, block):
            fv = [str(x) for x in block.freevars]
            return {'name': block.name,
                    'freevars': ",".join(sorted(fv))}

        def _prefix(self, prefix, text):
            return "\n".join(prefix + line for line in text.splitlines())
        
        
    def __init__(self):
        self.dialect = FolPythonDialect
    
    def __call__(self, formula, unit=None):
        if unit is None:
            unit = self.make_unit()
        unit.main = self.emit(unit, formula).behave(self.dialect.PROG_BEHAVIOR)
        unit.main.name = 'main'
        return unit
        
    def make_unit(self, **kw):
        return self.dialect.Unit(**kw)
    
    def emit(self, unit, formula):
        op = formula.root
        B = self.Block
        E = self.Expr
        _ = self.dialect.EXPRESSIONS
        freevars = set()
        def e(subformula):
            c = self.emit(unit, subformula)
            freevars.update(c.freevars)
            return self._refer(unit, c)
        # Quantifier semantics
        if op == FolFormula.FORALL:
            variable, subformula = formula.subtrees
            variable = unit.id_of(variable.root)
            c = e(subformula)
            b = B(_['for var in D (if not cond then false) true']
                   % dict(var=variable, cond=c),
                  freevars=freevars-set([variable]))
            return b
        if op == FolFormula.EXISTS:
            variable, subformula = formula.subtrees
            variable = unit.id_of(variable.root)
            c = e(subformula)
            b = B(_['for var in D (if cond then true) false']
                   % dict(var=variable, cond=c),
                  freevars=freevars-set([variable]))
            return b
        # Connective semantics
        elif op == FolFormula.IMPLIES:
            lhs, rhs = formula.subtrees
            return E(_["not a or b"] % dict(a=e(lhs), b=e(rhs)), freevars)
        elif op == FolFormula.IFF:
            lhs, rhs = formula.subtrees
            return E(_["a iff b"] % dict(a=e(lhs), b=e(rhs)), freevars)
        elif op == FolFormula.AND:
            lhs, rhs = formula.subtrees
            return E(_["a and b"] % dict(a=e(lhs), b=e(rhs)), freevars)
        elif op == FolFormula.OR:
            lhs, rhs = formula.subtrees
            return E(_["a or b"] % dict(a=e(lhs), b=e(rhs)), freevars)
        elif op == FolFormula.NOT:
            rhs, = formula.subtrees
            return E(_["not a"] % dict(a=e(rhs)), freevars)
        # Structure interpretation semantics
        else:
            i, is_free = unit._id(op)
            if is_free: freevars.add(i)
            if formula.subtrees:
                args = [e(s) for s in formula.subtrees]
                expr = self.dialect.CALLING.predicate(i, args)
            else:
                expr = str(i)
            return self.Expr(expr, freevars)
            

    def _refer(self, unit, code):
        if isinstance(code, self.Block):
            code.name = "f%d" % id(code)
            unit.funcs += [code.behave(self.dialect.FUNC_BEHAVIOR)]
            return self.dialect.CALLING.subexpression(code)
        else:
            return str(code)
        
        
class FolPythonDialect(object):
    
    EXPRESSIONS = \
    {'for var in D (if cond then true) false':
     "for %(var)s in d:\n"
     "    if %(cond)s:\n"
     "        %%(istrue)s\n"
     "%%(isfalse)s",
     'for var in D (if not cond then false) true':
     "for %(var)s in d:\n"
     "    if not %(cond)s:\n"
     "        %%(isfalse)s\n"
     "%%(istrue)s",
     'a and b':     "(%(a)s and %(b)s)",
     'a or b':      "(%(a)s or %(b)s)",
     'not a':       "(not %(a)s)",
     'not a or b':  "(not %(a)s or %(b)s)",
     'a iff b':     "(%(a)s == %(b)s)",
     }
    
    class Behavior(FolEvalCodegen.Behavior):
        def body(self, code):
            body = super(FolPythonDialect.Behavior, self).body(code)
            if code.name == "main": # yuCK!!
                body = code.init + "\n" + body
            return body

    PROG_BEHAVIOR = Behavior(istrue="return True",
                             isfalse="return False",
                             ret="return %(value)s",
                             header="def main(d, i):",
                             indent="    ")
    FUNC_BEHAVIOR = Behavior(istrue="return True",
                             isfalse="return False",
                             ret="return %(value)s",
                             header="def %(name)s(d, %(freevars)s):",
                             indent="    ")

    class CallingConvention(object):
        def subexpression(self, code):
            fv = [str(x) for x in code.freevars]
            return "%s(d, %s)" % (code.name, ",".join(sorted(fv)))
        def predicate(self, op, args):
            return "%s(%s)" % (op, ", ".join(args))
        
    CALLING = CallingConvention()

    class Unit(FolEvalCodegen.Unit):
        
        def __str__(self):
            func_code = "\n".join(str(f) for f in self.funcs)
            self.main.init = "\n".join(self.init_code())
            main_code = str(self.main)
            return self.preamble + "\n" + func_code + "\n\n" + main_code
        
        def init_code(self):
            init_code = ["%s = i[%r] # %r" % (v, unicode(k.literal), k)
                          for k, v in self.ids.iteritems()
                          if (k.kind in ['function', 'predicate', '?'] or 
                              self.ids[k] in self.main.freevars)
                             and k not in self.bindings]
            init_code += ["%s = %s" % (v, self.bindings[k])
                          for k, v in self.ids.iteritems()
                          if k in self.bindings]
            return init_code
        
        def to_function(self):
            d = {}
            exec str(self) in d
            return d['main']
        
    
class FolCDialect(object):
    
    EXPRESSIONS = \
    {'for var in D (if cond then true) false':
     "for (int %(var)s=0; %(var)s<d; ++%(var)s) {\n"
     "    if (%(cond)s) {\n"
     "        %%(istrue)s\n"
     "    }\n"
     "}\n"
     "%%(isfalse)s",
     'for var in D (if not cond then false) true':
     "for (int %(var)s=0; %(var)s<d; ++%(var)s) {\n"
     "    if (! %(cond)s) {\n"
     "        %%(isfalse)s\n"
     "    }\n"
     "}\n"
     "%%(istrue)s",
     'a and b':     "(%(a)s && %(b)s)",
     'a or b':      "(%(a)s || %(b)s)",
     'not a':       "(! %(a)s)",
     'not a or b':  "(! %(a)s || %(b)s)",
     'a iff b':     "(%(a)s == %(b)s)",
     }
    
    class Behavior(FolEvalCodegen.Behavior):
        def _fillin(self, block):
            fv = [str(x) for x in block.freevars if x.kind=='variable']
            return {'name': block.name,
                    'freevars': ",".join("int "+x for x in ["d"]+sorted(fv))}

    PROG_BEHAVIOR = Behavior(istrue="return true;",
                             isfalse="return false;",
                             ret="return %(value)s;")
    FUNC_BEHAVIOR = Behavior(istrue="return true;",
                             isfalse="return false;",
                             ret="return %(value)s;",
                             header="bool %(name)s(%(freevars)s) {",
                             footer="}",
                             indent="    ")
    
    class CallingConvention(object):
        def subexpression(self, code):
            fv = [str(x) for x in code.freevars if x.kind=='variable']
            return "%s(%s)" % (code.name, ",".join(["d"] + sorted(fv)))
        def predicate(self, op, args):
            return "%s%s" % (op, "".join("[%s]"%a for a in args))

    CALLING = CallingConvention()            

    class Unit(FolEvalCodegen.Unit):
        
        def __init__(self, name="formula"):
            super(FolCDialect.Unit, self).__init__()
            self.name = name
            self.main = ""
        
        def __str__(self):
            init_code = self.declarations()
            func_code = "\n".join(str(f) for f in self.funcs)
            main_code = "bool eval_%s(int d) {\n%s\n}" % (self.name, self.main)
            return init_code + "\n" + func_code + "\n" + main_code

        def declarations(self):
            # TODO: Fol compiler:C declarations:
            # This is very very specific. Use the signature to generalize
            arrays = []
            scalars = []
            for symbol, cid in self.ids.iteritems():
                if symbol.kind == 'predicate':
                    arrays.append(u"int %s[4][4]; /* %s */" % (cid, symbol))
                elif symbol.kind == 'function':
                    scalars.append(u"int %s; /* %s */" % (cid, symbol))
            return u"\n".join(arrays + scalars)


class Gcc(object):
    def compile_and_run(self, program_code, aout="/tmp/eval"):
        import subprocess
        gcc = subprocess.Popen("g++ -o %s -xc++ -" % aout,
                               shell=True,
                               stdin=subprocess.PIPE)
        gcc.communicate(program_code)
        if gcc.returncode == 0:
            ev = subprocess.Popen(aout, stdout=subprocess.PIPE);
            return ev.communicate()



if __name__ == '__main__':
    from adt.tree.build import TreeAssistant
    
    t = TreeAssistant().of(FolFormula)
    
    class Signature:
        a = FolFormula.Identifier(u'α', 'predicate')
        v = FolFormula.Identifier('v', 'variable')
        u = FolFormula.Identifier('u', 'variable')
        
    FORALL = FolFormula.FORALL
    IMPLIES = FolFormula.IMPLIES
    AND = FolFormula.AND
    vars().update(Signature.__dict__)

    inputs = [(FORALL, [v, (FORALL, [u, (IMPLIES, [(a, [v, u]), (a, [u, v])])])]), #@UndefinedVariable
              (FORALL, [u, (a, [u, u])]) #@UndefinedVariable
              ]
    
    for input in inputs:
        formula = t(input)
        print formula
        
        print '-' * 20
        print "/Python/"
        cg = FolEvalCodegen()
        cg.dialect = FolPythonDialect
        
        code = cg(formula)

        compiled_formula = code.to_function()
        
        d = [1,2]
        print compiled_formula(d, i = {a: lambda x,y: x==y}) #@UndefinedVariable
        print compiled_formula(d, i = {a: lambda x,y: x<=y}) #@UndefinedVariable

        print '-' * 20
        print "/C/"
        cg = FolEvalCodegen()
        cg.dialect = FolCDialect
        code = cg(formula, cg.make_unit(name="phi"))

        #print code.ids
        #print code
        
        main_template = r"""
        #include <stdio.h>
        const int D=4;
        int main(int argc, char *argv[]) {
            for (int i=0; i<D; ++i)
                for (int j=0; j<D; ++j)
                    %(alpha)s[i][j] = %(alpha_expr)s;
            printf("%%s\n", eval_phi(D) ? "true" : "false");
        }
        """
        
        main1 = main_template % {'alpha': code.ids[u"α"], 'alpha_expr': "i==j"}
        main2 = main_template % {'alpha': code.ids[u"α"], 'alpha_expr': "i<=j"}

        print Gcc().compile_and_run(str(code) + "\n" + main1)
        print Gcc().compile_and_run(str(code) + "\n" + main2)
        
        print "=" * 40
