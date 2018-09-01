# encoding=utf-8

import itertools
import codecs

from adt.tree.transform import TreeTransform
from adt.graph.format import DigraphFormatter
from adt.graph.transform.apply import ApplyTo

from pattern.collection.strings import MultiSubstitution
from pattern.meta.event_driven import EventBox

from logic.fol import Identifier, FolFormula
from logic.fol.syntax.transform.delta import DeltaReduction,\
    PatternDeltaReduction
from logic.fol.syntax.transform import AuxTransformers
from logic.fol.syntax.transform.alpha import AlphaRenaming
from logic.smt.smtlib.sexpr import SExpression
from logic.smt.smtlib.input import SmtLib2InputFormat
from logic.smt.smtlib.output import SmtLib2OutputFormat, NamingConvention
from logic.fol.semantics.graphs import AlgebraicStructureGraphTool
from ui.text.lists import bulleted_list
from ui.text.table import side_by_side
from ui.text import indent_block
from filesystem.paths import CommonPath, SearchPath, find_closest

from eprv.synopsis.declare import TypeDeclarations, TypeInference
from eprv.synopsis.expand import Expansion
from eprv.modules import ModuleSystem
from eprv.extensions.easy_funcs import EasyFunctionsExtension
import collections
from eprv.extensions.prog.while_fe import WhileFrontend
from eprv.synopsis.fast_dr import FastSubstitutionOperator
from eprv.extensions.ternary import TernaryOperator
from pattern.debug.profile import ProcessingPhases, Stopwatch, TimeProfile
from eprv.extensions.fresh import FreshSymbolIntroduction, RenumberLiterals



try:
    from eprv.synopsis.ux.richtext import FormattedText
except ImportError:
    FormattedText = None # Qt not available

try:
    from adt.graph.visual.graphviz import GraphvizGraphLayout
except ImportError:
    GraphvizGraphLayout = None # pygraphviz not available




from functools import partial



class SynopsisNamingConvention(NamingConvention):
    
    ESCAPE_SEQ = {"'": "@_@", '"': "@__@", '#': "@1@", '>': "@gt@", '<': "@lt@", '(': "@9@", ')': "@0@",
                  ".": "@dot@",
                  '[': "@lb@", ']': "@rb@", u'α': "@a@", u'β': "@b@", u'γ': "@c@"}
    VALID_IDENTIFIER_RE = r'[_a-zA-Z0-9*$@\-=><]+$' 
    
    class When(object):
        def __init__(self, p, f):
            self.f, self.p = f, p
        def __call__(self, x):
            if self.p(x): return self.f(x)
            else: return x
    
    def __init__(self):
        import re
        m = self.ESCAPE_SEQ
        self._ck = re.compile(self.VALID_IDENTIFIER_RE)
        self._multisubst = MultiSubstitution(m)
        self._sscript_re = re.compile(ur'[₀₁₂₃₄₅₆₇₈₉]+')
        self._sscript_tab = {ord(k) : ord(v) for k,v in zip(u"₀₁₂₃₄₅₆₇₈₉", "0123456789")}
        self.escape = self.When(self._should_escape, Identifier.lift(self._s_escape))
        self.unescape = Identifier.lift(MultiSubstitution({v:k for k,v in m.iteritems()}))
        self._is_valid_identifier = Identifier.lift(self._s_is_valid)
        
    def _escape(self, s):
        s = self._multisubst(s)
        tab = self._sscript_tab
        return self._sscript_re.sub (lambda x: '$'+x.group().translate(tab), s)
        
    def _should_escape(self, s):
        return not (isinstance(s, Identifier) and s.kind in ['connective', 'quantifier'])
        
    def _s_escape(self, s):
        if isinstance(s, (str,unicode)) and s and s[0] == '"' or isinstance(s, Identifier) and s.kind in ['connective', 'quantifier']:
            return s
        else:
            return self._escape(unicode(s))
        
    def _s_is_valid(self, s):
        return (s and s[0] == '"') or self._check(self._ck, s) 
        
    def check(self, name):
        if isinstance(name, Identifier) and name.kind in ['connective', 'quantifier']:
            return
        self._is_valid_identifier(name)
        
        


