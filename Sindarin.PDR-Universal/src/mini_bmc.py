
from z3 import *  # @UnusedWildImport

from z3support.vocabulary import Z3TwoVocabulary, Z3Renaming



class BMC(object):
    """
    Unrolls a loop a bounded number of times, constructs a multi-vocabulary formula
    and then attempts to find a concrete trace.
    """
    
    def __init__(self, init, rho, bad, background, locals):  # @ReservedAssignment
        self.Init = init
        self.Rho = rho
        self.Bad = bad
        self.background = background
        self.Locals = Z3TwoVocabulary.promote(locals)

    def find_concrete_trace(self, num_steps):
        k = num_steps
        state_locals = [self.Locals.present.dup('$%d' % i)
                        for i in xrange(k+1)]   # 0..k
        s = Solver()
        s.add(self._rename_to(state_locals[0], self.Init))
        for i in xrange(k):
            s.add(self._rename_two(state_locals[i], state_locals[i+1], self.Rho))
        for i in xrange(k+1):
            s.add(self._rename_to(state_locals[i], self.background))
        s.add(self._rename_to(state_locals[k], self.Bad))
        decision = s.check()
        print decision
        
        if sat == decision:
            #set_param(max_lines=1000, max_width=120, max_indent=80, max_depth=40)
            #print s.model()
            return self._unzip_structures(s.model(), state_locals)
        
    def _rename_to(self, state_locals, term):
        return Z3Renaming(self.Locals.present, state_locals)(term)

    def _rename_two(self, state0_locals, state_locals, term):
        assert len(self.Locals) == len(state0_locals) == len(state_locals)
        return Z3Renaming(self.Locals.past + self.Locals.present,
                          state0_locals + state_locals)(term)


    def _unzip_structures(self, multi_vocab_model, state_locals):
        present = self.Locals.present
        return [self.SubModelAdapter(multi_vocab_model, Z3Renaming(present, state_locals_i))
                for state_locals_i in state_locals]

    class SubModelAdapter(object):
        
        def __init__(self, big_model, renaming):
            self.big_model = big_model
            self.renaming = renaming
            
        def get_universe(self, z3_sort):
            return self.big_model.get_universe(z3_sort)
            
        def evaluate(self, term):
            return self.big_model.evaluate(self.renaming(term))
        
        def get_interp(self, decl):
            return self.big_model.get_interp(self.renaming(decl))
