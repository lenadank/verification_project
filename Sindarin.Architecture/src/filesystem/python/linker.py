
import os.path


class Linker(object):
    
    EXECFILE_FUNC = "def e(fn): x = os.path.dirname(fn); f = file(fn); sys.path[:0]=[os.path.abspath(x)]; os.chdir(x); return f"
    STARTUP_FN_FUNC = "def s(p,d): return os.path.join(os.path.dirname(__file__), p, d)"
   
    PRUNE_SVN_FILTER = staticmethod(lambda x: os.path.basename(x) != '.svn')
    PRUNE_GIT_FILTER = staticmethod(lambda x: os.path.basename(x) != '.git')
   
    def __init__(self, wd, workspace_dir="../..", dep=[], extdep=[], startup=None):
        self.wd = wd
        self.workspace_dir = workspace_dir
        self.dep = dep
        self.extdep = extdep
        self.extdir = "ext/lib"
        self.startup = startup
        # Other configuration parameters
        self.copy_to_root = []    # list of filenames / directories to copy to root folder
        self.symlink_to_root = []    # list of filenames / directories to create symbolic links for in root folder
        self.filters = [self.PRUNE_SVN_FILTER, self.PRUNE_GIT_FILTER]   # predicates that must return 'True' for file to be copied
   
    def with_copy_to_root(self, filenames):
        self.copy_to_root.extend(filenames)
        return self
    
    def with_symlink_to_root(self, filenames):
        self.symlink_to_root.extend(filenames)
        return self
    
    def with_filters(self, filters):
        self.filters.extend(filters)
        return self
    
    def with_modules(self, modules):
        for mod in modules:
            if isinstance(mod, (str, unicode)):
                self.extdep += [mod]
            elif hasattr(mod, '__path__'):
                self.extdep += mod.__path__
            elif hasattr(mod, '__file__'):
                self.extdep += [mod.__file__]
            else:
                print "warning: module %s has neither __file__ nor __path__." % (mod,)
        return self
   
    def zip(self, output_filename="/tmp/United.zip", toplevel_dir=None):
        # Set up some required paths
        wd = os.path.abspath(self.wd)
        workspace = os.path.abspath(os.path.join(wd, self.workspace_dir))
        
        this_proj = os.path.basename(os.path.dirname(wd))
        if toplevel_dir is None:  # - root directory within the archive
            toplevel_dir = this_proj.split('.')[0] 
            
        # Add files to the zip
        import zipfile
        z = zipfile.ZipFile(output_filename, "w")
        def add_all(directory, archive_path, directory_prefix=''):
            for path, dirs, files in os.walk(directory):
                dirs[:] = [x for x in dirs if all(p(os.path.join(path, x))
                                                  for p in self.filters)]
                for filename in files:
                    fp = os.path.join(path, filename)
                    if all(p(fp) for p in self.filters):
                        z.write(fp, archive_path + "/" + fp[len(directory_prefix):])
        for proj in self.dep + [this_proj]:
            proj_dir = os.path.join(workspace, proj)
            add_all(proj_dir, toplevel_dir, workspace)
            
        for extdir in self.extdep:
            if os.path.isdir(extdir):
                add_all(extdir, toplevel_dir + "/" + self.extdir,
                        os.path.dirname(extdir))
            else:
                print "warning: currently only supporting packages as deps, sorry...  ('%s')" % (extdir,)
            
        for copy_item in self.copy_to_root:
            if os.path.isfile(copy_item):
                z.write(copy_item, toplevel_dir + "/" + os.path.basename(copy_item))
            elif os.path.isdir(copy_item):
                add_all(copy_item, toplevel_dir)
            else:
                print "warning: '%s' not found" % copy_item
        
        def write_link(z, filename, arcname):
            # http://www.mail-archive.com/python-list@python.org/msg34223.html
            zipInfo = zipfile.ZipInfo(arcname)
            zipInfo.create_system = 3
            # long type of hex val of '0xA1ED0000L',
            # symlink file type + permissions 0755  lrwxr-xr-x
            zipInfo.external_attr = 2716663808L
            z.writestr(zipInfo, filename)
        
        for symlink_item in self.symlink_to_root:
            if os.path.exists(symlink_item):
                write_link(z, os.path.join(proj, symlink_item), 
                           toplevel_dir + "/" + os.path.basename(symlink_item))
            else:
                print "warning: '%s' not found" % copy_item
        
        if self.startup is not None:
            z.writestr(toplevel_dir + "/" + os.path.basename(self.startup),
                       "import os.path, sys\n" +
                       self.EXECFILE_FUNC + "\n" +
                       self.STARTUP_FN_FUNC + "\n" +
                       "exec e(s('%s', '%s'))\n" % (this_proj, self.startup))
        
        z.close()
        print "Wrote '%s'" % (output_filename,)