class CheckQuantifierAlternation(object):
    
    def is_af(self, phi):
        return self.is_universal(phi) or self.is_existential(phi)
        
    def is_ae(self, phi):
        if phi.root == FolFormula.EXISTS:
            return self.is_existential(phi.subtrees[1])
        else:
            return self.is_af_core(phi, self.is_ae, self.is_ea)
    
    def is_ea(self, phi):
        if phi.root == FolFormula.FORALL:
            return self.is_universal(phi.subtrees[1])
        else:
            return self.is_af_core(phi, self.is_ea, self.is_ae)
    
    def is_universal(self, phi):
        return phi.root != FolFormula.EXISTS and \
               self.is_af_core(phi, self.is_universal, self.is_existential)
    
    def is_existential(self, phi):
        return phi.root != FolFormula.FORALL and \
               self.is_af_core(phi, self.is_existential, self.is_universal)
        
    def is_af_core(self, phi, positive, negative):
        r = phi.root
        s = phi.subtrees
        if r == FolFormula.NOT:
            return all(negative(x) for x in s)
        elif r == FolFormula.IMPLIES and len(s) == 2:
            return all(negative(x) for x in s[:-1]) and positive(s[-1])
        elif r == FolFormula.IFF:
            return all(negative(x) and positive(x) for x in s)
        elif r == "ite":
            return negative(s[0]) and all(positive(x) for x in s)
        else:
            return all(positive(x) for x in s)



class EPRFragment(CheckQuantifierAlternation):

    def verify_valid_alternation(self, phi, ctx=None):
        if phi.root == "lemma" and not self.is_ae(phi) or \
           phi.root != "lemma" and not self.is_universal(phi):
            raise ValueError, "detected unwanted quantifier alternation in '%s'" % phi
    def verify_no_function_survives(self, phi, ctx=None):
        if any(x.root.kind == 'function' and x.root != "lemma" and x.subtrees for x in phi.nodes):
            raise AssertionError, "bug: function symbols remain in '%s'" % phi



