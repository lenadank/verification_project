# encoding=utf-8
from adt.tree import Tree
from logic.fol.syntax.theory import FolTheory
from logic.fol.syntax import Identifier
from logic.fol.syntax.formula import FolFormula, FolSignature
from logic.fol.semantics.extensions.arith import FolIntegerArithmetic
from logic.fol.semantics.extensions.po import FolNaturalPartialOrder
from logic.fol.semantics.extensions.equality import FolWithEquality
from adt.tree.transform.apply import ApplyTo



class LexerRules(object):
    
    class opAssoc:
        LEFT = 'left'
        RIGHT = 'right'
    
    STANDARD_ARITH = [
        ("*", 2, opAssoc.LEFT),
        ("/", 2, opAssoc.LEFT),
        ("+", 2, opAssoc.LEFT),
        ("-", 2, opAssoc.LEFT),
        ("-", 1, opAssoc.RIGHT),
        ]
    
    STANDARD_COMPARE = [
        ("=", 2, opAssoc.LEFT),
        (("!=", FolWithEquality.neq), 2, opAssoc.LEFT),
        (("<=", FolNaturalPartialOrder.le), 2, opAssoc.LEFT),
        ("<", 2, opAssoc.LEFT),
        ((">=", FolNaturalPartialOrder.ge), 2, opAssoc.LEFT),
        (">", 2, opAssoc.LEFT),
        ]
    
    PROP_LOGIC = [
        (("~", FolFormula.NOT), 1, opAssoc.RIGHT),
        (("&", FolFormula.AND), 2, opAssoc.LEFT),
        (("|", FolFormula.OR), 2, opAssoc.LEFT),
        (("<->", FolFormula.IFF), 2, opAssoc.RIGHT),
        (("->", FolFormula.IMPLIES), 2, opAssoc.RIGHT),
        ]
    
    STATEMENTS = [
        (":", 2, opAssoc.RIGHT),
        ]
    
    OPERATORS = STANDARD_ARITH + STANDARD_COMPARE + PROP_LOGIC + STATEMENTS

    QUANTIFIERS = ['forall', 'exists',
                   FolFormula.FORALL, FolFormula.EXISTS]

    tokens = (
        'NUMBER',
        'QUANTIFIER',
        'IDENTIFIER',
        'ESCAPED_SYMBOL',
        'TAG', 'FUNCTION_TAG',
        'LPAREN', 'RPAREN',
        'COMMA',
    )# + tuple('OP%d' % i for i in xrange(len(OPERATORS)))
    
    t_QUANTIFIER = u'forall|exists|%s|%s' % (FolFormula.FORALL, FolFormula.EXISTS)
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_COMMA = r','
    t_FUNCTION_TAG = r'`'
    t_ignore = ' \t\r\n'

    def t_IDENTIFIER(self, t):
        r'[a-zA-Z_][a-zA-Z0-9_]*'
        if t.value in self.QUANTIFIERS:
            t.type = 'QUANTIFIER'
        return t
    
    def t_NUMBER(self, t):
        r'[0-9]+(\.[0-9]+)?'
        if '.' in t.value:
            t.value = float(t.value)
        else:
            t.value = int(t.value)
        return t
        
    def t_ESCAPED_SYMBOL(self, t):
        r'\[ [^[\]]* \]  |  \[\[ [^\]]*(\][^\]]+)*  \]\]'
                     #           \-------v-------/
                     # this is like:    .*?
        if t.value.startswith("[["):
            t.value = t.value[2:-2]
        else:
            t.value = t.value[1:-1]
        return t
        
    def t_TAG(self, t):
        r'{[^}]*}'
        t.value = t.value[1:-1]
        return t
                
    def __init__(self):
        ops = set(); opnames = []
        for i, (op, _, _) in enumerate(self.OPERATORS):
            if op not in ops:
                opnames += ["OP%d" % i]
                setattr(self, 't_OP%d' % i, self._op_regexp(op))
                ops.add(op)
        self.tokens = self.tokens + tuple(opnames)
    
    def _op_regexp(self, op):
        if not isinstance(op, tuple): op = (op,)
        return '|'.join(re.escape(unicode(x)) for x in op)
    
    def t_error(self,t):
        raise SyntaxError, u"Illegal character '%s' at %d:%d" % (t.value[0],t.lineno,t.lexpos)
    
    
    
