
class BasicCollectionModule(object):
    
    def __init__(self):
        self.heap = { }
        self.uid = 0
        
    def arraylist(self, state, exchange):
        """
        List *arraylist();
        """
        self.uid += 1
        self.heap[self.uid] = []
        exchange[0:2] = [self.uid, 0]

    def size(self, state, exchange):
        """
        int List::size();
        """
        uid, e1 = exchange
        exchange[0] = len(self.heap[uid])

    def add(self, state, exchange):
        """
        void List::add(void *item);
        """
        e0, e1, e2, e3 = exchange
        uid = e0
        self.heap[uid].append((e2, e3))
    
    def add_at(self, state, exchange):
        """
        void List::add_at(int index, void *item);
        """
        uid, e1, index, item0, item1 = exchange
        lst = self.heap[uid]
        i = index
        lst[i:i] = [(item0, item1)]
    
    def get(self, state, exchange):
        """
        void *List::get(int index);
        """
        uid, e1, index = exchange
        exchange[0:2] = self.heap[uid][index]
    
    def remove(self, state, exchange):
        """
        void Iterator::remove();
        """
        iter_uid, e3 = exchange
        iter = self.heap[iter_uid]
        lst = self.heap[iter[0]]
        i = iter[1]
        if not (1 <= i < len(lst)):
            raise RuntimeError, "invalid iterator position for remove()"
        del lst[i-1]

    def iterator(self, state, exchange):
        """
        Iterator *List::iterator();
        """
        e0, e1 = exchange
        uid = e0
        self.uid += 1
        self.heap[self.uid] = (uid, 0)
        exchange[0:2] = [self.uid, 0]
     
    def hasNext(self, state, exchange):
        """
        bool Iterator::hasNext();
        """
        e0, e1 = exchange
        iter_uid = e0
        list_uid, index = self.heap[iter_uid]
        exchange[0] = (index < len(self.heap[list_uid]))

    def next(self, state, exchange):
        """
        void *Iterator::next();
        """
        e0, e1 = exchange
        iter_uid = e0
        list_uid, index = self.heap[iter_uid]
        self.heap[iter_uid] = (list_uid, index+1)
        exchange[0:2] = self.heap[list_uid][index]

