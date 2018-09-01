

class TracableError(Exception):
    
    def __init__(self, at=None):
        self.at = at
        


class SegmentationViolation(TracableError):
    
    def __init__(self, segment, address, at=None):
        super(SegmentationViolation, self).__init__(at)
        self.segment, self.address = segment, address

    def __str__(self):
        return "Segmentation violation: address=0x%x" % self.address



class StackUnderflow(TracableError):
    pass
