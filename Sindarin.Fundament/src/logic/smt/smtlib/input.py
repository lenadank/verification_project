# encoding=utf-8

import math
from functools import partial

from adt.tree import Tree
from adt.tree.transform import TreeTransform
from adt.tree.transform.substitute import TreeSubstitution

from logic.fol import FolFormula, Identifier
from logic.fol.semantics.extensions.sorts import FolManySortSignature
from logic.fol.semantics.extensions.equality import FolWithEquality
from logic.fol.syntax.transform import AuxTransformers
from logic.fol.syntax.transform.delta import DeltaReduction
from logic.smt.smtlib.sexpr import SExpression
from logic.smt.smtlib import NamingConvention
from pattern.debug.profile import ProcessingPhases



class SchemeExpression(Tree):
    """
    Basically a function-call expression of the form
    (f arg0 arg1 ...)
    which may be nested.
    """
    
    def __init__(self, *a, **kw):
        """@see adt.tree.Tree.__init__ for prototype"""
        super(SchemeExpression, self).__init__(*a, **kw)
        self.attributes = []
        
    def __str__(self):
        if isinstance(self.root, FolFormula.Identifier):
            r = self.root.mnemonic
        else:
            r = self.root
        if isinstance(r, bool):
            r = ["false", "true"][int(r)]
        elif isinstance(r, float):
            neg = (r < 0); r = math.fabs(r)
            r = "(/ %d %d)" % r.as_integer_ratio() # gives maximal precision
            if neg: r = '(- 0 %s)' % r
        elif isinstance(r, int) and r < 0:
            r = '(- 0 %d)' % (-r)
        else:
            r = str(r)
            
        if self.subtrees or self.attributes:
            return "(%s%s%s)" % (r,
                                   "".join(" "+str(s) for s in self.subtrees),
                                   "".join("\n"+str(s) for s in self.attributes))
        else:
            return r
    
    def __nonzero__(self):
        return not not (self.root or len(self.subtrees) or self.attributes)
        
    @classmethod
    def promote(cls, o):
        if isinstance(o, cls): return o
        return cls(o)

    ##
    # Parsing
    ##

    @classmethod
    def tokenize(cls, text):
        import re
        l = re.compile("[ ()]|[^ ()]+")
        return [tok for tok in l.findall(text) if tok != " "]

    @classmethod
    def parse(cls, token_stream):
        if isinstance(token_stream, str): 
            token_stream = cls.tokenize(token_stream)
        t = iter(token_stream)
        tok = t.next()
        if tok != "(": return tok
        root = tok = t.next()
        subexpr = []
        while tok != ")":
            tok = cls.parse(t)
            if tok != ")":
                subexpr.append(cls.promote(tok))
        return cls(root, subexpr)
        


class SmtLibInputFormat(object):
    
    class Attribute(object):
        def __init__(self, name, value):
            self.name = name
            self.value = value
        def __str__(self):
            return ":%s %s" % (self.name, self.value)
            
    def __init__(self, signature=FolManySortSignature(), logic="QF_UF"):
        self.signature = signature
        if not isinstance(signature, FolManySortSignature):
            self.signature = FolManySortSignature(signature.funcs, signature.preds)
        self.logic = logic
        self.builtin_mappings = {'R': "Real",
                                 'Z': "Int",
                                 FolWithEquality.Signature.eq: "="}
            
    def predicates(self, preds):
        S = SchemeExpression
        return S("", [S(p, self.sort_of(p,a) or [""]) for p,a in preds
                      if p not in self.builtin_mappings])
    
    def functions(self, funcs):
        S = SchemeExpression
        return S("", [S(f, self.sort_of(f,a)) for f,a in funcs
                      if f not in self.builtin_mappings])
    
    def quantified_expression(self, variable):
        S = SchemeExpression
        return S("?%s" % variable, self.sort_of(variable,0))
    
    def mkid(self, identifier, *a):
        x = identifier
        return SchemeExpression(self.builtin_mappings.get(x, x), *a)
    
    def sort_of(self, symbol, arity):
        S = self.mkid
        sr = self.signature.sort_of(symbol, arity)

        if not sr:
            raise TypeError, "No sort for '%s/%d'" % (symbol, arity)

        from_,to_ = sr[0] # TODO support more than one 
        to_ = [x for x in [to_] if x is not None]
        return [S(f) for l in (from_, to_) for f in l]
    
    def benchmark(self, title):
        return SchemeExpression("benchmark %s" % title)
    
    def list(self, l): #@ReservedAssignment
        S = SchemeExpression
        if l:
            return S("", [S.promote(x) for x in l])
        else:
            return S("", [""])
    
    def formula(self, formula):
        r = formula.root
        quantifiers_and_connectives = {FolFormula.FORALL: "forall",
                                       FolFormula.EXISTS: "exists",
                                       FolFormula.IMPLIES: "implies",
                                       FolFormula.AND: "and",
                                       FolFormula.OR: "or",
                                       FolFormula.IFF: "iff",
                                       FolFormula.NOT: "not"
                                      }
        it = r
        kind = None
        if isinstance(r, FolFormula.Identifier):
            kind = r.kind
            if r.kind == 'quantifier' or r.kind == 'connective':
                it = quantifiers_and_connectives[r]
            if r.kind == 'variable':
                it = "?%s" % r
        S = self.mkid
        if kind == 'quantifier':
            expr = S(it, [self.quantified_expression(s.root) for s in formula.subtrees[:-1]] +
                         [self.formula(s) for s in formula.subtrees[-1:]])
        else:
            expr = S(it, [self.formula(s) for s in formula.subtrees])
        return self._tree_fold(expr)
    
    def theory(self, formulas, title="theory"):
        bm = self.benchmark(title)
        A = self.Attribute
        signature = self.signature
        all_sorts = set(["V"]) | self.signature.sorts.set()
        all_sorts = set(x for x in all_sorts if x not in self.builtin_mappings)
        attrs = [A("logic", SchemeExpression(self.logic)),
                 A("extrasorts", self.list(all_sorts)),
                 A("extrafuns", self.functions(signature.funcs)),
                 A("extrapreds", self.predicates(signature.preds))]
        attrs = [a for a in attrs if a.value]
        bm.attributes.extend(attrs)
        if formulas:
            bm.attributes.extend([A("assumption", self.formula(f))
                                  for f in formulas[:-1]])
            bm.attributes.append(A("formula", self.formula(formulas[-1])))
        return bm

    def __call__(self, thing):
        if isinstance(thing, list):
            thing = self.theory(thing, "theory")
        elif isinstance(thing, FolFormula):
            thing = self.theory([thing], "formula")
        return thing

    def _tree_fold(self, tree, foldables=("and", "or")):
        r = tree.root
        if r in foldables:
            subs = []
            for s in tree.subtrees:
                if s.root == r:
                    subs.extend(self._tree_fold(s, foldables).subtrees)
                else:
                    subs.append(s)
        else:
            subs = tree.subtrees
        return type(tree)(r, [self._tree_fold(s, foldables) for s in subs])
    
    

    
