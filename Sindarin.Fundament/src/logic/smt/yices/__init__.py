# encoding=utf-8
"""
Yices - an SMT solver from SRI.
http://yices.csl.sri.com/

Input format is standard SMT-LIB (1.2).
Output format is a bunch of closed formulas in the same format (with a bit
of metadata around them).
"""

from subprocess import Popen, PIPE
import os
from logic.smt.yices.input import YicesInputFormat
from logic.smt.yices.output import YicesOutputFormat
from logic.fol.syntax.formula import FolSymbolic
from logic.fol.semantics.extensions.equality import FolWithEquality
from filesystem.paths import CommonPath
from pattern.collection.basics import OneToMany, BuildupSet
from logic.fol.syntax.scheme import FolSubstitution



class Yices(object):
    """
    OO API for the Yices SMT solver.
    """
    
    UNIX_PATH = ["/usr/local/bin", "/opt/local/bin"]
    
    YICES1_COMMAND = "yices -e --smtlib"
    YICES2_COMMAND = "yices -m -f"
    
    def __init__(self):
        self.command = self.YICES1_COMMAND
        self.input_format = YicesInputFormat()
        self.output_format = YicesOutputFormat()
        
    def __call__(self, theory):
        in_ = str(self.input_format(theory))
        env = os.environ.copy()
        env["PATH"] = CommonPath().join()
        p = Popen(self.command, shell=True,
                  stdin=PIPE, stdout=PIPE, stderr=PIPE, env=env)
        out, err = p.communicate(in_)
        if p.returncode != 0:
            raise SystemError, "yices: %s\nInput was: %s" % (err, in_)
        if not out.startswith("sat") and not (out.startswith("unknown") and out.strip() != "unknown"):
            raise SystemError, "yices: %s\nInput was: %s" % (out, in_)
        try:
            return self.output_format(out)
        except:
            print out



class ForcedMarch(object):
    """
    An attempt to combine interpreted functions with an SMT solver. The 
    functions are expressed ordinarily as uninterpreted, but when a model is
    returned it is checked for any assigned function values and if it deviates
    for the value computed by the library function, an equation forcing the
    correct value is artificially introduced and the process is repeated.
    """
    
    class DivergeError(ValueError): pass
    
    def __init__(self, solver):
        self.solver = solver
        self.standard_interpretation = {}
        self.max_iterations = 5
        
    def with_(self, standard_interpretation):
        self.standard_interpretation.update(standard_interpretation)
        return self
        
    def __call__(self, theory):
        y = self.solver
        I = self.standard_interpretation
        L = FolSymbolic.Language(FolWithEquality.Signature)
        M = y(theory)
        # Now force
        force_theory = []
        for _ in xrange(self.max_iterations):
            n = len(force_theory)
            for symbol in M.interpretation:
                if symbol.kind == 'function' and symbol in I:
                    answer = M.interpretation[symbol]
                    compute = I[symbol]
                    for x in answer:
                        correct_answer = compute(x)
                        if answer[x] != correct_answer:
                            force_theory += [L.with_(x=x, f=symbol, fx=correct_answer) 
                                             * "eq(f(x), fx)"]
            if n == len(force_theory): break
            M = y(theory + force_theory)
        else:
            raise self.DivergeError, "theory closure does not converge"
        return M
                    
                    
                    
if __name__ == '__main__':
    import math
    from logic.fol import Identifier, FolFormula
    from logic.fol.semantics.extensions.sorts import FolManySortSignature
    from logic.fol.semantics.extensions.sorts import FolSorts
    
    def the_sine_cosine_demo():
        class Signature(FolWithEquality.Signature):
            add = Identifier("+", 'function')
            cos = Identifier("cos", 'function')
            sin = Identifier("sin", 'function')
            x = Identifier("[x]", 'function', mnemonic="x")
            
            sorts = FolSorts({add: "R×R→R",
                              sin: "R→R",
                              cos: "R→R",
                              x: "→R"})
            formal = FolManySortSignature.from_sorts(sorts)
    
            standard_interpretation = \
                {sin: lambda x: math.sin(x*math.pi/180),
                 cos: lambda x: math.cos(x*math.pi/180)}
            
        _ = Signature
        L = FolSymbolic.Language(Signature)
        
        phi = L.with_(_60=-60) * "eq(x, add(sin(_60), cos(_60)))"
        print phi
        
        y = Yices()
        y.input_format.logic = "QF_UFLRA"
        y.input_format.signature = L.signature
        y.input_format.builtin_mappings.update({_.add: "+"})
        y.output_format.signature = L.signature
            
        M = ForcedMarch(y).with_(_.standard_interpretation)([phi])
        print M
        print "%.64f" % M.interpretation[_.x]    
        
    def the_discrete_demo():
        class Signature(FolWithEquality.Signature):
            add = Identifier("+", 'function')
            mul = Identifier("*", 'function')
            gt = Identifier(">", 'predicate', mnemonic="gt")
            ge = Identifier("≥", 'predicate', mnemonic="ge")
            lt = Identifier("<", 'predicate', mnemonic="lt")
            le = Identifier("≤", 'predicate', mnemonic="le")

            x = Identifier("[x]", 'function', mnemonic="x")
            y = Identifier("[y]", 'function', mnemonic="y")
            z = Identifier("[z]", 'function', mnemonic="z")

            b = Identifier(":b:", 'function', mnemonic="b")

            i = Identifier("i", 'variable')
            
            sorts = FolSorts({add: "Z×Z→Z", mul: "Z×Z→Z", gt: "Z×Z→",
                              x: "Z→Z", y: "Z→Z", z: "Z→Z", b: "Z×Z→Z", i: "→Z"})
            formal = FolManySortSignature.from_sorts(sorts)
            
        _ = Signature
        L = FolSymbolic.Language(_)
        
        phi = L * ["i ** (eq(add(mul(x(i),3),y(i)), z(i)) & eq(b(i,z(i)),6) & ge(y(i),0) & lt(y(i),3))"]
        psi = L * ["eq(z(0),1)", "eq(z(1),8)", "eq(z(2),12)", "eq(z(3), 7)", "eq(x(4),3) & eq(y(4),1)"]
        print phi
        
        y = Yices()
        y.input_format.logic = "AUFLIA"
        y.input_format.signature = L.signature
        y.input_format.builtin_mappings.update({_.add: "+", _.mul: "*", 
                                                _.gt: ">", _.le: "<=", _.lt: "<", _.ge: ">="})
        y.output_format.signature = L.signature

        M = y(phi + psi)
        print M
        I = M.interpretation
        for i in sorted(I[_.z]):
            print "%3d  %6d  %6d  %6d" % (i, I[_.x][i], I[_.y][i], I[_.z][i])
        
    the_discrete_demo()

