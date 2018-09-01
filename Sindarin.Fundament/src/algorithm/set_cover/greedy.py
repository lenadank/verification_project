
from pattern.collection import OrderedSet, Cabinet
from algorithm.set_cover import NoSetCoverAtAll



class GreedySetCover(object):
    
    JOIN_ALL = "universe = union of all subsets"
    
    def __init__(self, universe, subsets):
        self.universe = universe
        self.subsets = subsets
        if self.universe is self.JOIN_ALL:
            self.universe = reduce(lambda x,y: x | y, self.subsets, set())
    
    def __call__(self):
        return list(self)

    def __iter__(self):
        uncovered = self.universe
        while uncovered:
            subsets_by_size = Cabinet().of(OrderedSet)\
                                .with_key(lambda x: (len(x & uncovered), x))\
                                .updated(self.subsets)
            most = max(subsets_by_size.keys())
            if most == 0:
                raise NoSetCoverAtAll(uncovered)
            choice = subsets_by_size[most][0] 
            yield choice
            uncovered = uncovered - choice
        


if __name__ == "__main__":
    inputs = [(set([1,2,3,4]), [set([1,4]), set([1,2,3]), set([2]), set([3,4])]),
              (set([2,3,4]), [set([1,4]), set([2])])] 
    
    for input in inputs:
        u, s = input
        try:
            for si in GreedySetCover(u, s)():
                print list(si)
        except NoSetCoverAtAll:
            print "no cover"
        print "-" * 20