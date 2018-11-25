#!/bin/bash
set -e
E=`dirname "$(readlink "$0")"`
src=$E/src benchmarks=$E/benchmarks
# Absence of universal invariant
echo "Absence of universal invariant"
python -u $src/relaxed_trace_analyzer.py -u $benchmarks/no-universal/sll-shared-tail.imp -n=10
python -u $src/relaxed_trace_analyzer.py -u $benchmarks/no-universal/sll-comb.imp -n=10
echo "******************************"
echo "Bug finding"
# Bug finding
python -u $src/relaxed_trace_analyzer.py -u $benchmarks/bugs/sll-insert-at-bug.imp -n=10
python -u $src/relaxed_trace_analyzer.py -u $benchmarks/bugs/sll-filter-bug.imp -n=10
python -u $src/relaxed_trace_analyzer.py -u $benchmarks/bugs/sll-insertion-sort-bug.imp -n=10
python -u $src/relaxed_trace_analyzer.py -u $benchmarks/bugs/sll-sorted-merge-bug.imp -n=10
