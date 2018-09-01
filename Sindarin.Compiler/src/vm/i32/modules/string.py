
class BasicStringModule(object):
    
    def __init__(self):
        self.heap = { }
        self.uid = 0
        self.modules = { }
        
    def new(self, state, exchange):
        """
        String *string();
        """
        self.uid += 1
        self.heap[self.uid] = ""
        exchange[0] = self.uid

    def load(self, state, exchange):
        """
        void String::strload(char *);
        """
        e0, e1, e2, e3 = exchange
        uid = e0
        buf = state.buffers[e2]
        addr = e3
        while buf[addr] != 0:
            addr += 1
        s = "".join([chr(x) for x in buf[e3:addr]])
        self.heap[uid] = s
    
    def puts(self, state, exchange):
        """
        void String::puts();
        """
        uid = exchange[0]
        s = self.heap[uid]
        self.modules['io'].output_stream.append(s)
