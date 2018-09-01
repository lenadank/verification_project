
import sys


class Tee(object):
    def __init__(self, filename, out=None):
        self.file = open(filename, "w")
        self.out = out or sys.stdout
    def write(self, text):
        self.out.write(text)
        self.file.write(text)
    def flush(self):
        self.out.flush()
        self.file.flush()


class FileNotFound(IOError):
    pass