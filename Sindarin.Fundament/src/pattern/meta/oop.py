
from pattern.collection.basics import WorksetGenerator, OrderedSet



def all_ur_base(cls):
    ws = WorksetGenerator(set([cls]))
    vis = OrderedSet()
    for c in ws:
        vis.add(c)
        ws.workset.update(b for b in c.__bases__ if b not in vis)
    return vis



class standardproperty(object):
    def __init__(self, name=None):   self.name = name
    def __get__(self, obj, owner):   return (obj if obj is not None else owner).__dict__[self.name]
    def __set__(self, obj, value):   obj.__dict__[self.name] = value


# http://stackoverflow.com/questions/128573/using-property-on-classmethods
class ClassProperty(property): 
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class AutoNamingProperty(standardproperty):
    
    name = None
    
    def __init__(self, proxy=None):
        super(AutoNamingProperty, self).__init__()
        self.__property = (proxy if proxy is not None 
                           else
                           super(AutoNamingProperty, self))
    
    def __get__(self, instance, owner):
        self._getname(owner)
        if instance is None: return self
        try:
            return self.__property.__get__(instance, owner)
        except KeyError:
            raise AttributeError, "'%s' object's attribute '%s' is not set" % (type(instance).__name__, self.name)
    
    def __set__(self, instance, value):
        self._getname(type(instance))
        self.__property.__set__(instance, value)

    def _getname(self, owner_type):
        if self.name is None:
            for cls in all_ur_base(owner_type):
                for key, value in cls.__dict__.iteritems():
                    if value is self:
                        self.name = key
        assert self.name is not None


class _OverridableProperty(standardproperty):
    def __get__(self, instance, owner):
        try:
            return instance.__dict__['_ovr_%s' % self.name]
        except KeyError:
            return self._get(instance)
    def __set__(self, instance, value):
        instance.__dict__['_ovr_%s' % self.name] = value

class OverridableProperty(AutoNamingProperty, _OverridableProperty):
    def __init__(self, getfunc):
        self._get = getfunc
        super(OverridableProperty, self).__init__()


class UniqProperty(standardproperty):
    """
    Throws away multiple consequent assignments of the same value.
    """
    
    def __init__(self, proxy=None):
        super(UniqProperty, self).__init__()
        self.__property = (proxy if proxy is not None 
                           else
                           super(UniqProperty, self))

    def __get__(self, instance, owner):
        return self.__property.__get__(instance, owner)

    def __set__(self, instance, value):
        try:
            ditto = value == self.__get__(instance, type(instance))
        except (KeyError, AttributeError):
            ditto = False
        if not ditto: self.__property.__set__(instance, value)


class InnerClasses(object):
    """
    Provides facilities for nesting classes one inside the other.
    Currently offers a fix for pickle that allows instances of nested classes 
    to be serialized.
    """

    class Owned(object):
        def __init__(self, owner):
            self.o = owner
        def by(self, owner):  # for use if a different constructor is needed
            self.o = owner
            return self

    @classmethod
    def nest(_, cls):
        """A decorator for a container class."""
        nested = [(k,v) for k,v in cls.__dict__.iteritems()
                  if isinstance(v, type) and hasattr(v, '__nestlings__')]
        for k, nested_class in nested:
            _._insert_ns(cls, nested_class)
            setattr(cls, k, nested_class)
        cls.__nestlings__ = [v for k,v in nested]
        return cls

    @classmethod
    def nested(_, cls):
        """A decorator for a nested class; containing class must be decorated
        with 'nest'."""
        return _.nest(cls)
        
    @classmethod
    def _insert_ns(cls, container, contained):
        import sys
        contained.__name__ = '%s.%s' % (container.__name__, contained.__name__)
        sys.modules[container.__module__].__dict__[contained.__name__] = contained
        for recurse in getattr(contained, '__nestlings__', ()):
            cls._insert_ns(container, recurse)

nest = InnerClasses.nest
nested = InnerClasses.nested



if __name__ == '__main__':
    class A(object): pass
    class B(object): pass
    class C(B): pass
    class D(A, C): pass
    
    print all_ur_base(D)

    class P(standardproperty):
        def __set__(self, instance, value):
            print "set", value
            super(P, self).__set__(instance, value)
            
    class UniqP(AutoNamingProperty, UniqProperty, P):
        pass
            
    class Q(object):
        #also possible: p = UniqProperty(proxy=P('p'))
        p = UniqP()
    q = Q()
    for v in 'aabacc':
        q.p = v

    @nest
    class Asilo(object):
        @nested
        class Nido(object):
            @nested
            class Ucello(object):
                pass
            u = Ucello()
    
    Nido = Asilo.Nido
    print Nido.__name__, Nido
    print Nido.Ucello.__name__, Nido.Ucello
    
    import pickle, cPickle
    u = Nido.Ucello()
    pickle.loads(pickle.dumps(u))
    cPickle.loads(cPickle.dumps(u))