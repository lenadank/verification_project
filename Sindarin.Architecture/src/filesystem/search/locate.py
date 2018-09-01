import subprocess
import shlex
import os.path
from filesystem.paths import CommonPath
from filesystem import FileNotFound as FileNotFoundBase



class SpotlightLocate(object):
    
    class FileNotFound(FileNotFoundBase):
        pass
    
    def __init__(self):
        self.mdfind_exe = CommonPath().find_file('mdfind')
        self.mdfind_args = ['-name']
        self.filters = []
        
    def __call__(self, filename):
        for match in self.iter(filename):
            return match
        raise self.FileNotFound, "cannot locate file using Spotlight: '%s'" % filename

    def iter(self, filename):
        args = self.mdfind_args
        if not isinstance(args, list): args = shlex.split(args)
        out = subprocess.check_output([self.mdfind_exe] + args + [filename])
        for fn in out.splitlines():
            if os.path.basename(fn) == filename:
                if all(f(fn) for f in self.filters):
                    yield fn

