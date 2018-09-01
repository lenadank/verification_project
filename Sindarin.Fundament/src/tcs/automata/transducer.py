
from tcs.automata import DigraphBasedAutomaton



class MealyMachine(object):
    
    class TransitionLabel(DigraphBasedAutomaton.TransitionLabel):
        def __init__(self, input_symbol, output_symbol):
            super(MealyMachine.TransitionLabel, self).__init__(input_symbol)
            self.output_symbol = output_symbol
            
    
    def __init__(self, underlying_state_machine):
        self.automaton = underlying_state_machine
        
    def __call__(self, input_string):
        decision, transitions = self.automaton.with_transitions(input_string)
        return decision, self.extract_output(transitions)
    
    def extract_output(self, transitions):
        return [[e.label.output_symbol for e in t
                 if isinstance(e.label, MealyMachine.TransitionLabel)]
                for t in transitions]
