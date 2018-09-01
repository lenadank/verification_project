
from vm.stack_machine.stack import Stack
from vm.stack_machine.instructions import IntrinsicOperations,\
    MemoryInstructions
from vm.stack_machine.fetch import FetchLoop



class Processor(object):
    
    class InstructionModules(dict, FetchLoop.InstructionSignatures):
        def __init__(self, stack, mem):
            self.intrinsic = i = IntrinsicOperations(stack)
            self.memory = m = MemoryInstructions(stack, mem)
            self.jump = j = FetchLoop.JumpInstructions(None, stack) # fetch will be filled in later
            # Fill mapping
            for module in [i, m, j]:
                for method in dir(module):
                    if not method.startswith('_'):
                        self[method] = getattr(module, method)
            for method in ['push', 'pick', 'yank']:
                self[method] = getattr(stack, method)
            self['yank/2'] = self['yank']
        def sizeof(self, mnemonic):
            if mnemonic == 'yank/2': return 3
            if mnemonic in ['push', 'pick', 'yank', 'jump_fast']: return 2
            return 1
    
    def __init__(self):
        self._cs = []
        self._ds = []
        self._ss = Stack()
        
        self.core = self.InstructionModules(self._ss, self._ds)
        self.thread = self.core.jump.fetch = FetchLoop(self.core, self._cs)

    def __call__(self, program_asm):
        self._cs[:] = program_asm
        self.thread._pc = 0
        self.thread()
        return self._ss



if __name__ == '__main__':
    p = Processor()
    print "Instruction set:", p.core.keys()
    program = ['push', 0x9,                                  # 1: c = 9 
               'push', 0x1, 'pick', 1, 'sub', 'yank', 1,     # 2: c = c - 1
               'pick', 0, 'push', 2, 'jump_if',              # 3: if c goto 2
               'jump_fast', -1]
    
    program = ['push', 'A',          # 0x00
               'push', 0x09,         # 0x02
               'call',               # 0x04
               'push', 0,            # 0x05
               'jump_fast', -1,      # 0x07
               # def f(x) := x ? 9 : 8
               'pick', 1,            # 0x09   if x goto then
               'push', 0x12,         # 0x0a   
               'jump_if',            # 0x0c
               'push', 8,            # 0x0e   return 8
               'jump_fast', 0x14,    # 0x10   (goto [epilogue])
               'push', 9,            # 0x12   then: return 9
               'pick', 1,            # 0x14   [epilogue]
               'yank/2', 2, 2,       # 0x16
               'jump']
    
    p._cs += program
    p.thread()
    print p._ss