class ParserRules(object):
    
    LexerRules = LexerRules
    OPERATORS = LexerRules.OPERATORS
    
    def __init__(self):
        self.tokens = self.LexerRules().tokens
        def opnum(op):
            for i, (op0,_,_) in enumerate(self.OPERATORS):
                if op0 == op: return i
            assert False
        # @@ global -- not thread-safe, and stuff
        self.p_infix_expr.im_func.__doc__ = \
            "atom : " + "\n| " .join(("atom OP%d atom" % i if arity == 2 else "OP%d atom"  %i)
                                     for op,arity,_ in self.OPERATORS for i in [opnum(op)])
        self.precedence = tuple((assoc, 'OP%d' % i) 
                           for i, (_,_,assoc) in reversed(list(enumerate(self.OPERATORS)))
                           if 'OP%d' % i in self.tokens)
        
    def p_leaf(self, p):
        """atom : NUMBER
                | IDENTIFIER
                | ESCAPED_SYMBOL
        """
        p[0] = Tree(p[1])
    
    def p_tagged_leaf(self, p):
        """atom : TAG IDENTIFIER
                | TAG ESCAPED_SYMBOL
        """
        p[0] = Tree(Identifier.promote(p[2], kind=p[1]))

    def p_tagged_func_leaf(self, p):
        """atom : FUNCTION_TAG IDENTIFIER
                | FUNCTION_TAG ESCAPED_SYMBOL
        """
        p[0] = Tree(Identifier.promote(p[2], kind='function'))
    
    def p_node(self, p):
        """atom : IDENTIFIER LPAREN comma_sep_list RPAREN
                | ESCAPED_SYMBOL LPAREN comma_sep_list RPAREN
        """
        p[0] = Tree(p[1], p[3])
        
    def p_comma_sep_list(self, p):
        """
        comma_sep_list : atom
                       | atom COMMA comma_sep_list
        """
        p[0] = [p[1]] + (p[3] if len(p)>3 else [])
        
    def p_infix_expr(self, p):
        """
        atom : atom binary-operator atom
             | unary-operator atom
         (see __init__)
        """
        if len(p) == 4:
            p[0] = Tree(p[2], [p[1], p[3]])
        else:
            p[0] = Tree(p[1], [p[2]])

    def p_parenthesized_expr(self, p):
        """
        atom : LPAREN atom RPAREN
        """
        p[0] = p[2]
        
    def p_special_form_quantified_expr(self, p):
        """
        atom : QUANTIFIER symbol_list LPAREN atom RPAREN
        """
        p[0] = Tree(p[1], [Tree(x) for x in p[2]] + [p[4]])
    
    def p_symbol(self, p):
        """
        symbol : IDENTIFIER
               | ESCAPED_SYMBOL
        """
        p[0] = p[1]
    
    def p_symbol_list(self, p):
        """
        symbol_list : symbol
                    | symbol symbol_list
        """
        p[0] = [p[1]] + (p[2] if len(p)>2 else [])
        
    def p_error(self, p):
        raise SyntaxError, p
    
    
    
import re
from ply import lex, yacc


