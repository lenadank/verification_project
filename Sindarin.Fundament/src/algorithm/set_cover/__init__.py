

class NoSetCoverAtAll(Exception):
    
    def __init__(self, uncoverable_elements):
        self.uncoverable_elements = uncoverable_elements
        
    def __str__(self):
        return "no cover for %r" % self.uncoverable_elements

