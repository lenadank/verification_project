#encoding=utf-8
import re
from adt.tree import Tree
from adt.tree.transform import TreeTransform
from adt.tree.transform.apply import ApplyTo
from logic.fol import Identifier, FolFormula
from compilation.parsing.silly import SillyLexer, SillyBlocker
from logic.fol.syntax.transform import AuxTransformers
import functools



class WhileLexerRules(object):
    
    tokens = ('IDENTIFIER',
              'NULL',
              'OP_ASSIGN',
              'OP_PERIOD',
              'OP_SEMI',
              'OP_COMMA',
              'LPAREN', 'RPAREN',
              'LCURLY', 'RCURLY',
              'LBRACK', 'RBRACK',
              'FORMULA',
              'SKIP',
              'IF', 'THEN', 'ELSE', 'WHILE',
              'NEW',
              'ASSUME', 'ASSERT',
              'RETURN')
    
    t_OP_ASSIGN = r':='
    t_OP_PERIOD = r'[.]'
    t_OP_SEMI = r';'
    t_OP_COMMA = r','
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_LCURLY = r'\{'
    t_RCURLY = r'\}'
    t_LBRACK = r'\['
    t_RBRACK = r'\]'
    t_FORMULA = r'\$[^$]*\$'
    t_ignore = ' \t\r\n'
    
    RESERVED = {'null': 'NULL',
                'skip' : 'SKIP',
                'if': 'IF', 'then': 'THEN', 'else': 'ELSE', 'while': 'WHILE',
                'new': 'NEW',
                'assume': 'ASSUME', 'assert': 'ASSERT',
                'return': 'RETURN'}
    
    def t_IDENTIFIER(self, t):
        r"[a-zA-Z_][a-zA-Z_0-9]*"
        if t.value in self.RESERVED:
            t.type = self.RESERVED[t.value]
        return t
    
    def t_error(self,t):
        raise SyntaxError, u"Illegal character '%s' at %d:%d" % (t.value[0],t.lineno,t.lexpos)



class WhileParserRules(object):
    
    def __init__(self,formula_parser):
        """@param formula_parser is an instance of ForFormulaParser"""
        self.ffparser = formula_parser
    
    tokens = WhileLexerRules.tokens

    def p_error(self, p):
        if p is None: p = "unexpected end of input"
        raise SyntaxError, "Syntax error: %s" % p

    #
    # Basic Grammar of WHILE-language
    #
    
    def p_command_singl(self, p):
        """cmd : cmdf"""
        p[0] = p[1]
    
    def p_command_seq(self, p):
        """cmd : cmdf OP_SEMI cmd"""
        p[0] = Tree(p[2], [p[1], p[3]])
    
    def p_command_atom(self, p):
        """cmdf : stmt"""
        p[0] = p[1]
        
    def p_command_if_then_else(self, p):
        """cmdf : IF formula THEN cmdf ELSE cmdf"""
        p[0] = Tree('if', [p[2], p[4], p[6]])
        
    def p_command_while(self, p):
        """cmdf : WHILE formula LCURLY formula RCURLY cmdf"""
        p[0] = Tree('while', [p[2], p[4], p[6]])
    
    def p_command_block(self, p):
        """cmdf : LPAREN cmd RPAREN"""
        p[0] = p[2]
        
    def p_stmt_skip(self, p):
        """stmt : SKIP"""
        p[0] = Tree(p[1])
    
    def p_stmt_assign(self, p):
        """stmt : id OP_ASSIGN id"""
        p[0] = Tree('x:=y', [p[1], p[3]])
    
    def p_id(self, p):
        """id : IDENTIFIER"""
        p[0] = Tree(p[1])
        
    def p_formula(self, p):
        """formula : FORMULA"""
        result = self.ffparser(p[1][1:-1])
        p[0] = result        
    #
    # Additional Annotations
    #
    
    def p_assume_assert(self, p):
        """stmt : ASSUME formula
                | ASSERT formula
        """
        p[0] = Tree(p[1], [p[2]])
        
    #
    # Pointer Statements
    #
        
    def p_stmt_assign_null(self, p):
        """stmt : id OP_ASSIGN NULL"""
        p[0] = Tree('x:=null', [p[1]])
        
    def p_stmt_allocate(self, p):
        """stmt : id OP_ASSIGN NEW"""
        p[0] = Tree('x:=new', [p[1]])

    def p_stmt_field_get(self, p):
        """stmt : id OP_ASSIGN id OP_PERIOD id"""
        p[0] = Tree('x:=y.n', [p[1], p[3], p[5]])
        
    def p_stmt_field_set(self, p):
        """stmt : id OP_PERIOD id OP_ASSIGN id"""
        p[0] = Tree('x.n:=y', [p[1], p[3], p[5]])
        
    def p_stmt_field_set_null(self, p):
        """stmt : id OP_PERIOD id OP_ASSIGN NULL"""
        p[0] = Tree('x.n:=null', [p[1], p[3]])

    #
    # Rules for Procedural Programs
    #
    
    def p_stmt_call(self, p):
        """stmt : id OP_ASSIGN id LPAREN ids RPAREN"""
        p[0] = Tree("r:=f(...)", [p[1], Tree(p[3].root, p[5])])
    
    def p_list_of_args_singl(self, p):
        """ids : id"""
        p[0] = [p[1]]
    def p_list_of_args_cons(self, p):
        """ids : id OP_COMMA ids"""
        p[0] = [p[1]] + p[3]
    
    def p_stmt_return(self, p):
        """stmt : RETURN id"""
        p[0] = Tree(p[1], [p[2]])
    
    def p_stmt_annotated(self, p):
        """stmt : stmt annotation"""
        p[0] = Tree("/", [p[1], p[2]])
        
    def p_annotation(self, p):
        """annotation : LBRACK formula RBRACK"""
        p[0] = p[2]




