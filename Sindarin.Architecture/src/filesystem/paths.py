
import sys
import os.path
import copy
from filesystem import FileNotFound as FileNotFoundBase



class SearchPath(list):
    
    class FileNotFound(FileNotFoundBase):
        pass
    
    def find_file(self, filename):
        for location in self:
            if hasattr(location, 'find_file'):
                # delegate call to specialized location class
                try:
                    return location.find_file(filename)
                except location.FileNotFound:
                    pass
            else:
                full = os.path.join(location, filename)
                if os.path.exists(full):
                    return full
        else:
            raise self.FileNotFound, "can't find '%s' along path" % filename
        
    def __call__(self, filename):
        return self.find_file(filename)
    
    def join(self):
        return os.path.pathsep.join(self)
    
    def __add__(self, other):
        c = copy.copy(self)
        c.extend(other)
        return c


class SystemExecutablePath(SearchPath):
    
    def __init__(self):
        gather = os.environ["PATH"].split(os.path.pathsep)
        super(SystemExecutablePath, self).__init__(gather)
    
    def reapply(self):
        os.environ["PATH"] = self.join()


class BundleExecutablePath(SearchPath):
    """
    Specific to Mac OS X; Discovers the path to bundled executables.
    """
    
    RESOURCE_DIRECTORY = "Resources"
    BINARY_DIRECTORY = "MacOS"
    
    def __init__(self):
        R = self.RESOURCE_DIRECTORY
        B = self.BINARY_DIRECTORY
        gather = [os.path.join(os.path.dirname(fn), B)
                  for fn in sys.path
                  if os.path.basename(fn) == R]
        super(BundleExecutablePath, self).__init__(gather)


class CommonPath(SearchPath):
    """
    It is a combination of common search locations.
    """

    POSIX_PATH = ["/opt/local/bin", "/usr/local/bin"]
    
    def __new__(cls):
        path = SystemExecutablePath()
        if os.path.pathsep == ':':
            bp = BundleExecutablePath()
            path = (bp + path + cls.POSIX_PATH)
        return path
    


def find_closest(filename=None, indicator_file=None, start_at=None):
    if start_at:
        d = os.path.realpath(start_at)
    else:
        d = os.getcwd()
    while os.path.isdir(d):
        if indicator_file is not None and os.path.exists(os.path.join(d, indicator_file)):
            return d
        if filename is not None and os.path.exists(os.path.join(d, filename)):
            return os.path.join(d, filename)
        dt = os.path.dirname(d)
        if dt == d: break
        d = dt
