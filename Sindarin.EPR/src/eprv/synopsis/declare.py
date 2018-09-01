# encoding=utf-8
'''
Provides utilities to specify FO many-sorted signature declarations by 
using some syntactic structures.
'''

import copy
from logic.fol import Identifier, FolFormula
from logic.fol.semantics.extensions.arith import FolIntegerArithmetic
from logic.fol.semantics.extensions.sorts import FolSorts, FolManySortSignature
from logic.fol.syntax.theory import FolTheory



class TypeDeclarations(FolManySortSignature):
    
    COLON_SEP = [':']
    FUNC_SEP = [u"→", '->', FolFormula.IMPLIES]
    PARAM_SEP = [u"×", FolIntegerArithmetic.mul, "*"]
    EMPTY_MARKER = [FolFormula(Identifier("", '?'))]

    def to_sorts(self, phi):
        if not isinstance(phi, FolFormula) or phi.root not in self.COLON_SEP or len(phi.subtrees) != 2:
            raise ValueError, "expected a declaration, found '%s'" % phi
        name, typename = phi.subtrees
        if not name.subtrees:
            name = name.root
        else:
            raise ValueError, "expected atomic identifier, found '%s' (in declaration '%s')" % (name, phi)
        if typename.root in self.FUNC_SEP:
            if len(typename.subtrees) == 2:
                left, right = typename.subtrees
            else:
                raise ValueError, "invalid usage of '%s' (in declaration '%s')" % (self.FUNC_SEP[0], phi)
        else:
            left, right = self.EMPTY_MARKER, typename
        from_ = () if left == self.EMPTY_MARKER else map(self._typename,
                                                         left.split(self.PARAM_SEP))
        to_ = '' if right == self.EMPTY_MARKER or right.root == "bool" else self._typename(right)
        return FolSorts({name: FolSorts.FunctionType(from_, to_)})
    
    def _typename(self, term):
        if term.subtrees:
            raise NotImplementedError, "Non-atomic type '%s'" % term
        return term.root
    
    def is_declaration(self, phi):
        return isinstance(phi, FolFormula) and phi.root in self.COLON_SEP
    
    def read_from(self, formulas):
        if not isinstance(formulas, (list,set,tuple)): formulas = (formulas,)
        for phi in formulas:
            self |= self.from_sorts(self.to_sorts(phi))
        return self



class TypeInference(object):
    
    SPECIALTIES = [Identifier("ite", 'connective'),
                   Identifier("?:", 'macro')]
    
    def __init__(self):
        self.declarations = FolSorts()
        self.signature = FolManySortSignature(set(), set())
        self.special_symbols = {sym.literal: sym for sym in self.SPECIALTIES}
        
    def __call__(self, formula_or_formulas):
        if isinstance(formula_or_formulas, (tuple, list)):
            for phi in formula_or_formulas:
                self._formula(phi)
            if isinstance(formula_or_formulas, FolTheory):
                formula_or_formulas.signature |= self.signature
                formula_or_formulas.signature = formula_or_formulas.vocabulary
        else:
            self._formula(formula_or_formulas)
        return formula_or_formulas
    
    def _formula(self, phi, result_type='', bound_vars=set()):
        """
        (changes formula in-place, and also affects self.signature)
        """
        r, s, arity = phi.root, phi.subtrees, len(phi.subtrees)
        if isinstance(r, Identifier):
            if r.kind == '?' and r.literal in self.special_symbols:
                phi.root = r = self.special_symbols[r.literal]
            if r.kind == 'quantifier':
                v = self._variable(phi.subtrees[0])
                for expr in phi.subtrees[1:]: self._formula(expr, '', bound_vars | v)
                return ''
            elif r.kind == 'connective':
                for expr in phi.subtrees: self._formula(expr, '', bound_vars)
                return ''
            elif r == "?:":  # @@ hard-coded for now
                self._formula(s[0], '', bound_vars)
                term_types = [self._formula(x, '?', bound_vars) for x in s[1:]]
                if term_types and all(x == term_types[0] for x in term_types[1:]):
                    return term_types[0]
                else:
                    return '?'
            elif r in bound_vars:
                phi.root = [v for v in bound_vars if v == r][0]
                sort = self.declarations.ary(phi.root, 0)
                self._infer(phi, result_type)
                return sort[0].to_ if sort else ' '
            else:
                sort = self.declarations.ary(r, arity)
                if len(sort) == 1:
                    # matching declaration
                    subtypes = sort[0].from_
                    result_type = sort[0].to_
                else:
                    # undeclared or ambiguous
                    subtypes = (' ',) * arity
                # Try to assign a kind (predicate or function) to identifier
                if r.kind == '?':
                    if (r, arity) in self.signature.funcs:
                        cr = [s for s,a in self.signature.funcs if (s,a)==(r,arity)][0]
                    elif (r, arity) in self.signature.preds:
                        cr = [s for s,a in self.signature.preds if (s,a)==(r,arity)][0]
                    else:
                        cr = copy.copy(r)
                        # TODO somtimes this is 'bool' when it should be ''
                        if result_type == 'bool': result_type = ''
                        cr.kind = 'predicate' if result_type == '' else 'function'
                        if sort: self.signature.sorts[cr] = sort
                    if cr.kind == 'function':
                        self.signature.funcs.add((cr, arity))
                    else:
                        self.signature.preds.add((cr, arity))
                    phi.root = cr
                
                self._infer(phi, result_type)
                
                for expr, subtype in zip(phi.subtrees, subtypes):
                    self._formula(expr, subtype, bound_vars)
                return result_type
                    
    def _variable(self, variable_expr):
        if not variable_expr.subtrees:
            v = variable_expr.root
            if isinstance(v, Identifier) and v.kind == '?':
                cv = copy.copy(v)
                cv.kind = 'variable'
            else:
                cv = v
            sort = self.declarations.ary(cv, 0)
            if sort: self.signature.sorts[cv] = sort
            return set([cv])
                
        return set()
    
    def _infer(self, expr, expected_type):
        sorts = self.signature.sorts
        r = expr.root
        if expected_type not in [' ', '', '?'] and not expr.subtrees and r not in sorts:
            sorts[r] = [((), expected_type)]





if __name__ == '__main__':
    sample_decls = """
        x : V*V -> []
        """
    
    from logic.fol.syntax.parser import FolFormulaParser
    L = FolFormulaParser()
    FolFormula.INFIXES += [':']
    
    decls = [L * line
             for line in (x.strip() for x in sample_decls.splitlines())
                 if line]
    
    td = TypeDeclarations()
    
    for phi in decls:
        print u'§ ', phi
    
    print td.read_from(decls)
    
    