# encoding=utf-8

from pattern.functor import MembershipFunctor



class TransitiveClosure(object):

    class FloydWarshall(object):
        def __call__(self, domain, relation):
            if isinstance(relation, set):
                tc = MembershipFunctor(relation)
            else:
                tc = MembershipFunctor((x,y) for x,y in relation if relation(x,y))
            for k in domain:
                for x in domain:
                    for y in domain:
                        if (x,k) in tc and (k,y) in tc:
                            tc.add((x,y))
    
            return tc
                
    class Reachability(object):
        def __call__(self, domain, relation):
            raise NotImplementedError
    
    def __init__(self, domain):
        self.domain = domain
        self.algorithm = self.FloydWarshall()
    
    def using(self, algorithm):
        self.algorithm = algorithm
        return self
    
    def __call__(self, relation):
        return self.algorithm(self.domain, relation)


class ReflexiveTransitiveClosure(TransitiveClosure):
    
    def __call__(self, relation):
        tc = super(ReflexiveTransitiveClosure, self).__call__(relation)
        tc.update((x,x) for x in self.domain)
        return tc



if __name__ == '__main__':
    relation = set((x,x+2) for x in xrange(4))
    print sorted(TransitiveClosure(range(6))(relation))
    print sorted(ReflexiveTransitiveClosure(range(6))(relation))
