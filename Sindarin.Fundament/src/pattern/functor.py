# encoding=utf-8


class Functor(object):

    def following(self, other):
        return FunctorCompsition([self, other])

    def across(self, sequence):
        return [self(x) for x in sequence]
    
    def across_values(self, mapping):
        return dict((key, self(value)) for key, value in mapping.iteritems())

    def __mul__(self, other):
        if isinstance(other, Functor):
            return self.following(other)
        elif isinstance(other, list):
            return self.across(other)
        elif isinstance(other, dict):
            return self.across_values(other)


class FunctorCompsition(Functor, list):
    
    def __call__(self, arg0):
        y = arg0
        for f in reversed(self):
            y = f(y)
        return y
    
    def following(self, other):
        return FunctorCompsition(self + [other])


class FunctorExtension(Functor, list):
    
    def __call__(self, *args):
        for f in self[:-1]:
            try:
                return f(*args)
            except (ValueError,KeyError):
                continue
        else:
            return self[-1](*args)


class Overloaded(Functor, dict):
    """
    A functor which performs various actions depending on the type of the
    argument.
    """
    
    def __call__(self, arg0):
        for key, func in self.iteritems():
            if isinstance(arg0, key):
                return func(arg0)
        else:
            raise TypeError, "unexpected type: '%s'" % type(arg0).__name__


class ExplicitFunctor(Functor, dict):
    """
    A functor explicitly defined by a mapping from its domain to its range.
    """
    
    def __call__(self, *args):
        try:
            if len(args) == 1:
                return self[args[0]]
            else:
                return self[args]
        except KeyError:
            raise ValueError, "f%r for f=%r" % (args, self)
        
    def __repr__(self):
        return u"{%s}" %\
            u" ".join(u"%r↦%r" % (x,y) for x,y in self.iteritems())


class MembershipFunctor(Functor, set):
    
    def __call__(self, *args):
        if len(args) == 1:
            return args[0] in self
        else:
            return args in self
        
    def __repr__(self):
        return u"∈{%s}" % (u",".join(`x` for x in self))
    
    def iteritems(self):
        return ((x, True) for x in self)


class PartialFunction(Functor):
    
    UNDEFINED = "<undef>"
    
    def __init__(self, functor, defined_subset):
        self.functor = functor
        self.defined = defined_subset
    
    def __call__(self, *args):
        if len(args) == 1:
            is_defined = args[0] in self.defined
        else:
            is_defined = args in self.defined
        if is_defined:
            return self.functor(*args)
        else:
            return self.UNDEFINED 


class Labeled(Functor):
    
    def __init__(self, label, functor):
        self.underlying = functor
        self.label = label
        
    def __call__(self, *a, **kw):
        return self.underlying(*a, **kw)

    def __repr__(self):
        return self.label


class Inverse(Functor):
    
    def __init__(self, functor, domain):
        self.functor = functor
        self.domain = domain
        self.lookup_table = None
        
    def __call__(self, *a):
        if self.lookup_table is None:
            f = self.functor
            self.lookup_table = ExplicitFunctor((f(x), x) for x in self.domain)
        return self.lookup_table(*a)


class SetWhere(object):
    
    def __init__(self, cond=lambda _: False):
        self.cond = cond
        
    def __contains__(self, element):
        return self.cond(element)
    
    ALL = ()  # just for PyDev to not get confused

SetWhere.ALL = SetWhere(lambda _: True)


class SetComplement(object):
    
    def __init__(self, set): #@ReservedAssignment
        self.set = set
        
    def __contains__(self, element):
        return element not in self.set



class MultiWayFunctor(Functor):
    """
    A functor that performs a complex operation mapping n inputs to m outputs.
    Normally this is done by a function with n parameters returning a tuple
    with m elements; But in addition, the functor can be called with a 
    dictionary in which values are keyed by some identifiers (not necessarily
    string literals), and the return value is also a dictionary with possibly
    different keys.
    """
    
    def __init__(self, func, input_order, output_order):
        self.input_order = input_order
        self.output_order = output_order
        self.func = func
        self.default_prefix_args = ()
        
    def __call__(self, *args):
        return self.func(*args)

    def map(self, data, positional_args=None): #@ReservedAssignment
        pargs = positional_args if positional_args is not None \
                                else self.default_prefix_args
        args = pargs + tuple(data[v] for v in self.input_order)
        out_seq = self.func(*args)
        return dict(map(None, self.output_order, out_seq))
    
    def map_update(self, data, positional_args=None):
        data.update(self.map(data, positional_args))
        return data



if __name__ == "__main__":
    # this example is shown in the Wikipedia entry "Function composition"
    f = ExplicitFunctor({"a": 1, "b": 1, "c": 3, "d": 4})
    g = ExplicitFunctor({1: "@", 2: "#", 3: "#", 4: "!!"})
    print f
    print (g * f)("c")
    print g * dict(f)

    