class FolFormulaParser(object):
    
    OPERATORS = ParserRules.OPERATORS
    
    OPERATOR_MAP = {'~':  FolFormula.NOT,     FolFormula.NOT: FolFormula.NOT,
         '&':  FolFormula.AND,                FolFormula.AND: FolFormula.AND,
         '|':  FolFormula.OR,                 FolFormula.OR: FolFormula.OR,
         '->': FolFormula.IMPLIES,            FolFormula.IMPLIES: FolFormula.IMPLIES,
         '<->': FolFormula.IFF,               FolFormula.IFF: FolFormula.IFF,
         'forall': FolFormula.FORALL,         FolFormula.FORALL: FolFormula.FORALL,
         'exists': FolFormula.EXISTS,         FolFormula.EXISTS: FolFormula.EXISTS,
         '=': FolWithEquality.eq,
         '!=': FolWithEquality.neq,           FolWithEquality.neq: FolWithEquality.neq,
         '*': FolIntegerArithmetic.mul, 
         ('-',2): FolIntegerArithmetic.sub,
         ('-',1): FolIntegerArithmetic.neg,
         '<=': FolNaturalPartialOrder.le,     FolNaturalPartialOrder.le: FolNaturalPartialOrder.le,
         '>=': FolNaturalPartialOrder.ge,     FolNaturalPartialOrder.ge: FolNaturalPartialOrder.ge}

    LexerRules, ParserRules = LexerRules, ParserRules
    ParseError = SyntaxError
    
    def __init__(self, operators=OPERATORS):
        self.native_types = (int, float)
        self.signatures = []
        rules = ((self.LexerRules, self.ParserRules) 
                 if operators is FolFormulaParser.OPERATORS
                 else self._override_operators(operators))
        self._create_ply_objects(rules)

    def _override_operators(self, operators):
        class LexerRulesExtra(self.LexerRules):
            OPERATORS = operators
        class ParserRulesExtra(self.ParserRules):
            LexerRules = LexerRulesExtra
            OPERATORS = operators
        return LexerRulesExtra, ParserRulesExtra
        
    def _create_ply_objects(self, (LexerRules, ParserRules)):
        self.lexer = lex.lex(module=LexerRules(), reflags=re.UNICODE)
        self.parser = yacc.yacc(module=ParserRules(), write_tables=0, debug=0)
        
    def parse_tree(self, text):
        try:
            return self.parser.parse(text, lexer=self.lexer)
        except SyntaxError, e:
            raise SyntaxError, u"in '%s': unexpected %s" % (text, e or "end of input")

    # Logic-related functionality

    def __call__(self, text, signatures=None):
        if signatures is not None: self.signatures = signatures
        tree = self.parse_tree(text)
        for node in tree.nodes:
            node.root = self._ident(node.root, len(node.subtrees))
        return self._spread_quantifiers(self._to_formula(tree))

    def __mul__(self, representation_form):
        r = representation_form
        if isinstance(r, list):
            return FolTheory(self(phi) for phi in r).with_signature(self._combined_signatures())
        else:
            return self(r)

    def lookup(self, literal):
        for sig in self.signatures:
            for symbol in sig.itersymbols():
                if symbol == literal or \
                        isinstance(symbol, Identifier) and \
                        symbol.mnemonic == literal:
                    return symbol
        else:
            return Identifier.promote(literal)

    def unparse(self, formula):
        """Re-formats 'formula' as text that this parser can later parse.
        @formula an FolFormula instance
        """
        idre = re.compile(self.LexerRules.t_IDENTIFIER.__doc__ + "$")
        def escaping(t):
            if t not in FolFormula.INFIXES and t not in [FolFormula.FORALL, FolFormula.EXISTS, FolFormula.NOT]:
                if not (isinstance(t, Identifier) and isinstance(t.literal, (int, float))):
                    u = unicode(t)
                    if not idre.match(u):
                        t = Identifier(u'[%s]' % u, '?')
            return t
        return unicode(ApplyTo(nodes=escaping).asnew(formula))

    def _ident(self, tok, arity):
        """ Creates an identifier from a given token. """
        if isinstance(tok, Identifier):
            return tok
        elif any(isinstance(tok, t) for t in self.native_types):
            return Identifier(tok, 'function')
        try:
            return self.OPERATOR_MAP[tok]
        except KeyError:
            try:
                return self.OPERATOR_MAP[(tok, arity)]
            except KeyError:
                return self.lookup(tok)

    def _to_formula(self, tree):
        _ = self._spread_quantifiers
        return _(FolFormula(tree.root, 
                            [self._to_formula(s) for s in tree.subtrees]))
        
    def _spread_quantifiers(self, formula):
        while isinstance(formula.root, Identifier) and \
              formula.root.kind == 'quantifier' and len(formula.subtrees) > 2:
            r, s = formula.root, formula.subtrees
            formula = type(formula)(r, s[:-2] + [type(formula)(r, s[-2:])])
        return formula
        
    def _combined_signatures(self):
        if self.signatures:
            return reduce(lambda x,y: x|y, self.signatures)
        else:
            return FolSignature() # empty signature :(
        

    
if __name__ == '__main__':
    l = lex.lex(module=LexerRules(), reflags=re.UNICODE)
    l.input(u'a(b,c)[§]+')
    while 1:
        tok = l.token()
        if not tok: break
        print tok    
        
    M = FolFormulaParser()
#    l = lex.lex(module=LexerRules(), reflags=re.UNICODE)
#    p = yacc.yacc(module=ParserRules(), write_tables=0, debug=1)
#    print p.parse("a(1,a(2) + 9 & ~b)", lexer=l)
    print M("forall i ([∃](j, a(1,a(j) + 9)) & ~b)")
    print M("-1")
    print M.unparse(M("forall i ([∃](j, a(1,a(j) + 9)) & ~b)"))
    