class ProofSynopsis(object):
   
    Expansion = Expansion
    Backend = SmtLib2InputFormat
    
    class Context(collections.namedtuple("Context", "expansion signature")):
        pass
    
    def __init__(self, options={}):
        self.options = options
        self.expansion = e = self.Expansion()
        self.post_process = ProcessingPhases([])
        
        macros = ['lemma(phi) := [;]([](push), echo(["]([\'], phi, [\'])), assert(not(phi)), []([check-sat]), []([get-model]), [](pop))',
                   "check := lemma(false)"]
        macros_f = self.macros_f = DeltaReduction()
        macros_f.IS_DESCENDING = False
        macros_f.transformers += \
            [DeltaReduction.Transformer(macros_f, e.parser(m)) for m in macros]

        self.renumber_f = RenumberLiterals()
        self.quote_f = AuxTransformers.quote_strings

        self.emit_phases = ProcessingPhases([(self.macros_f, "Synopsis macros"),
                                             (self.quote_f, "Quote strings")])

        self.type_declarations = TypeDeclarations()
        self.type_inference = None

        self.smt = self.Backend(naming_convention=SynopsisNamingConvention())
        self.libs = []
        
        self.on_assertion = EventBox(stop_on_error=True)
        
        self.initialize_mixins()
        
    def initialize_mixins(self):
        # Add pattern matching support
        self.expansion.delta = PatternDeltaReduction(recurse=True, dir=PatternDeltaReduction.BOTTOM_UP)
        self.expansion.delta.tuning.local_.before = AlphaRenaming()
        #self.subst = ProtectedSyntacticSubstitutionOperator()
        #self.expansion._enrich([self.subst])
        def dumpit(phi, ctx=None): print "??? ", phi
        fso = FastSubstitutionOperator()
        fsi = FreshSymbolIntroduction()
        self.post_process.phases += [(fsi, "Fresh symbols"), (fso, "Syntactic substitution")]
        # Add While-language support
        self.while_fe = WhileFrontend.Mixin(self.expansion.reader.parser);
        self.expansion._enrich([self.while_fe])
        # Add ternary operator
        ter = TernaryOperator()
        self.on_assertion += [ter.inspect_formula]
        # Add type inference
        if self.options.get('type-inference', False):
            self.type_inference = TypeInference()
            self.type_inference.declarations = self.type_declarations.sorts
        # Add easy functions
        if self.options.get('easy-funcs', False):
            ef = EasyFunctionsExtension()
            self.on_assertion += [ef.inspect_formula]
        # Check that resulting formulas are in the EPR fragment
        #if self.options.get('epr-check', False):
        #    self.fragment = epr = EPRFragment()
        #    self.on_assertion += [epr.verify_valid_alternation, epr.verify_no_function_survives]

    @classmethod
    def get_annotations(cls, program_text):
        import re
        for mo in re.finditer(r"^#\s*@(\w+)\W(.*)$", program_text, flags=re.MULTILINE):
            yield mo.groups()

    def emit_form(self, expr):
        expr = self.emit_phases(expr)
        r = expr.root
        if r == ';':
            return list(itertools.chain(*[self.smt.to_sexprs(phi) for phi in expr.split(';')]))
        else:
            return [SExpression('assert', [assertion])
                    for assertion in self.smt.to_sexprs(expr)]

    def emit(self, outfile, se):
        for cmd in self.emit_form(se):
            print >>outfile, cmd

    def emit_preface(self, outfile):
        print >>outfile, self.smt.preface
        for decl in self.smt.to_declare(self.renumber_f(self.type_declarations)):
            print '###', decl
            print >>outfile, decl

    def oblige(self, t):        return self._collect(t, self.obligations)
    def assume(self, t):        return self._collect(t, self.assumptions)

    def _collect(self, t, parts_f):
        parts = []
        xform = TreeTransform([partial(parts_f, collect=parts)], dir=TreeTransform.BOTTOM_UP)
        parts += [xform(t)]
        return parts

    def obligations(self, t, collect=[]):
        if t.root == 'valid':
            collect += [type(t)(Identifier('lemma', '?'), [x]) for x in t.subtrees]
            return FolFormula(FolFormula.TRUE)
        
    def assumptions(self, t, collect=[]):
        if t.root == 'provided':
            collect += t.subtrees
            return FolFormula(FolFormula.TRUE)


    def first_pass(self, program_text):
        """
        Collects all the declarations and yields the rest of the formulas
        """
        e = self.expansion
    
        if isinstance(program_text, list):
            stream = e(program_text)
        else:
            stream = itertools.chain(*[e(x) for x in self.libs + [program_text]])
        stream = (phi for x in stream for y in self.oblige(x) for phi in self.assume(self.post_process(y)))

        ctx = self.Context(expansion=self.expansion, signature=self.type_declarations)
        ti = self.type_inference if self.type_inference is not None else lambda x: x
        
        for phi in stream:
            phi = self.renumber_f(phi)  # TODO: This should NOT be needed here!
            if self.type_declarations.is_declaration(phi):
                self.type_declarations.read_from([phi])
            else:
                phi = ti(phi)
                self.on_assertion(phi, ctx)
                yield phi  # fwd to 2nd pass

    def __mul__(self, line_of_text):
        """
        Quickly parse, expand, and return result as FolFormula.
        """
        return FolFormula.conjunction(self.expansion(line_of_text))

    def __call__(self, program_text):
        import os.path, tempfile
        outfilename = os.path.join(tempfile.gettempdir(), "synopsis.smt2")
        outfile = open(outfilename, 'w')
    
        # First pass to collect all declarations
        stream = list(self.first_pass(program_text))
        self.emit_preface(outfile)
                    
        # Second pass gets the rest and emits them as assertions
        for phi in stream:
            phi = self.renumber_f(phi)
            y = side_by_side([" *>", bulleted_list(phi.split(), bullet='')], colsep='')
            print unicode(y)
    
            self.emit(outfile, phi)
                
        return outfilename



