#!/bin/bash
set -e
E=`dirname $(realpath $0)` src=$E/src benchmarks=$E/benchmarks
# Absence of universal invariant
python $src/epr_pdr.py -u $benchmarks/no-universal/sll-shared-tail.imp
python $src/epr_pdr.py -u $benchmarks/no-universal/sll-comb.imp
# Bug finding
python $src/epr_pdr.py -u $benchmarks/bugs/sll-insert-at-bug.imp
python $src/epr_pdr.py -u $benchmarks/bugs/sll-filter-bug.imp
python $src/epr_pdr.py -u $benchmarks/bugs/sll-insertion-sort-bug.imp
python $src/epr_pdr.py -u $benchmarks/bugs/sll-sorted-merge-bug.imp
