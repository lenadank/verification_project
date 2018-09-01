
from collections import Mapping
from vm.stack_machine.exceptions import SegmentationViolation



class FetchLoop(object):
    
    class InstructionSignatures(Mapping):
        def sizeof(self, mnemonic):
            """ Instruction size (including mnemonic), must be >= 1 """
            raise NotImplementedError

    class JumpInstructions(object):
        def __init__(self, fetch, stack):
            self.fetch, self.stack = fetch, stack
        def jump(self):
            """ Indirect jump (address is taken from stack) """
            self.fetch._pc = self.stack.pop()
        def jump_if(self):
            """ Conditional indirect jump (both condition and address taken 
                from stack) """
            addr, cond = self.stack.pop_many(2)
            if cond:
                self.fetch._pc = addr
        def jump_fast(self, address):
            """ Direct jump """
            self.fetch._pc = address
        def call(self):
            """ Pop call address from stack, push return address and jump """
            ret_addr = self.fetch._pc
            self.jump()
            self.stack.push(ret_addr)
        
    def __init__(self, signature, code, start=0):
        self.signature = signature
        self._cs = code
        self._pc = start
        
    def once(self):
        """ Executes one processor cycle """
        try:
            mn = self._cs[self._pc]
        except IndexError:
            raise SegmentationViolation(self._cs, self._pc)
        sz = self.signature.sizeof(mn)
        argv = self._cs[self._pc:self._pc + sz]
        if len(argv) < sz: raise SegmentationViolation(self._cs, self._pc)
        self._pc += sz
        self.signature[mn](*argv[1:])
        
    def __call__(self):
        while self._pc >= 0:
            self.once()
        
