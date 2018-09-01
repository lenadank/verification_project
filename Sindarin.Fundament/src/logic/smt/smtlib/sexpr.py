'''
The S-Expression Data and Code Representation Format
'''

import math

from adt.tree import Tree
from logic.fol.syntax.formula import FolFormula
from pattern.mixins.unicode import UnicodeMixIn
# This functionality requires Sindarin.Compiler
from compilation.parsing.silly import SillyLexer, SillyBlocker



class SExpression(Tree, UnicodeMixIn):
    """
    Basically a function-call expression of the form
    (f arg0 arg1 ...)
    which may be nested.
    """
    
    def __init__(self, *a, **kw):
        """@see adt.tree.Tree.__init__ for prototype"""
        super(SExpression, self).__init__(*a, **kw)
        self.attributes = []
        
    def __unicode__(self):
        if isinstance(self.root, FolFormula.Identifier):
            r = self.root.mnemonic if self.root.mnemonic else self.root.literal
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
            r = unicode(r)
            
        if self.subtrees or self.attributes:
            return u"(%s%s%s)" % (r + " " if r else '',
                                   " ".join(unicode(s) for s in self.subtrees),
                                   "".join("\n"+unicode(s) for s in self.attributes))
        else:
            return r
    
    def __nonzero__(self):
        return not not (self.root or len(self.subtrees) or self.attributes)
 
 
 
 
class SExpressionParser(object):
    
    def __init__(self):
        self.lexer = l = SillyLexer(r"\(|\)|;;.*\n|'[^\n]*'(?=\n)")
        self.blocker = SillyBlocker((l.TOKEN, '('), (l.TOKEN, ')'))

    def filt(self, tokens):
        """ Filters out comments from the token stream produced by the 
        lexer """
        return (x for x in tokens if not x[1].startswith(';;')) # @@@ !
    
    def __call__(self, program_text):
        ast = self.blocker(self.filt(self.lexer(program_text)))
        return list(self.treeness(map(SExpression.reconstruct, ast)))

    @classmethod
    def treeness(cls, trees):
        for t in trees:
            tok = t.root
            if tok[1].strip():
                s = list(cls.treeness(t.subtrees))
                if s and not s[0].subtrees:
                    yield type(t)(s[0].root, s[1:])
                else:
                    if tok[1].startswith("'"):   # @@@ !
                        yield type(t)(tok[1])
                    else:
                        for word in tok[1].split():
                            yield type(t)(word, s)
                


if __name__ == '__main__':
    text = "(declare-fun V!val!2 () V)"
    text = "(assert (forall ((u V) (v V)) (=> (n u v) (n+ u v))))"
    text = """
(model 
  ;; universe for V:
  ;;   V!val!2 V!val!3 V!val!1 V!val!0 V!val!4 
  ;; -----------
  ;; definitions for universe elements:
  (declare-fun V!val!2 () V)
  (declare-fun V!val!3 () V)
  (declare-fun V!val!1 () V)
  (declare-fun V!val!0 () V)
  (declare-fun V!val!4 () V)
  ;; cardinality constraint:
  (forall ((x V))
          (or (= x V!val!2)
              (= x V!val!3)
              (= x V!val!1)
              (= x V!val!0)
              (= x V!val!4)))
  ;; -----------
  (define-fun i () V
    V!val!0)
  (define-fun i@ () V
    V!val!1)
  (define-fun j () V
    V!val!3)
  (define-fun y () V
    V!val!4)
  (define-fun x () V
    V!val!2)
  (define-fun n*!76 ((x!1 V) (x!2 V)) bool
    (ite (and (= x!1 V!val!0) (= x!2 V!val!1)) true
      false))
  (define-fun n+@!71 ((x!1 V) (x!2 V)) bool
    (ite (and (= x!1 V!val!2) (= x!2 V!val!3)) true
    (ite (and (= x!1 V!val!1) (= x!2 V!val!3)) true
      false)))
  (define-fun n@!74 ((x!1 V) (x!2 V)) bool
    (ite (and (= x!1 V!val!2) (= x!2 V!val!3)) true
      false))
  (define-fun n*@!75 ((x!1 V) (x!2 V)) bool
    (ite (and (= x!1 V!val!1) (= x!2 V!val!2)) true
    (ite (and (= x!1 V!val!2) (= x!2 V!val!3)) true
    (ite (and (= x!1 V!val!1) (= x!2 V!val!3)) true
      false))))
  (define-fun n+!73 ((x!1 V) (x!2 V)) bool
    (ite (and (= x!1 V!val!0) (= x!2 V!val!1)) true
      false))
  (define-fun k!69 ((x!1 V)) V
    (ite (= x!1 V!val!1) V!val!1
    (ite (= x!1 V!val!4) V!val!4
    (ite (= x!1 V!val!2) V!val!2
      V!val!0))))
  (define-fun n+ ((x!1 V) (x!2 V)) bool
    (n+!73 (k!69 x!1) (k!69 x!2)))
  (define-fun k!70 ((x!1 V)) V
    (ite (= x!1 V!val!3) V!val!3
    (ite (= x!1 V!val!4) V!val!4
    (ite (= x!1 V!val!2) V!val!2
      V!val!1))))
  (define-fun n@ ((x!1 V) (x!2 V)) bool
    (n@!74 (k!70 x!1) (k!70 x!2)))
  (define-fun n+@ ((x!1 V) (x!2 V)) bool
    (n+@!71 (k!70 x!1) (k!70 x!2)))
  (define-fun n*@ ((x!1 V) (x!2 V)) bool
    (n*@!75 (k!70 x!1) (k!70 x!2)))
  (define-fun n!72 ((x!1 V) (x!2 V)) bool
    (ite (and (= x!1 V!val!0) (= x!2 V!val!1)) true
      false))
  (define-fun n ((x!1 V) (x!2 V)) bool
    (n!72 (k!69 x!1) (k!69 x!2)))
  (define-fun n* ((x!1 V) (x!2 V)) bool
    (n*!76 (k!69 x!1) (k!69 x!2)))
)"""

    l = SillyLexer(r'\(|\)|;;.*\n')
    tokens = list(l(text))
    tokens = [x for x in tokens if not x[1].startswith(';;')] # @@@ !
    print tokens
    
    b = SillyBlocker((l.TOKEN, '('), (l.TOKEN, ')'))
    t = list(b(tokens))
    print t
    
    tsp = list(SExpressionParser.treeness(t))
    tsp = [t for t in tsp if t.root == 'model']
    assert len(tsp) == 1
    print tsp[0]
