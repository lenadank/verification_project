
from tcs.regexp import RegExp
from adt.graph.build import FlowGraphTool
from adt.tree.paths import Path

from tcs.automata import DigraphBasedAutomaton
from tcs.automata.transducer import MealyMachine



class RegExp2FSA(object):
    
    StateLabel = DigraphBasedAutomaton.StateLabel

    def __init__(self):
        self.uid = 0
    
    def __call__(self, regexp):
        p = self.prebuild(regexp)
        for exit in p.outgoing:
            exit.node.label.is_accept = True
        return DigraphBasedAutomaton(p())
    
    def prebuild(self, regexp, path=Path()):
        path = path + [regexp]
        if regexp.root == RegExp.NODE_CONCAT:
            return self.concat(regexp.subtrees, path)
        elif regexp.root == RegExp.NODE_REPEAT:
            assert len(regexp.subtrees) == 1
            return self.repeat(regexp.subtrees[0], path)
        else:
            return self.leaf(regexp.root, path)

    def concat(self, subtrees, path=Path()):
        a = self.prebuild(subtrees[0], path)
        for sub in subtrees[1:]:
            a = a >> self.prebuild(sub, path)
        return a
    
    def repeat(self, subtree, path=Path()):
        a = self.prebuild(subtree, path)
        n = self._new_state()
        return n >> (a >> a) >> n
    
    def leaf(self, root, path):
        a = self._new_state()
        b = self._new_state()
        symbol = MealyMachine.TransitionLabel(root.symbol, path)
        return a >> symbol >> b
        
    def _new_state(self):
        self.uid += 1
        lbl = self.StateLabel(self.uid, False)
        n = FlowGraphTool.block(lbl)
        return n
    
    
class RegExpMatch(object):
    
    def __init__(self, regexp, input_string, xducer_output):
        self.components = regexp.subtrees or [regexp]
        self.indices = self.indexize(self.components, xducer_output)
        self.cutpoints = self.cut(self.indices, len(self.components))
        self.parts = self.break_apart(self.cutpoints, input_string)
    
    @classmethod
    def indexize(cls, regexp_components, xducer_output):
        indexing = []
        for out in xducer_output:
            indices = []
            for out_xref in out:
                for i in xrange(len(regexp_components)):
                    if out_xref.goes_through(regexp_components[i]):
                        indices.append(i)
                        break
            indexing.append(indices)
        return indexing
    
    @classmethod
    def cut(cls, indices, num_components):
        i = 0
        parts = [0]
        for j in xrange(len(indices)):
            assert i <= max(indices[j])
            while i not in indices[j]:
                parts.append(j)
                i += 1
            parts[i] = j+1#.append(input_string[j])
        # - pad to match number of components
        return parts + [len(indices)] * (num_components - len(parts))

    @classmethod
    def break_apart(cls, cutpoints, input_string):
        c = [0] + cutpoints
        return [input_string[c[i]:c[i+1]] for i in xrange(len(cutpoints))]


if __name__ == "__main__":
    from adt.graph.format import DEFAULT as formatter
    from tcs.regexp import RegExpAssistant
    
    res = [('+', [('*', ['g']), 'h']), 
           ('+', [('*', ['g']), ('*', ['g'])]),
           ('+', [('*', ['g']), 'g'])]
    inputs = ["gggh", "gg", "ggg", "g7ggh"]
    
    r2a = RegExp2FSA()
    
    for re in res:
        r = RegExpAssistant.build(re)
        print r

        am = r2a(r)
        print formatter(am.g)
        
        for input in inputs:
            #decision, transitions = am.with_transitions(input)
            decision, stuff = MealyMachine(am)(input)
            if decision:
                match = RegExpMatch(r, input, stuff)
                stuff = match.cutpoints
            print u"   %-40s %-7r %r" % (input, decision, stuff)
