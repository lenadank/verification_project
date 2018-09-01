'''
Macro definition & expansion support.
'''

from logic.fol.syntax.parser import FolFormulaParser, LexerRules
from logic.fol.syntax.formula import FolFormula
from pattern.optimize.cache import OncePerInstance
from logic.fol.syntax.transform.delta import DeltaReduction
from eprv.synopsis.binding import ProtectedDeltaReduction



class SynopsisFormulaParser(FolFormulaParser):
    class LexerRules(FolFormulaParser.LexerRules):
        def t_IDENTIFIER(self, t):
            r"""[a-zA-Z0-9_#\']+['"*+#_]*[0-9]*"""
            return super(SynopsisFormulaParser.LexerRules, self).t_IDENTIFIER(t)
    class ParserRules(FolFormulaParser.ParserRules):
        LexerRules = LexerRules



    

class Expansion(object):
    
    class FormulaReader(object):
        
        def __init__(self):
            self.defops = [(":=", 2, LexerRules.opAssoc.RIGHT)]
            if ':=' not in FolFormula.INFIXES:
                FolFormula.INFIXES += [":="]
            
        @OncePerInstance
        def _mkparser(self):
            return SynopsisFormulaParser(operators=FolFormulaParser.OPERATORS+self.defops)
        
        @property
        def parser(self):
            return self._mkparser()
        
        def __call__(self, program_text):
            if isinstance(program_text, (str, unicode)):
                inputs = self._separate_blocks(program_text)
            else:
                inputs = program_text
    
            for line in inputs:
                phi = line if isinstance(line, FolFormula) else \
                      self.parser(line)
                yield phi

        def _separate_blocks(self, program_text):
            buf = ""
            for line in program_text.splitlines(True):
                if line.startswith('#'): continue
                indented = any(line.startswith(ws) for ws in " \t")
                if not indented:
                    if buf.strip(): yield buf
                    buf = ''
                buf += line
            if buf.strip(): yield buf

    def __init__(self):
        self.reader = self.FormulaReader()
        self.delta = DeltaReduction(recurse=True)
        self.fwd_defs = []
    
    @property
    def parser(self):
        return self.reader.parser

    def __call__(self, program_text):
        defs = self.delta.transformers
        
        for phi in self.reader(program_text):
            try:
                xt = self.delta.parse_definition(phi)
                # @@@ OH YUCK! forward 'pvars' so it gets all the way to
                #  the proof synopsis
                #if getattr(xt, 'head', None) in self.fwd_defs: 
                #    yield phi; continue
                defs += [xt]
            except ValueError:
                # not a definition
                psi = self._apply_fix(self.delta, phi)
                #psi = self.delta(phi)
                yield psi
                
    def _apply_fix(self, xform, phi):
        ''' Applies transform until the result no longer changes '''
        phi = xform(phi) # first one runs asnew
        while True:
            changed = []
            phi = xform.inplace(phi, out_diff=changed)
            if not changed: break
            print phi
            #phi_prime = xform(phi)#, out_diff=changed)
            #if phi == phi_prime: break #not changed: break
            #phi = phi_prime
        return phi

    def _enrich(self, p):
        self.delta.transformers += [lambda t: x(t, self) for x in p]
        


class SyntacticSubstitutionOperator(object):
    
    delta_factory = DeltaReduction
    
    def __call__(self, t, e):
        """
        Notice: inner substitutions are applied before the outer ones.
        """
        r, s = t.root, t.subtrees
        a = len(s)
        if r == "dr" and a >= 2:
            dx = self.delta_factory()
            dx.transformers += [dx.Transformer(dx, x) for x in s[:-1]]
            dx.IS_DESCENDING = False
            dx.dir = dx.BOTTOM_UP
            return dx(s[-1])


class ProtectedSyntacticSubstitutionOperator(SyntacticSubstitutionOperator):
    
    delta_factory = ProtectedDeltaReduction



        