class WhileFrontend(object):

    class WhileParser(object):
        def __init__(self,formula_parser):
            import os.path
            from ply import lex, yacc
            here = os.path.dirname(__file__)
            self.l = lex.lex(module=WhileLexerRules(), reflags=re.UNICODE)
            self.p = yacc.yacc(module=WhileParserRules(formula_parser),
                               tabmodule='synopsis.autogen.while_parsetab', 
                               outputdir=os.path.join(here,'autogen'),
                               debug=0)
        def __call__(self, text):
            return self.p.parse(text, lexer=self.l)

    class WhileASTDeserialize(object):
        def __init__(self):
            self.l = l = SillyLexer(r'\{|\}|,')
            self.b = SillyBlocker((l.TOKEN, '{'), (l.TOKEN, '}'))
        def __call__(self, text):
            t, = self.forestify(self.b(self.l(text)))
            t = TreeTransform([functools.partial(AuxTransformers.unfold, symbols={';': 2})], 
                              dir=TreeTransform.BOTTOM_UP, recurse=True)(t)
            return t
        def forestify(self, p):
            l = self.l
            forest, t = [], None
            for el in p:
                r = el.root
                if r[0] == l.TEXT and r[1].strip():
                    r = re.sub(u"^'(.*)'$", r'\1', r[1].strip())
                    t = Tree(r)
                    forest += [t]
                elif r == (l.TOKEN, '}'):
                    assert t is not None
                    t.subtrees = self.forestify(el.subtrees)
                    t = None
            return forest
        
    class Mixin(object):
        """ A mix-in for use of the While front-end in ProofSynopsis. """
        def __init__(self, formula_subparser):
            self.wf = WhileFrontend(formula_subparser)
        def __call__(self,t,e):
            root = t.root
            subtrees  = t.subtrees
            # Applies nodes of the form program(x) where x is a leaf
            if root == "program" and len(subtrees) == 1 and len(subtrees[0].subtrees) == 0:  
                return self.wf(subtrees[0].root.literal)
                
    def __init__(self,FolFormulaParser):
        self.parser = self.WhileParser(FolFormulaParser)
        
    def __call__(self, program_text, compose_prefix=''):
        ast = self.parser(program_text)
        astf = ApplyTo(nodes=Identifier.promote).inplace(FolFormula.reconstruct( ast ))
        if compose_prefix:
            for n in astf.nodes:
                if n.subtrees:
                    n.root = Identifier(compose_prefix + n.root.literal, 'macro')
                    
        return astf






if __name__ == '__main__':
    fe = WhileFrontend()
    
    astf = fe.parser("( if $C( i )$ then ( t := i.n ; j.n := null ; j.n := t ) else j := i ) ; i := i.n")

    print astf

    # Demo AST deserialization
    w = WhileFrontend.WhileASTDeserialize()
    print w(unicode(astf))
    
    
    print w(";{x:=y{i,j},y:=x.n{k,i},x.n:=y{i,i}}")
    print w(";{;{x:=y{i,h},x:=null{j},x:=null{t},while {((i != null) & (t = null)), I, skip}}}")
    raise SystemExit

    astf = fe("k:=i.n ; i.n:=j; j:=i; i:=k", 'wp ')
    astf = fe("( if $C( i )$ then ( t := i.n ; j.n := null ; j.n := t ) else j := i ) ; i := i.n", 'wp ')

    astf.subtrees += [FolFormula.promote("Q")]

    def compose_xform(t):
        import copy
        r, s = t.root, t.subtrees
        a = len(s)
        if r == 'wp ;' and a == 3:
            c1 = copy.deepcopy(s[0])
            c2 = copy.deepcopy(s[1])
            c2.subtrees += [s[2]]
            c1.subtrees += [c2]
            return c1
        if r == 'wp if' and a == 4:
            ct, ce = copy.deepcopy(s[1]), copy.deepcopy(s[2])
            ct.subtrees += [s[3]]
            ce.subtrees += [s[3]]
            return type(t)(r, [s[0], ct, ce])

    print astf
    
    xf = TreeTransform([compose_xform], dir=TreeTransform.TOP_DOWN, recurse=True)
    xf.IS_DESCENDING = True
    print xf(astf)