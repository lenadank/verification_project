from pattern.meta.oop import ClassProperty


def singleton_factory(ctor_func):
    """
    Converts a function into one that is only called once, subsequent calls
    just return the same object.
    """
    closure = []
    def factorize():
        if not closure:
            closure.append(ctor_func())
        return closure[0]
    if hasattr(ctor_func, '__name__'):
        factorize.__name__ = ctor_func.__name__
    return factorize

    

def class_singleton(ctor_func):
    ignore_first = lambda f: lambda x, *a: f(*a) 

    return ClassProperty(classmethod(ignore_first(singleton_factory(ctor_func))))
    