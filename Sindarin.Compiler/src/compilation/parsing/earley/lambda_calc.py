'''
Example for using Earley for simple untyped lambda calculus.
'''
from Earley import Earley, PrintTrees
from adt.tree.transform.substitute import TreeSubstitution
from adt.tree.transform import TreeTransform
from compilation.parsing import Tagged




class LambdaParser(object):

    nlG = [("S", "Abs"),
           ("S", "App"),
           ("S", "id"),
            ("Abs", "lambda", "id", "S"),
            ("App", "S", "S"),
           ("S", "(", "S", ")")
           ]
    lG = [("id", "v"), ("id", "w"), ("id", "x"), ("id", "y"), ("id", "z"),
          ("lambda", "\\"), ("(", "("), (")", ")")]


    def __init__(self):
        self.lexer = lambda x: x
        
    @classmethod
    def _rightmost(cls, t, consider=["App", "Abs"]):
        if t.subtrees:
            j = cls._rightmost(t.subtrees[-1], consider)
        else:
            j = None
            
        if j is None:
            return t.root if t.root in consider else None
        else:
            return j
    
    @classmethod
    def valid(cls, t):
        return not any(n.root == 'App' and cls._rightmost(n.subtrees[0]) == 'Abs'
                       for n in t.nodes)
        
    def simplify(self, t):
        def transform(t):
            r, arity, s = t.root, len(t.subtrees), t.subtrees
            h = None
            if r == 'S' and arity == 1:
                h = s[0]
            #elif r == 'id' and arity == 1:
            #    h = s[0]
            elif r == 'Abs' and arity == 3:
                h = type(t)(r, s[1:])
            elif r == 'S' and arity == 3 and s[0].root == '(' and s[2].root == ')':
                h = s[1]
            elif isinstance(r, Tagged) and hasattr(r, 'token'):
                h = type(t)(r.token)
                
            if h is not None:
                return recurse(h)
            
        recurse = TreeTransform([transform])
        return recurse(t)
            
        
    def __call__(self, expr_text):
        e = Earley(self.nlG, self.lG, expr_text, lexer=self.lexer)
        return [self.simplify(t) for t in e if self.valid(t)]



class LambdaInterpreter(object):
    
    def _substitute(self, body, variable, value):
        return TreeSubstitution({variable: value})(body)

    def beta_reduce(self, func, arg):
        assert func.root == 'Abs' and len(func.subtrees) == 2
        param, body = func.subtrees
        return self._substitute(body, param, arg)

    def is_value(self, term):
        return term.root == 'Abs'

    def e_absapp(self, expr):
        is_value = self.is_value
        beta_reduce = self.beta_reduce

        class Transformer(object):
            def __init__(self):
                self.stop = False
            def __call__(self, t):
                if not self.stop and t.root == 'App' and \
                   all(is_value(x) for x in t.subtrees):
                    assert len(t.subtrees) == 2
                    self.stop = True
                    func, arg = t.subtrees
                    return beta_reduce(func, arg)
                
        return TreeTransform([Transformer()])(expr)



if __name__ == '__main__':
    
    inputs = ["\\ v v w".split(),
              "( \\ v \\ x v ) \\ v v w".split()]
    
    inputs += [["\\", Tagged("v").with_(token="tru"), 
                      Tagged("v").with_(token="tru")]]
    
    parser = LambdaParser()
    interp = LambdaInterpreter()
    
    for expr in inputs:
        print ">> %s <<" % expr
        e = parser(expr)
        PrintTrees(e)
        
        if e:
            print interp.e_absapp(e[0])
    
        