class TCSpecific(object):
    
    @classmethod
    def restore_tc_from_rtc(cls, m, relation_name, tc_relation_name=None, rtc_relation_name=None):
        nstar = m.interpretation[rtc_relation_name]  # n*
        nplus_restored = lambda u,v: nstar(u,v) and u != v
        m.interpretation[tc_relation_name] = nplus_restored
    
    @classmethod
    def restore_edge_relation_from_tc(cls, m, relation_name=None, rtc_relation_name=None):
        if relation_name is None:
            if rtc_relation_name is not None:
                relation_name, tc_relation_name = cls._guess_edge_label(rtc_relation_name)
            else:
                raise ValueError, "at least one of 'relation_name', 'rtc_relation_name' must be given"
        if rtc_relation_name is None:
            tc_relation_name, rtc_relation_name = cls._locate_tc_and_rtc(m, relation_name)
        if tc_relation_name not in m.interpretation:
            cls.restore_tc_from_rtc(m, relation_name, tc_relation_name, rtc_relation_name)
        nplus = m.interpretation[tc_relation_name]  # n+
        n_restored = lambda u,v: nplus(u,v) and not \
                                 any(nplus(u,w) and nplus(w,v)
                                     for w in m.domain)
        m.interpretation[relation_name] = n_restored
        return relation_name

    @classmethod
    def _locate_tc_and_rtc(cls, m, relation_name, fallback=None):
        for i in xrange(len(relation_name)+1):
            t = relation_name[:i] + '+' + relation_name[i:]
            r = relation_name[:i] + '*' + relation_name[i:]
            if t in m.interpretation or r in m.interpretation:
                break
        else:
            if fallback is None:
                raise KeyError, u"tc of %s" % relation_name
            
        return t, r
    
    @classmethod
    def _guess_edge_label(cls, tc_relation_name):
        tc_u = unicode(tc_relation_name)
        if '*' in tc_u:
            return tc_u.replace('*', ''), tc_u.replace('*', '+')
        else:
            raise ValueError, u"cannot extract original name from '%s'" % tc_u


class DummyStopwatch(object):
    def __enter__(self):            return self
    def __exit__(self, exc, v, tb): pass



def run_z3_and_produce_model(smtlib2_filename, gui=True, verbose=False, swatch=DummyStopwatch(), synopsis=None):
    
    if gui and (FormattedText is None or GraphvizGraphLayout is None):
        print "warning: Qt/pygraphviz packages missing, GUI disabled."
        gui = False
    
    import os.path, tempfile
    outfn = os.path.join(tempfile.gettempdir(), "model")
    z3_exe = CommonPath().find_file('z3' if os.name == 'posix' else 'z3.exe')
    with swatch:
        if verbose:  cmd = "%s %s | tee %s" % (z3_exe, smtlib2_filename, outfn)
        else:        cmd = "%s %s > %s" % (z3_exe, smtlib2_filename, outfn)
        os.system(cmd)
        z3_model = codecs.open(outfn, encoding='utf8').read()
    
    #print z3_model
    
    ofmt = SmtLib2OutputFormat()
    ofmt.naming = SynopsisNamingConvention()
    d = ofmt(z3_model)
    
    if any(e.root == 'model' for e in d.expressions): print "(counterexample)"
    
    if synopsis is not None:
        td = synopsis.type_declarations
        unary_preds = [p for p,_ in td.preds if td.sorts.ary(p, 1)]
        consts = [c for c,_ in td.funcs if td.sorts.is_const(c)]
    else:
        unary_preds = ['C', 'free', '_free', 'free1', 'free2']
        consts = ['b0', 'h', 'e', 't', '_h', 'h_']
    
    # TODO: Make stuff not hard-coded
    binary_preds = ["R", "F0", "F1", "F2", "F3", "A", "B", "D", "m", "R_k0", "R_km0", "LO", "R_f", "R_g","R_k10", "R_km10","R_k20", "R_km20",'m1','m2', 'n_m1','n_m2','nR_k10','nR_k20','nR_km10','nR_km20' , 'nn_m1','nn_m2','nnR_k10','nnR_k20','nnR_km10','nnR_km20','n_k1*','n_k2*','nn_k1*','nn_k2*']
    binary_preds_with_tc = ['n', "n'", 'n"', '_n', 'p', '_p', 'p_', 'p__', '__n', 'n_', 'n0', 'n1', 'n2', 'n3', 'n4', 'n5', 'n12', 'R', 'p1', 'p2', 'p3',
                            'k','k1','k2']
						
    # Filter out some undesired "model is not available" messages
    d_ = [x for x in d if not 
          (isinstance(x, d.MessageItem) and 'model is not available' in x.msg)]
    
    doc_cells = []
    
    for e in d_:
        if isinstance(e, d.ModelItem):
            m = e.structure
            toc = []
            #viz = False
            for n in binary_preds_with_tc:
                try:
                    TCSpecific.restore_edge_relation_from_tc(m, n)
                except KeyError:
                    continue
                toc += [n]
                _, nstar = TCSpecific._locate_tc_and_rtc(m, n)
                print m.binary_relation_as_table(nstar)
                
            #for r in ["R", "F2", "F3"]:
            #    if r in m.interpretation:
            #        print m.binary_relation_as_table(r)
                
            toc += [r for r in binary_preds if r in m.interpretation]

            for c in consts:
                if c in m.interpretation:
                    doc_cells += [('txt', u"%s = %s" % (c,m.interpretation[c]))]
                    
            print unary_preds
            for up in unary_preds:
                if up in m.interpretation:
                    cf = m.interpretation[up]
                    s = [x for x in m.domain if cf(x)]
                    doc_cells += [('txt', u"%s = %s" % (up, s))]

            for relation in toc:
                g = AlgebraicStructureGraphTool(m, [relation])()
                g = ApplyTo(nodes=lambda x: x.replace("V!val!", ':')).inplace(g)
                doc_cells += [('txt', '%s : %s' % (relation, "V -> V -> bool"))]
                if gui:
                    fn = GraphvizGraphLayout().with_(output_format='svg')(g)
                    doc_cells += [('img', open(fn, "rb").read())]
                else:
                    fmtd = DigraphFormatter()(g)
                    doc_cells += [('txt', indent_block(fmtd))]
                #viz = True
            if not toc:
                doc_cells += [('txt', "(no relations to draw)")]
        else:
            if FormattedText:
                text = FormattedText(e)
                if isinstance(e, d.MessageItem):
                    text.css['color'] = 'grey'
            else:
                text = unicode(e)
            doc_cells += [('txt', text)]

    return doc_cells



