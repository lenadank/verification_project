
from pattern.collection import OneToOne
import thread



class CallingContext(object):
    
    THREAD_LOCAL = OneToOne().of(lambda x: object.__new__(CallingContext)._empty())
    
    def __new__(cls):
        return cls.THREAD_LOCAL[thread.get_ident()]
    
    def _empty(self):
        self.stack = []
        return self
    
    def __enter__(self):
        owner = self
        restore = self.__dict__.copy()
        class Guard(object):
            def __exit__(self, exc, value, tb):
                owner.__dict__.clear()
                owner.__dict__.update(restore)
                
        self.stack.append(Guard())
        return self
    
    def __exit__(self, exc, value, tb):
        self.stack.pop().__exit__(exc, value, tb)
    
    

if __name__ == '__main__':
    with CallingContext() as ctx:
        ctx.value = 6
        print getattr(CallingContext(), 'value', None)
        
    print getattr(CallingContext(), 'value', None)
    