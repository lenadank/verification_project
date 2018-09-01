
import new #@UnresolvedImport
import copy

from adt.tree.search.pattern import TreeTopPattern
from adt.tree.transform.substitute import TreeSubstitution,\
    TreePatternSubstitution

from pattern.collection.basics import OrderedSet

from logic.fol import Identifier

from modifiers import CompositeIdentifier
from formula import FolFormula, FolSymbolic



class FolScheme(object):
    
    BY_ROLE = 'by-role'
    
    class Placeholder(Identifier):
        tags = ['placeholder']
    
    def __init__(self, formula, placeholders='?'):
        self.formula = formula
        if placeholders is self.BY_ROLE:
            self.placeholders = self._auto_placeholders_by_role(formula)
        elif isinstance(placeholders, (str,unicode)):
            self.placeholders = \
                self._auto_placeholders_by_prefix(formula, placeholders)
        else:
            self.placeholders = placeholders
        self._pattern = None
        
    def __repr__(self):
        return "%r{%r}" % (self.formula, self.placeholders)
        
    def __call__(self, *fillin):
        if len(fillin) != len(self.placeholders):
            raise TypeError, "expecting %d expressions, got %d" % (len(self.placeholders), len(fillin))

        s = FolSubstitution(dict((placeholder, filler)
                                  for placeholder, filler
                                  in map(None, self.placeholders, fillin)))
            
        return s(self.formula)
    
    def fill_partial(self, fillin_dict):
        formula = FolSubstitution(fillin_dict)(self.formula)
        placeholders = [p for p in self.placeholders
                        if p not in fillin_dict and 
                        FolFormula(p) not in fillin_dict]
        return FolScheme(formula, placeholders)
    
    def _get_pattern(self):
        return self._pattern or FolPattern(self.formula)
    
    def _set_pattern(self, pattern):
        """allows one to override 'pattern' with something else."""
        self._pattern = pattern
        
    pattern = property(_get_pattern, _set_pattern)

    def _auto_placeholders_by_prefix(self, formula, prefix="?"):
        ph = OrderedSet()
        for symbol in formula.terminals:
            if (isinstance(symbol, Identifier) and 
                    isinstance(symbol.literal, (str,unicode)) and
                    symbol.literal.startswith(prefix) and
                    symbol.literal != prefix):
                symbol.tags = symbol.tags + ["placeholder"]  # note: may be shared; thus copy
                symbol.kind = 'term' 
                ph.add(symbol)
        return list(ph)
    
    def _auto_placeholders_by_role(self, formula, leaf_q=["?"], any_q=["variable"]):
        """
        Employs the following rules to choose which symbols will act as placeholders:
        - identifiers with kind=="?" occurring in leaf nodes (unknown) are placeholders
        - any identifier with kind=="variable" is a placeholder
        - other identifiers are literal symbols (not placeholders).
        """
        ph = [n.root for n in formula.nodes
                if isinstance(n.root, Identifier) and
                    (n.root.kind in any_q or not n.subtrees and n.root.kind in leaf_q)]
        def tag_ph(k):
            if not isinstance(k, self.Placeholder):
                k = self.Placeholder(k.literal, 'term' if k.kind == '?' else k.kind)
            return k
        TreeSubstitution({k: tag_ph(k) for k in ph}).inplace(formula)
        return ph



class FolPattern(TreeTopPattern):

    class IdentifierMatch(object):
        def __call__(self, pattern, text):
            IS = CompositeIdentifier.InternalStructure
            if isinstance(pattern, Identifier) and isinstance(text, Identifier) and \
               isinstance(pattern.literal, IS) and isinstance(text.literal, IS):
                return self._normalize(FolPattern(pattern.literal).match(text.literal))
            elif pattern == text:
                return FolPattern.MatchObject(text, {})
            else:
                return None
        def _normalize(self, mo):
            """
            Makes sure CompositeIdentifier.InternalStructure trees never appear
            naked, but wrapped inside a CompositeIdentifier.
            """
            if mo is not None:
                updates = [(k, CompositeIdentifier(v, None))
                           for k,v in mo.groups.iteritems()
                           if isinstance(v, CompositeIdentifier.InternalStructure)]
                mo.groups.update(updates)
            return mo

    def _is_node_placeholder(self, iden):
        if not isinstance(iden, Identifier): return False
        return "placeholder" in getattr(iden, 'tags', []) and \
            iden.kind in ["function", "predicate", "variable"]

    def _is_subtree_placeholder(self, iden):
        if not isinstance(iden, Identifier): return False
        return "placeholder" in getattr(iden, 'tags', []) and \
            iden.kind in ["formula", "term"]

    def _is_subtrees_placeholder(self, iden):
        if not isinstance(iden, Identifier): return False
        return "vector" in iden.tags

    scalar_match = IdentifierMatch()


class FolSubstitution(TreeSubstitution):
    
    def scalar_transform(self, identifier):
        IS = CompositeIdentifier.InternalStructure
        if isinstance(identifier, Identifier) and \
           isinstance(identifier.literal, IS):
            new_literal = self(identifier.literal)
            if new_literal != identifier.literal:  # @@@ this is not the best way
                c = copy.copy(identifier)
                c.literal = new_literal.normalize()
                return c



class FolPatternSubstitution(TreePatternSubstitution):

    class Substitution(TreePatternSubstitution.Substitution):
        TreeSubstitution = FolSubstitution

    class SubstitutionChain(TreePatternSubstitution.SubstitutionChain, Substitution):
        pass

    class AugmentSubstitution(TreePatternSubstitution.AugmentSubstitution):
        pass
        

FolPatternSubstitution.Substitution.TreePatternSubstitution = FolPatternSubstitution
FolPatternSubstitution.AugmentSubstitution.TreePatternSubstitution = FolPatternSubstitution
        

class FolSymbolicExtension(FolSymbolic):
    """
    Extends FolSymbolic with functions for creating schemes.
    """
    
    def to_scheme(self):
        return FolScheme(self.to_formula(), [ph for ph in self.identifiers
                                             if "placeholder" in ph.tags])
        
    @classmethod
    def scheme(cls, lambda_expr, signature_vars={}):
        return cls.construct(lambda_expr, signature_vars).to_scheme()

    class LanguageExtension(FolSymbolic.Language):
        def scheme(self, expr):
            return self.FolSymbolic.scheme(expr, self.dict)
        def __pow__(self, expr):
            if isinstance(expr, list):
                return [self.scheme(el) for el in expr]
            else:
                return self.scheme(expr)


    @staticmethod
    def extend():
        for k,v in FolSymbolicExtension.__dict__.iteritems():
            if isinstance(v, classmethod) or isinstance(v, new.function):
                if k != 'extend':
                    setattr(FolSymbolic, k, v)
        for k,v in FolSymbolicExtension.LanguageExtension.__dict__.iteritems():
            if isinstance(v, classmethod) or isinstance(v, new.function):
                if k != 'extend':
                    setattr(FolSymbolic.Language, k, v)



FolSymbolicExtension.extend()
