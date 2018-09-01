
import copy

from adt.tree.transform import TreeTransform
from adt.tree.transform.substitute import TreeSubstitution
from logic.fol import Identifier, FolFormula
from adt.tree.transform.apply import ApplyTo, TreeNodeRename



class AuxTransformers(object):
    """
    Yeah, this class sucks.
    
    Used by: mainly the SmtLib2InputFormat class, but also the While language frontend.
    """
    
    @classmethod
    def fold(cls, t, symbols=[FolFormula.FORALL, FolFormula.AND]):
        """
        Transforms e.g. and(x,and(u,v)) to and(x,u,v)
        """
        r, s = t.root, t.subtrees
        if s:
            if r in symbols:
                def folded_form():
                    for x in s:
                        if x.root == r:
                            for y in x.subtrees: yield y
                        else:
                            yield x
                s = list(folded_form())
                return type(t)(r, s)
    
    @classmethod
    def unfold(cls, t, symbols={FolFormula.AND: 2}):
        """
        Opposite of fold(t), normalizes the dictated symbols to their
        respective arity by repeating the operator.
        E.g. and(x,y,z) ---> and(x,and(y,z)) 
        """
        r, s = t.root, t.subtrees
        if s and r in symbols:
            arity = symbols[r]
            if len(s) > arity:
                return type(t)(r, [s[0], type(t)(r, s[1:])])
            elif arity > 1 and len(s) == 1:
                return s[0]
    
    @classmethod
    def regroup(cls, t, head, tag):
        r, s = t.root, t.subtrees
        if r == head:
            s_tag = []
            for x in s:
                if s_tag and s_tag[-1].root == tag and x.root == tag:
                    s_tag[-1].subtrees += x.subtrees
                else:
                    s_tag += [copy.copy(x)]
            return type(t)(r, s_tag)

    @classmethod
    def flatten(cls, t, vec_tag='$'):
        """
        e.g. f(a, $(b,c), d) ---> f(a, b, c, d)
        """
        def xform(t):
            if any(s for s in t.subtrees if s.root == vec_tag):
                def flat_form():
                    for x in t.subtrees:
                        if x.root == vec_tag:
                            for y in x.subtrees: yield y
                        else:
                            yield x
                return type(t)(t.root, list(flat_form()))
        return TreeTransform([xform], dir=TreeTransform.BOTTOM_UP)(t)

    @classmethod
    def get_all_bound_vars(cls, t):
        varset = set()
        for n in t.nodes:
            if isinstance(n.root, Identifier) and n.root.kind == 'quantifier':
                varset.add(n.subtrees[0].root)
        return varset
    
    @classmethod
    def renumber_bound_vars(cls, t):
        """
        Makes sure any two bound variable identifiers that are not equal (not __eq__(x,y))
        have distinct literals. Note: performs modification in-place.
        """
        def gen_vars():
            i = 0
            while True:
                yield Identifier('$%d' % i, 'variable')
                i += 1
        varset = cls.get_all_bound_vars(t)
        vardict = dict(zip(varset, gen_vars()))  # :)
        return TreeNodeRename(vardict).inplace(t)
    
    @classmethod
    def quote_strings(cls, t):
        def xform(t):
            if t.root == '"':
                return type(t)(u'"%s"' % ''.join(unicode(x) for x in t.subtrees))
        return TreeTransform([xform])(t)
            