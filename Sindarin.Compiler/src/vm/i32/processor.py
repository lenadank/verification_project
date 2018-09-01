from state import MachineState
from instruction import Value, Instruction



class Processor(object):
    """
    Holds the current state and defines a transition function which modifies
    current state according to instruction.
    """
    
    def __init__(self, state=None):
        if state is None:
            self.state = MachineState()
        else:
            self.state = state
        self.modules = { }
        self.directive = self._directive()
    
    def execute(self, instructions):
        # Preload
        ip = 0
        while ip < len(instructions):
            i = instructions[ip]
            self.mark(self.state, ip, i)
            ip += 1

        # Run
        try:
            ip = 0
            while ip < len(instructions):
                i = instructions[ip]
                ip = self.transition(self.state, ip, i)
        except:
            print "RUNTIME ERROR in %r at ip=%d %r" % (self, ip, i)
            raise

    def _directive(self):
        def alloc(state, ip, p, size, ofs=None):
            if ofs is not None:
                size = state.buffers[size][ofs]
            state.pointers[p] = state.buffers.allocate(size)
        def free(state, ip, buf):
            del state.buffers[buf]
        
        def val(state, ip, buf, addr, val):
            state.buffers[buf][addr] = val
        def adr(state, ip, p, val):
            state.pointers[p] = val
        def ptr(state, ip, p, buf, addr):
            state.pointers[p] = state.buffers[buf][addr]
        
        def mov(state, ip, buf1, addr1, buf2, addr2):
            state.buffers[buf1][addr1] = state.buffers[buf2][addr2]

        def add(state, ip, buf1, addr1, buf2, addr2):
            state.buffers[buf1][addr1] += state.buffers[buf2][addr2]
        def sub(state, ip, buf1, addr1, buf2, addr2):
            state.buffers[buf1][addr1] -= state.buffers[buf2][addr2]
        def mul(state, ip, buf1, addr1, buf2, addr2):
            state.buffers[buf1][addr1] *= state.buffers[buf2][addr2]
        def div(state, ip, buf1, addr1, buf2, addr2):
            state.buffers[buf1][addr1] /= state.buffers[buf2][addr2]
        def mod(state, ip, buf1, addr1, buf2, addr2):
            state.buffers[buf1][addr1] %= state.buffers[buf2][addr2]
            
        def ceq(state, ip, buf1, addr1, buf2, addr2):
            state.buffers[buf1][addr1] = \
                (state.buffers[buf1][addr1] == state.buffers[buf2][addr2])
        def clt(state, ip, buf1, addr1, buf2, addr2):
            state.buffers[buf1][addr1] = \
                (state.buffers[buf1][addr1] < state.buffers[buf2][addr2])
        def not_(state, ip, buf1, addr1):
            state.buffers[buf1][addr1] = not state.buffers[buf1][addr1]

        def juc(state, ip, lbl):
            return lbl
        def jif(state, ip, buf, addr, lbl):
            if state.buffers[buf][addr] != 0:
                return lbl
            else:
                return ip + 1
            
        def ext(state, ip, exchange, module, entry):
            getattr(self.modules[module], entry)(state, state.buffers[exchange])

        I = Instruction
        return { I.ALLOC: alloc, I.FREE: free, I.VAL: val, I.ADR: adr, I.PTR: ptr,
                 I.MOV: mov,
                 I.ADD: add, I.SUB: sub, I.MUL: mul, I.DIV: div, I.MOD: mod,
                 I.JUC: juc, I.JIF: jif, I.CEQ: ceq, I.CLT: clt, I.NOT: not_,
                 I.EXT: ext
               }


    @staticmethod
    def mark(state, ip, instruction):
        if instruction[0] == Instruction.LBL:
            state.pointers[instruction[2][0]] = ip

    def transition(self, state, ip, instruction):
        
        def get(proto, args):
            get = { Value.IMMEDIATE: int,
                    Value.MEMORY: state.pointers.get,
                    Value.POINTER: str
                  }
            return map(lambda x,y: get[x](y), proto, args)
        
        
        mnemonic, proto, args = instruction
        vals = get(proto, args)
        
        if mnemonic == Instruction.LBL:
            pass
        elif mnemonic in self.directive:
            n = self.directive[mnemonic](state, ip, *vals)
            if n is not None:
                return n
        else:
            raise InvalidInstruction, instruction
        
        return ip + 1


class InvalidInstruction(KeyError):
    pass



if __name__ == "__main__":
    code = [("alloc", "pi", ("u", 16)),
            ("alloc", "pi", ("v", 4)),
            ("val", "mii", ("v", 0, 33)),
            ("val", "mii", ("v", 1, 3)),
            ("=", "mimi", ("u", 0, "v", 0)),
            ("+", "mimi", ("u", 0, "v", 1)),
            ("=", "mimi", ("u", 1, "v", 0)),
            ("/", "mimi", ("u", 1, "v", 1)),
            ("val", "mii", ("v", 2, 1)),
            ("lbl", "p", ("l",)),
            ("-", "mimi", ("v", 1, "v", 2)),
            ("*", "mimi", ("v", 0, "u", 1)),
            ("jif", "mim", ("v", 1, "l")),
            ("val", "mii", ("u", 3, 256)),
            ("val", "mii", ("u", 4, 96)),
            ("lbl", "p", ("euclid",)),
            ("=", "mimi", ("u", 5, "u", 3)),
            ("%", "mimi", ("u", 5, "u", 4)),
            ("=", "mimi", ("u", 3, "u", 4)),
            ("=", "mimi", ("u", 4, "u", 5)),
            ("jif", "mim", ("u", 5, "euclid")),
           ]
    p = Processor()
    p.execute(code)
    print p.state.buffers
    print p.state.pointers
