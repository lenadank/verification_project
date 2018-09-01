
import new



class Lazy(object):
    """
    E.g. Lazy(__repr__=lambda: bring_it_on('%s'))
    """
    
    def __new__(cls, **ops):
        lazy_ops = dict((name, lambda self, *a: func(*a))
                        for name, func in ops.iteritems())
        q = new.classobj("Lazy", (cls,), lazy_ops)
        return object.__new__(q)
