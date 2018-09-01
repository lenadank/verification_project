# encoding=utf-8
from logic.fol import Identifier
from adt.tree.transform.substitute import TreeSubstitution
from logic.fol.syntax.formula import FolFormula, FolSignature



class FolSequenceOperations(object):

    class Signature:
        REDUCE_GLOB = Identifier(u"Я", "quantifier")
        formal = FolSignature()

    @classmethod
    def quantifier_semantics(cls, formula, domain_consts):
        """
        Given a list of domain constants, unwraps the quantifier to a long
        formula or term.
        E.g. Я[+]x (f(x))  --->  f(1)+f(2)+f(3)+f(4)
        """
        if formula.root == cls.Signature.REDUCE_GLOB:
            if len(formula.subtrees) != 3:
                raise ValueError, "%r requires exactly 3 arguments, in %r" % (formula.root, formula)
            op, v, expr = formula.subtrees
            if op.subtrees != [] or op.root.kind != 'function':
                raise TypeError, "expected a binary function symbol instead of %r, in %r" % (op, formula)
            qf = reduce(lambda x,y: FolFormula(op.root, [x,y]),
                        (TreeSubstitution({v: i})(expr) for i in domain_consts))
            return qf
            