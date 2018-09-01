from vm.stack_machine.exceptions import StackUnderflow




class Stack(list):
    
    def pop(self):
        if not self: raise StackUnderflow()
        return super(Stack, self).pop()
    
    def push(self, item):
        self.append(item)
        
    def push_many(self, items):
        self.extend(items)
        
    def pop_many(self, nitems):
        return [self.pop() for _ in xrange(nitems)]
        
    def top(self):
        if not self: raise StackUnderflow()
        return self[-1]
        
    def __repr__(self):
        return "[ %s ]" % (" | ".join(map(repr, self)))
    
    def __unicode__(self):
        return u"[ %s ]" % (u" | ".join(map(unicode, self)))
    
    __str__ = __unicode__
    
    def yank(self, length, depth=1):
        del self[-(length+depth):-depth]
        
    def pick(self, depth):
        self.push(self[-(depth+1)])
        

        
if __name__ == '__main__':
    ss = Stack()
    ss.push('A')
    ss.push_many(['B', 'C'])
    print ss
    
    