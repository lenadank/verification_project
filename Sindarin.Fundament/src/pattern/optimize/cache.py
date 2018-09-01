from pattern.meta.oop import standardproperty, AutoNamingProperty
from collections import OrderedDict


class Memoization(object):
    
    class Statistics(object):
        def __init__(self):
            self.hits = 0
            self.misses = 0
    
    def __init__(self, function):
        self.function = function
        self.memo_key = lambda *args: self._fixate(args)
        self.memo = {}
        self.stats = Memoization.Statistics()

    def with_key(self, memo_key):
        self.memo_key = memo_key
        return self

    def __call__(self, *args):
        # - try getting from memo
        mkey = self.memo_key(*args)
        try:
            mvalue = self.memo[mkey]
            self.stats.hits += 1
            return mvalue
        except KeyError:
            # - compute value
            self.memo[mkey] = mvalue = self.function(*args)
            self.stats.misses += 1
            return mvalue

    def _fixate(self, args):
        if isinstance(args, list) or isinstance(args, tuple):
            return tuple(self._fixate(arg) for arg in args)
        elif isinstance(args, set):
            return tuple(sorted(args))
        else:
            return args


class BoundedCache(OrderedDict):
    """
    A dictionary that stores only the last n keys inserted.
    """
    
    capacity = 1
    
    def with_capacity(self, capacity):
        self.capacity = capacity
        return self
    
    def __setitem__(self, key, value):
        super(BoundedCache, self).__setitem__(key, value)
        if len(self) > self.capacity:
            for evict_key in self.iterkeys():
                del self[evict_key]
                break



class _OncePerInstance(standardproperty):
    def __get__(self, instance, owner):
        attr = '_once_%s' % self.name
        def f():
            try:
                instance_id, value = instance.__dict__[attr]
            except KeyError:
                instance_id, value = None, None
            # - check instance_id to detect copied or unpickled objects
            this = self.id(instance)
            if instance_id != this:
                instance_id, value = this, self._get(instance)
                instance.__dict__[attr] = (instance_id, value)
            return value
        f.__name__ = self.name
        return f
    def __set__(self, instance, value):
        raise AttributeError, 'read-only property'

class OncePerInstance(AutoNamingProperty, _OncePerInstance):
    def __init__(self, getfunc, id=id): #@ReservedAssignment
        self._get = getfunc
        self.id = id
        super(OncePerInstance, self).__init__()
    @classmethod
    def with_(cls, **kw):
        return lambda getfunc: cls(getfunc, **kw)



if __name__ == '__main__':
    class P(object):
        @OncePerInstance.with_(id=lambda x: 1)
        def f(self):
            print "id =", id(self)
            return id(self)
    
    import copy
    
    p = P()
    q = P()
    print p.f()
    print q.f()
    print p.f()
    print copy.copy(p).f()