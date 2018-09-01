
DEP = ["Sindarin.Fundament", "Sindarin.Compiler", "Sindarin.Architecture", "Sindarin.EPR"]

WORKSPACE_DIR = "../.."

import sys, os.path

here = os.path.dirname(__file__)

sys.path.append(here)

for proj in DEP:
    sys.path.append(os.path.join(here, WORKSPACE_DIR, proj, "src"))

for ext in ["ext/lib", "ext/lib/build"]:
    sys.path.append(os.path.join(here, WORKSPACE_DIR, ext))

# Set default encoding to UTF-8 for __repr__
# @@@ this is horrible!
if os.name == 'posix':
    reload(sys); sys.setdefaultencoding("utf-8") # @UndefinedVariable

import uniconsole  # @UnusedImport



if __name__ == '__main__':
    from filesystem.python.linker import Linker
    import ply, z3
    Linker(here, WORKSPACE_DIR, DEP)\
        .with_modules([ply, os.path.dirname(z3.__file__)])\
        .with_filters([lambda x: os.path.basename(x) not in ["United.zip", ".gitignore", ".git", "benchmarks.shelf", "paper", "spanning", "learning", "obsolete"]])\
        .with_copy_to_root(["benchmarks", "README.md", "LICENSE.txt", "paper/cav15/cav2015_submission_25.pdf"])\
        .with_symlink_to_root(["src/epr_pdr.py", "src/report.py",
                               "reruns-short.sh", "reruns-long.sh", "reruns-timeout.sh", "reruns-other.sh"])\
        .zip(toplevel_dir='univ-pdr')
