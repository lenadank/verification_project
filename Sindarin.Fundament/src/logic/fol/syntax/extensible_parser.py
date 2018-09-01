# encoding=utf-8
'''
An extensible FOL formula parser using Earley allowing to easily add
production rules.
'''
import re
from ply import lex

from adt.tree.transform import TreeTransform
from logic.fol.syntax.formula import FolFormula
from logic.fol.syntax import Identifier
from logic.fol.syntax.parser import LexerRules

from compilation.parsing import Tagged
from compilation.parsing.earley.Earley import Earley, PrintTrees
from pattern.mixins.unicode import UnicodeMixIn



class Grammar(object):
    '''Context-free grammar.'''
    
    class Rule(tuple, UnicodeMixIn):
        def __new__(cls, head, body):
            return super(Grammar.Rule, cls).__new__(cls, (head,) + tuple(body))
        @property
        def head(self): return self[0]
        @property
        def body(self): return self[1:]
        def __unicode__(self):
            annot = "{%s}" % self.head.attrs_fmtd() if isinstance(self.head, Tagged) else ""
            return "%s -> %s   %s" % (self.head, " ".join(unicode(x) for x in self.body), annot)
    
    class GrammarError(SyntaxError):
        pass
    
    def __init__(self, string_representation):
        self.rules = self._parse_productions(string_representation)
        
    def _parse_productions(self, text):
        productions = filter(None, (x.strip() for x in text.splitlines()))
        def split_symbols(nonterminal, word):
            nonterminal, word = nonterminal.strip(), word.strip()
            mo = re.match(r"(.*)\s+\{([^{}]*)\}", word)
            if mo: 
                word, annotation = mo.groups()
                nonterminal = Tagged(nonterminal).with_(annotation=annotation)            
            symbols = tuple((x[1:] if x and x[0] == '`' else x)
                            for x in word.split())
            return self.Rule(nonterminal, symbols)
        def parse_one(prod):
            try:
                nonterminal, derivations = prod.split('->', 1)
            except ValueError:
                raise self.GrammarError, "production malformed: '%s'" % prod
            derivations = derivations.split(" | ")
            return [split_symbols(nonterminal, x) for x in derivations]
        
        return [rule for prod in productions for rule in parse_one(prod)]
            
    def __unicode__(self):
        return '\n'.join(unicode(rule) for rule in self.rules)



class ParserXforms(object):
    
    def split(self, t, sep):
        if t.root in sep:  return [el for x in t.subtrees for el in self.split(x, sep)]
        else:              return [t]
        
    def __call__(self, t):
        annot = getattr(t.root, 'annotation', None)
        if annot: return self.apply(t, annot)
        
    def apply(self, t, annot):
        meth = getattr(self, annot, None)
        if meth: return meth(t)
        else: return self.default(t, annot)
            
    def default(self, t, annot):
        return None



class FolExtensibleLexer(object):
    
    NATIVES = ['(', ')', '|', '&', '->', '~']

    def __init__(self):
        self.yy = lex.lex(module=LexerRules(), reflags=re.UNICODE)

    def tag(self, tok):
        if tok.value in self.NATIVES:
            return tok.value
        else:
            return tok.type
        
    def __call__(self, input_text):
        self.yy.input(input_text)
        return (Tagged(self.tag(tok)).with_(token=tok) for tok in self.yy)
        


if __name__ == '__main__':
    l = FolExtensibleLexer()
    
    sample = "forall u ((P(u) | ~P(u)) & Q | U)"
    sample = "A & forall u (C)"
    
    tokens = list(l(sample))

    #lexer = lambda tokens: 
    #tokens = [ for tok in tokens]
    
    FOL_GRAMMAR = Grammar("""
        S -> fml {sam}
        fml -> QUANTIFIER IDENTIFIER ( fml )  {qua}
        fml -> fml `| fml {bin}  |  fml1 {sam}
        fml0 -> fml1 & fml0  {bin}  |  fml1 {sam}
        fml1 -> IDENTIFIER {singl} | IDENTIFIER ( term* ) {cal} | ~ fml1 {un} | ( fml ) {sam1}
        term* -> | term+
        term+ -> fml | fml , term+
    """)
    
    #print unicode(FOL_GRAMMAR)
    
    for rule in FOL_GRAMMAR.rules:
        if rule.head == 'fml': print rule
    
    #raise SystemExit
    
    class TX(ParserXforms):
        PRIM = {'forall': FolFormula.FORALL, '|': FolFormula.OR, '&': FolFormula.AND, '~': FolFormula.NOT, '->': FolFormula.IMPLIES, '<->': FolFormula.IFF}
        for v in PRIM.values(): PRIM[v.literal] = v
        
        def singl(self, t):   return FolFormula(Identifier((t.subtrees[0] if t.subtrees else t).root.token.value, '?'))
        def qua(self, t):     return FolFormula(self.PRIM[t.subtrees[0].root.token.value], [self.singl(t.subtrees[1]), t.subtrees[3]])
        def cal(self, t):     return FolFormula(self.singl(t).root, self.split(t.subtrees[2], ('term*', 'term+', ',')))
        def bin(self, t):     return FolFormula(self.PRIM[t.subtrees[1].root.token.value], [t.subtrees[0], t.subtrees[2]])
        def un(self, t):      return FolFormula(self.PRIM[t.subtrees[0].root.token.value], [t.subtrees[1]])
        def sam(self, t):     return t.subtrees[0]
        def sam1(self, t):    return t.subtrees[1]
        
    
    lG = set((Tagged(tok).with_(annotation='sam'), tok) for tok in tokens)

    ast = Earley(FOL_GRAMMAR.rules, lG, tokens, lexer=lambda x: x)
    PrintTrees(ast)
    assert len(ast) == 1
    ast = FolFormula.reconstruct(ast[0])
    print ast
    phi = TreeTransform([TX()], dir=TreeTransform.BOTTOM_UP)(ast)

    print phi