def show_results(doc_cells):
    print "#cells: ", len(doc_cells)

    if any(t for t,_ in doc_cells if t == 'img'):
        from eprv.synopsis.ux.richtext import RichTextApp
        a = RichTextApp([])
        for cell_type, cell_content in doc_cells:
            if cell_type == 'img':
                a.put_image(cell_content)
            else:
                a.put_text_block(cell_content)
        a()
    else:
        print '=' * 60
        print "  RESULTS"
        print '=' * 60
        for cell in doc_cells:
            print cell[1]



def module_system_default():
    import os.path
    import eprv
    here = os.path.dirname(os.path.realpath(eprv.__path__[0]))
    
    return ModuleSystem(SearchPath([find_closest("modules", start_at=here)]))



def main():
    from argparse import ArgumentParser
    a = ArgumentParser()
    a.add_argument("filename", type=str, help="Proof script")
    a.add_argument("--no-gui", action="store_true")
    a.add_argument("--verbose", action="store_true")
    a.add_argument("--mixin", nargs="+")
    a.add_argument("--macro-finder", action="store_true", help="Turn on Z3's macro finder mechanism")
    a.add_argument("--suppress-epr-check", action="store_true",
                   help="Does not check that the resulting formulas are EPR before sending them to Z3")
    args = a.parse_args()
    
    fol_fn = args.filename    
    inputs = open(fol_fn).read().decode("utf8")
    
    #import os.path
    #here = os.path.dirname(os.path.realpath(__file__))
    
    preface = "(declare-sort V 0)"
    if args.macro_finder:
        preface = "(set-option :smt.macro-finder true)\n" + preface
            

    ms = module_system_default()

    syn = ProofSynopsis({'easy-funcs': True, 'epr-check': not args.suppress_epr_check, 'type-inference': True})
    syn.smt.preface = preface
    syn.libs += [open(fn).read() for fn in
                 ms.find_module_sources_from_annotations(syn.get_annotations(inputs))]

    
    synswatch = Stopwatch()
    with synswatch:
        ofn = syn(inputs)
    

    z3swatch = Stopwatch()
    results = run_z3_and_produce_model(ofn, gui=not args.no_gui, verbose=args.verbose, swatch=z3swatch, synopsis=syn)
    show_results(results)

    
    print "\n/Statistics/"
    print TimeProfile().with_clock("Synopsis time", synswatch.clock).with_clock("Z3 time", z3swatch.clock)



if __name__ == '__main__':
    main()
