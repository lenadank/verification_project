#encoding=utf-8
'''
Interpretation of Models from the Output of Z3.
'''
import copy

from pattern.meta import oop

from logic.fol.semantics.extensions.sorts import FolManySortSignature, FolSorts
from logic.fol.syntax import Identifier
from logic.fol.semantics.structure import FolStructure
from logic.fol.semantics.graphs import AlgebraicStructureGraphTool

from logic.smt.smtlib import NamingConvention
from logic.smt.smtlib.sexpr import SExpressionParser
from collections import namedtuple
import operator


class ProcessModel(object):
    """
    Reads the elements of a logical structure produced by e.g. (get-model).
    """
    
    STANDARD_INTERPRETATION = { 'ite': lambda c, t, f: (t if c else f),
                                '=': lambda x,y: x == y,
                                'and': lambda *x: reduce(operator.and_, x), 
                                'or': lambda *x: reduce(operator.or_, x),
                                'not': lambda x: not x,
                                'false': lambda: False,
                                'true': lambda: True }
    
    def __init__(self):
        self.funcs = {}
        
    def __call__(self, model_sexpr):
        r = model_sexpr.root
        subs = model_sexpr.subtrees
        if r == 'model':
            for s in subs: self(s)
        elif r == 'declare-fun':
            name, args, ret = self._funprot(subs)
            self.funcs[name.root] = (args, ret, lambda: name.root)
        elif r == 'define-fun':
            (name, args, ret), (body,) = self._funprot(subs[:3]), subs[3:]
            argnames = [a.root for a in args]
            f = lambda *a: self._eval(body, dict(zip(argnames, a)))
            self.funcs[name.root] = (args, ret, f)
    
    def _funprot(self, prot_sexprs):
        assert len(prot_sexprs) == 3
        name, args, ret = prot_sexprs
        if name.subtrees:
            raise ValueError, "expected function identifier, found '%s'" % (name,)
        args = tuple(args.subtrees)
        return name, args, ret
    
    def _eval(self, sexpr, valuation={}):
        r = sexpr.root
        subs = sexpr.subtrees
        if r == 'let':
            return self._eval_let(subs[:-1], subs[-1], valuation)
        elif not subs:
            try:
                return valuation[r]
            except KeyError:
                pass
        try:
            body = self.STANDARD_INTERPRETATION[r]
        except KeyError:
            try:
                _, _, body = self.funcs[r]
            except KeyError:
                return r
        
        args = tuple(self._eval(s, valuation) for s in subs)
        return body(*args)
    
    def _eval_let(self, assignments, expr, valuation):
        """
        Evaluates an expression of the form:
          (let ((v1 (term1)) (v2 (term2))) expr)
        """
        kv = valuation.copy()
        for a in assignments:
            for el in a.subtrees:
                if len(el.subtrees) != 1:
                    raise ValueError, "invalid let: '%s' (at '%s')" % (a, el)
                lhs, rhs = el.root, el.subtrees[0]
                kv[lhs] = self._eval(rhs, valuation)
        return self._eval(expr, kv)

    def signature(self):
        """
        Extracts a first-order sorted signature describing the type of
        the structure.
        """
        sorts = FolSorts()
        for name, (args, ret, _) in self.funcs.iteritems():
            # ~ symbols with '!' are reserved for compiler-generated aux
            if not "!" in name: 
                nameid = Identifier(name, '?') # 'kind' will be filled by FolManySortSignature
                argtypes = [Identifier(a.subtrees[0].root, 'sort') for a in args]
                rettype = Identifier(ret.root, 'sort')
                if rettype == 'bool': rettype = ''
                sorts[nameid] = [FolSorts.FunctionType(argtypes, rettype)]
        return FolManySortSignature.from_sorts(sorts)
    
    def as_structure(self):
        """
        Turns me into a logical structure.
        @see logic.fol.semantics.structure.FolStructure
        """
        # TODO replace "V" with sorts according to available ones
        vals = sorted([v for v in self.funcs if v.startswith("V!")])

        sigma = self.signature()
        I = {}
        
        for name, arity in sigma.funcs + sigma.preds:
            r = self.funcs[name][-1]
            if arity == 0:  # constant
                I[name] = r()
            else:
                I[name] = r
                
        return FolStructure(domain=vals, interpretation=I) 



class SmtLib2OutputFormat(object):
    
    def __init__(self):
        self.parser = SExpressionParser()
        self.pm = ProcessModel()
        self.naming = NamingConvention()
        
    def __call__(self, output_text):
        d = self.Document(self)
        d.expressions = self.parser(output_text)
        return d
        
    def _expr_to_model(self, expr):
        pm = copy.deepcopy(self.pm)
        pm(expr)
        
        s = pm.signature()
        m = pm.as_structure()
        # Now unescape the names
        def unescape_identifier(s):
            return Identifier(self.naming.unescape(s.literal), s.kind, s.ns)
        m.interpretation = {unescape_identifier(k): v
                            for k,v in m.interpretation.iteritems()}
        return self.Document.ModelItem(signature=s, structure=m)
        
    class Document(oop.InnerClasses.Owned):
    
        class Item(object): pass
        class ModelItem(Item, namedtuple("ModelItem", "signature structure")): pass
        class DecisionItem(Item, namedtuple("DecisionItem", "decision")): pass
        class MessageItem(Item, namedtuple("MessageItem", "level msg")): pass

        def __init__(self, owner):
            super(SmtLib2OutputFormat.Document, self).__init__(owner)
            self.expressions = []
    
        def itermodels(self):
            return (self.o._expr_to_model(expr) for expr in self.expressions
                    if expr.root == 'model')
        
        def __iter__(self):
            for e in self.expressions:
                if e.root in ['sat', 'unsat', 'unknown']:
                    yield self.DecisionItem(decision=e.root)
                elif e.root == 'model':
                    yield self.o._expr_to_model(e)
                elif e.root == 'error':
                    yield self.MessageItem(level=e.root, 
                                           msg=' '.join(x.root for x in e.subtrees))
                else:
                    yield e



if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "/tmp/reverse.out"

    text = open(filename, "r").read()

    parser = SExpressionParser()
    tsp = parser(text)

    try:
        model_expr = [x for x in tsp if x.root == 'model'][0]
    except IndexError:
        raise ValueError, "input contains no model"

    print tsp
    pm = ProcessModel()
    pm(model_expr)
    import pprint
    pprint.pprint( pm.funcs )
    
    # unescape
    pm.funcs = {k.replace("@", "'"): v for k,v in pm.funcs.iteritems()}
    
    for symbol in ['i', "i'", 'j', 'x', 'y']:
        if symbol in pm.funcs:
            print "%s = %s" % (symbol, pm.funcs[symbol][-1]())

    def custom_partial_order(a, b):
        pl = ['n', 'n*', 'n+', 'n@', 'n*@', 'n+@']
        try:
            ai, bi = pl.index(a), pl.index(b)
        except ValueError:
            return cmp(a, b)
        return cmp(ai, bi)
    
    sigma = pm.signature()
    m = pm.as_structure()
    
    tables = [(p, m.binary_relation_as_table(p))
              for p, arity in sigma.preds if arity == 2]
    for p, t in sorted(tables, cmp=custom_partial_order, key=lambda t: t[0]):
        print t
        
    g = AlgebraicStructureGraphTool(m, ['n*'])() 
    print g.edges

    from adt.graph.visual.graphviz import GraphvizGraphLayout
    ggl = GraphvizGraphLayout()
    ggl.auto_open = False
    ggl(g)