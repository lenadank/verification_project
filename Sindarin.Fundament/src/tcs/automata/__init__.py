"""
Finite-State Automata (Deterministic and Non-deterministic)

A formulation
"""


from adt.graph.paths import Emerge
from pattern.collection import BuildupSet



class Automaton(object):
    
    ###
    # Basic SM Methods
    ###

    def __call__(self, input_string):
        state = self.initial()
        for symbol in input_string:
            state = self.next(state, symbol)
        return self.decide(state)

    def initial(self):
        raise NotImplementedError
    
    def next(self, state, symbol): #@ReservedAssignment
        raise NotImplementedError
    
    def decide(self, state):
        raise NotImplementedError
    
    ###
    # Computation Trace Methods
    ###
    
    def with_transitions(self, input_string):
        state = self.initial()
        transitions = []
        for symbol in input_string:
            state, transition = self.next_with_transition(state, symbol)
            transitions.append(transition)
        return self.decide(state), self.reduce(transitions)

    def next_with_transition(self, state, symbol):
        raise NotImplementedError
    
    def reduce(self, transitions): #@ReservedAssignment
        return transitions


class DigraphBasedAutomaton(Automaton):

    class StateLabel(object):
        def __init__(self, name, is_accept=False):
            self.name = name
            self.is_accept = is_accept
        def __repr__(self):
            if self.is_accept:
                return "((%s))" % self.name
            else:
                return "(%s)" % self.name
        @classmethod
        def parse(cls, s):
            if s.startswith("((") and s.endswith("))"):
                nm, yn = s[2:-2], True
            elif s.startswith("(") and s.endswith(")"):
                nm, yn = s[1:-1], False
            else:
                nm, yn = s, False
            return cls(nm, yn)
        
    class TransitionLabel(object):
        def __init__(self, input_symbol):
            self.input_symbol = input_symbol
        def __eq__(self, other):
            if isinstance(other, DigraphBasedAutomaton.TransitionLabel):
                return self.input_symbol == other.input_symbol
            else:
                return self.input_symbol == other
        def __repr__(self):
            return `self.input_symbol`
        def __str__(self):
            return str(self.input_symbol)

    def __init__(self, state_graph):
        self.g = state_graph

    def initial(self):
        return self._epsilon_closure(self.g.roots)
    
    def next(self, state, symbol): #@ReservedAssignment
        em = Emerge(self.g, BuildupSet)
        return self._epsilon_closure(em.single_step(state, symbol))
    
    def next_with_transition(self, state, symbol):
        em = Emerge(self.g, BuildupSet)
        next, transition = em.single_step_with_edges(state, symbol) #@ReservedAssignment
        return self._epsilon_closure(next), transition
    
    def decide(self, state):
        return len([n for n in state if n.label.is_accept]) > 0

    def reduce(self, transitions): #@ReservedAssignment
        if not transitions: return transitions
        transitions[-1] = [e for e in transitions[-1]
                           if e.destination.label.is_accept or # optimization cheat
                           self.decide(self._epsilon_closure([e.destination]))]
        prev = transitions[-1]
        for i in xrange(len(transitions)-2, -1, -1):
            sources = set(e.source for e in prev)
            transitions[i] = [e for e in transitions[i]
                              if self._epsilon_closure([e.destination])
                                .intersection(sources)]
            prev = transitions[i]
        return transitions

    def _epsilon_closure(self, state_set):
        em = Emerge(self.g, BuildupSet)
        return self._closure(state_set, lambda x: em.single_step(x, None))

    def _closure(self, buildup_set, func):
        if not isinstance(buildup_set, BuildupSet):
            buildup_set = BuildupSet(buildup_set)
        while buildup_set.dirty:
            buildup_set.accept()
            buildup_set.update(func(buildup_set))
        return buildup_set



if __name__ == "__main__":
    from adt.graph.build import FlowGraphTool
    from adt.graph.format import DEFAULT as formatter
    from adt.graph.transform.apply import ApplyTo 
    
    am_specs = [(["(0)", "((1))"],
                 lambda a,b: a >> 0 >> b >> 0 >> a),
                (["0", "1", "2", "3", "4", "((5))"],
                 lambda a,b,c,d,e,f: a >> 'c' >> a >> b >> 'a' >> c >> 'b' >> d >> \
                    'a' >> (c | e >> 'c' >> f))]
    
    inputs = [[0] * 3,
              "ccababac"]
    
    for am_spec in am_specs:
        g = FlowGraphTool(am_spec)()
        ApplyTo(nodes=DigraphBasedAutomaton.StateLabel.parse).inplace(g)
        print formatter(g)
        
        a = DigraphBasedAutomaton(g)
        for input in inputs: #@ReservedAssignment
            decision, transitions = a.with_transitions(input)
            print "%-40s %-8r %r" % (input, decision, (transitions))
            print "%-40s %-8r %r" % (input, decision, a.reduce(transitions))
