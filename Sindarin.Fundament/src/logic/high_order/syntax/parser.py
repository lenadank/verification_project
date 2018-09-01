"""
This module presents a parser for functional-programming style terms and
formulas, modeled after Gallina (the language for functional terms used by
Coq).
"""
from adt.tree import Tree
from logic.fol.syntax.parser import LexerRules



class FPLexerRules(LexerRules):
    
    OPERATORS = [(':', 2, LexerRules.opAssoc.LEFT),
                 ('->', 2, LexerRules.opAssoc.RIGHT),
                 ('=>', 2, LexerRules.opAssoc.RIGHT)]
    
    QUANTIFIERS = ['forall', 'fun']
    
    
    
    
class FPParserRules(object):
    
    LexerRules = FPLexerRules
    OPERATORS = LexerRules.OPERATORS
    
    def __init__(self):
        self.tokens = self.LexerRules().tokens
        def opnum(op):
            for i, (op0,_,_) in enumerate(self.OPERATORS):
                if op0 == op: return i
            assert False
        # @@ global -- not thread-safe, and stuff
        self.p_infix_expr.im_func.__doc__ = \
            "term : " + "\n| " .join(("term OP%d term" % i if arity == 2 else "OP%d term"  %i)
                                     for op,arity,_ in self.OPERATORS for i in [opnum(op)])
        self.precedence = tuple((assoc, 'OP%d' % i) 
                           for i, (_,_,assoc) in reversed(list(enumerate(self.OPERATORS)))
                           if 'OP%d' % i in self.tokens)

    def p_abstraction(self, p):
        """
        term : QUANTIFIER term
        """
        p[0] = Tree(p[1], [p[2]])

    def p_abstraction1(self, p):
        """
        term : QUANTIFIER term COMMA term
        """
        p[0] = Tree(p[1], [p[2], p[4]])

    def p_name(self, p):
        """
        aterm : IDENTIFIER
              | NUMBER
              | ESCAPED_SYMBOL
        """
        p[0] = Tree(p[1])

    def p_application(self, p):
        """
        aterm : aterm aterm
        """
        f, a = p[1], p[2]
        if not f.subtrees: f = f.root
        p[0] = Tree(f, [a])

    def p_term(self, p):
        """
        term : aterm
        """
        p[0] = p[1]

    def p_aterm_parens(self, p):
        """
        aterm : LPAREN term RPAREN
        """
        p[0] = p[2]

    def p_infix_expr(self, p):
        """
        term : term OP1 term
        """
        if len(p) == 4:
            p[0] = Tree(p[2], [p[1], p[3]])
        else:
            p[0] = Tree(p[1], [p[2]])


    def p_error(self, p):
        raise SyntaxError, p
    


import re
from ply import lex, yacc


class FPTermParser(object):

    LexerRules, ParserRules = FPLexerRules, FPParserRules
    ParseError = SyntaxError
    
    def __init__(self):
        rules = (self.LexerRules, self.ParserRules)
        self._create_ply_objects(rules)
        
    def _create_ply_objects(self, (LexerRules, ParserRules)):
        self.lexer = lex.lex(module=LexerRules(), reflags=re.UNICODE)
        self.parser = yacc.yacc(module=ParserRules(), write_tables=0, debug=0)
        
    def parse_tree(self, text):
        try:
            return self.parser.parse(text, lexer=self.lexer)
        except SyntaxError, e:
            raise SyntaxError, u"in '%s': unexpected %s" % (text, e or "end of input")



if __name__ == '__main__':
    text = '(fun (x -> f y -> a) : h j => [g-h] -> i) -> kjh'
    text = 'forall (x:u) (y:z), u'
    
    L = FPTermParser()
    
    print L.parse_tree(text)
    
    