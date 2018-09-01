
import operator



class StackInstructionsBase(object):

    def __init__(self, stack):
        self._ss = stack
        
    def _unop(self, unfunc):
        _ = self._ss
        _.push(unfunc(_.pop()))
        return self
        
    def _binop(self, binfunc):
        _ = self._ss
        l, r = _.pop_many(2)
        _.push(binfunc(l, r))
        return self
    

class IntrinsicOperations(StackInstructionsBase):
    
    def add(self): return self._binop(operator.add)
    def sub(self): return self._binop(operator.sub)
    def mul(self): return self._binop(operator.mul)
    def floordiv(self): return self._binop(operator.floordiv)



class MemoryInstructions(StackInstructionsBase):
    
    def __init__(self, stack, mem):
        super(MemoryInstructions, self).__init__(stack)
        self._ds = mem
        
    def alloc(self):
        _ = self._ss
        sz = _.pop()
        data = _.pop_many(sz)
        address = len(self._ds)
        self._ds += data
        _.push(address)
        return self
        
    def deref(self):
        return self._unop(lambda address: self.mem[address])

