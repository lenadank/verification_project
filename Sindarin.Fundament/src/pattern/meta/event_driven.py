
import traceback
from pattern.meta.oop import standardproperty, AutoNamingProperty



class EventBox(list):
    
    def __init__(self, stop_on_error=False):
        """ 
        @param stop_on_error: if one event terminates with an error,
            stop processing of other events.
        """
        self.stop_on_error = stop_on_error
    
    def __call__(self, *a, **kw):
        for f in self:
            try:
                f(*a, **kw)
            except SystemExit:
                raise
            except:
                if self.stop_on_error: raise
                traceback.print_exc()



class AbstractAttentiveProperty(standardproperty):

    def __init__(self, proxy=None):
        super(AbstractAttentiveProperty, self).__init__()
        self.__property = (proxy if proxy is not None 
                           else super(AbstractAttentiveProperty, self))

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
        # dispatch
        self(instance).on_set()
    

class AttentiveProperty(AutoNamingProperty, AbstractAttentiveProperty):
    
    class delegate: object
    
    def __call__(self, instance):
        self._getname(type(instance))
        eva = 'on_%s_set' % self.name
        d = instance.__dict__
        if eva in d:
            eb = d[eva]
        else:
            d[eva] = eb = EventBox()
        o = self.delegate()
        o.on_set = eb
        return o



if __name__ == '__main__':
    class P(object):
        lof = AttentiveProperty()
    
    def its_on(): print "It's on!"
    def its_off(): print "It's off!"
    
    p = P()
    P.lof(p).on_set += [its_on]
    p.lof = 'value'
    p.on_lof_set += [its_off]
    p.lof = 'eulav'
    print p.lof