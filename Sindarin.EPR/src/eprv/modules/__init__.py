'''
The module system is responsible for locating dependencies.
Modules contain axioms and other definitions typically stored in .fol files.
'''
import os.path
from filesystem.paths import SearchPath



class ModuleSystem(object):
    
    class ModuleNotFound(SearchPath.FileNotFound):
        pass
    
    def __init__(self, module_search_path=SearchPath()):
        self.module_search_path = module_search_path
        
    def find_module_source(self, module_name):
        try:
            location = self.module_search_path.find_file(module_name)
        except SearchPath.FileNotFound:
            raise self.ModuleNotFound, "cannot locate module '%s'" % (module_name,)
        if os.path.isdir(location):
            return filter(os.path.isfile, 
                          self._find_recursively(location))
        
    def find_module_sources_from_annotations(self, annotations):
        """
        The annotations are pairs [(key, value), ...].
        A 'uses' annotation is interpreted as a list of modules to import.
        """
        def get():
            for key, value in annotations:
                if key == 'uses':
                    for word in value.split():
                        if word:
                            for src_fn in self.find_module_source(word):
                                yield src_fn
        return list(get())
        
    def _find_recursively(self, root_path, criterion=lambda x: True):
        for root, dirs, files in os.walk(root_path):
            for basename in dirs + files:
                fullname = os.path.join(root, basename)
                yield fullname
