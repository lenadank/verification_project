
DEP = ["Sindarin.Fundament", "Sindarin.Compiler", "Sindarin.Architecture"]#, "Sindarin.Compiler", "Algonquin.Semantics"]

WORKSPACE_DIR = "../.."

import sys, os.path

here = os.path.dirname(__file__)

sys.path.append(here)

for proj in DEP:
    sys.path.append(os.path.join(here, WORKSPACE_DIR, proj, "src"))

# Set default encoding to UTF-8 for __repr__
# @@@ this is horrible!
if os.name == 'posix':
    reload(sys); sys.setdefaultencoding("utf-8") # @UndefinedVariable

import uniconsole  # @UnusedImport



if __name__ == '__main__':
    from filesystem.python.linker import Linker
    import ply
    EXTDEP = ply.__path__
    Linker(here, WORKSPACE_DIR, DEP, EXTDEP, startup="src/analyze.py")\
        .with_copy_to_root(["examples", "README"])\
        .zip(toplevel_dir='epr-verif')
