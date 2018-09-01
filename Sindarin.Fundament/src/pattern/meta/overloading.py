
import new



class CovertOps(object):
    """
    Allows different classes to overload the prototype of built-in operators.
    If one of the implementations return NotImplemented, the next 
    implementation is attempted according to the mro.
    """
    
    # Binary Operators
    
    def __add__(self, other):  return self.__binop__('__add__', other)
    def __radd__(self, other): return self.__binop__('__radd__', other)
    def __sub__(self, other):  return self.__binop__('__sub__', other)
    def __rsub__(self, other): return self.__binop__('__rsub__', other)

    def __eq__(self, other):   return self.__binop__('__eq__', other)

    def __getitem__(self, i):  return self.__binop__('__getitem__', i)

    # Auxiliaries
    
    def __binop__(self, op, other):
        me_again = getattr(self, op).im_func
        for cls in type(self).mro():
            try:
                sub = getattr(cls, op)
            except AttributeError:
                continue
            if isinstance(sub, new.instancemethod) and \
                         sub.im_func is not me_again:    # don't recurse
                r = sub(self, other)
                if r is not NotImplemented: return r
        return NotImplemented