class SmtLib2InputFormat(object):
 
    def __init__(self, naming_convention=NamingConvention()):
        _ = AuxTransformers
        fold_f = TreeTransform([_.fold], dir=TreeTransform.BOTTOM_UP)
        #fold_f.IS_DESCENDING = True
        self.naming = naming_convention
        
        regroup_f = TreeTransform([partial(_.regroup, head='forall', tag='')], dir=TreeTransform.BOTTOM_UP)

        synonyms = {FolFormula.FORALL:   Identifier('forall', 'quantifier'),
                    FolFormula.EXISTS:   Identifier('exists', 'quantifier'),
                    FolFormula.AND:      Identifier('and', 'connective'),
                    FolFormula.OR:       Identifier('or', 'connective'),
                    FolFormula.IFF:      Identifier('iff', 'connective'),
                    FolFormula.IMPLIES:  Identifier('=>', 'connective'),
                    FolFormula.NOT:      Identifier('not', 'connective'),
                    True: 'true', False: 'false'}
        synonyms_f = TreeSubstitution(synonyms)
    
        #e = Expansion()   # must get rid of it; only needed for the parser
        L = DeltaReduction.Transformer._mkparser()   # suggested optimization: use singleton for parser. Also, only parse macros once
        macros =  ["x != y := ~(x=y)",
                   "forall x (psi) := [forall]([]([](x,V)), psi)",
                   "exists x (psi) := [exists]([]([](x,V)), psi)"]
        macros_f = DeltaReduction(dir=TreeTransform.BOTTOM_UP)
        macros_f.IS_DESCENDING = False
        macros_f.transformers += \
            [DeltaReduction.Transformer(macros_f, L(m)) for m in macros]
                     
        from adt.tree.transform.apply import ApplyTo  # @Reimport
        escape_f = ApplyTo(nodes=naming_convention.escape_safe).inplace
        
        
        self.phases = ProcessingPhases([(macros_f, "Operators/quantifiers"),
                                        (SExpression.reconstruct, "S-expression"), 
                                        (fold_f, "Fold"), 
                                        (synonyms_f, "Rename keywords"),
                                        (regroup_f, "Regroup"),
                                        (escape_f, "Escape identifiers")])
        self.preface = ''

    def to_declare(self, sigma):
        """
        @param sigma: FolManySortSignature instance containing declarations
           to emit.
        @return a generator for declaration sexprs
        """
        S = lambda x, *a: SExpression(self.naming.escape_safe(x), *a)
        
        for s in sigma.symbols:
            if s.kind in ['function', 'predicate']:
                tps = sigma.sorts[s]
                for tp in tps:
                    to = tp.to_ if tp.to_ else 'Bool'
                    if tp.from_:
                        yield S('declare-fun', [S(s), S('', [S(x) for x in tp.from_]), S(to)])
                    else:
                        yield S('declare-const', [S(s), S(to)])
                

    def to_sexprs(self, phi):
        for conj in phi.split():
            se = self.phases(conj)
            yield se



if __name__ == '__main__':
    from logic.fol.syntax.formula import FolSymbolic
    from logic.fol.semantics.extensions.sorts import FolSorts
    
    class Signature(FolWithEquality.Signature):
        add = Identifier("+", 'function')
        cos = Identifier("cos", 'function')
        sin = Identifier("sin", 'function')
        x = Identifier("x", 'function')
        
        sorts = FolSorts({add: "R×R→R",
                          sin: "R→R",
                          cos: "R→R",
                          x: "→R"})
        formal = FolManySortSignature.from_sorts(sorts)
        
    _ = Signature
    L = FolSymbolic.Language(Signature)
    
    sif = SmtLib2InputFormat()
    
    for decl in sif.to_declare(_.formal):
        print decl
    
    raise SystemExit
    
    phi = L.with_(_60=-60) * "eq(x, add(sin(_60), cos(_60)))"
    print phi
    
    yic = SmtLibInputFormat(L.signature, logic="QF_UFLRA")
    yic.builtin_mappings.update({_.add: "+"})
    bm = yic.theory([phi], "sample")
    print bm
    print >> file("/tmp/autogen.smt", "w"), bm
    
