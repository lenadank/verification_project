

class BasicInputOutputModule(object):
    
    def __init__(self):
        self.input_stream = []
        self.output_stream = []
    
    def read(self, state, exchange):
        if len(self.input_stream) > 0:
            exchange[0] = self.input_stream[0]
            del self.input_stream[0]
        else:
            exchange[0] = 0

    def write(self, state, exchange):
        self.output_stream.append(exchange[0])
        
    def eof(self, state, exchange):
        exchange[0] = (len(self.input_stream) == 0)
