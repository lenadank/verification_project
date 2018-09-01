#!/bin/bash
set -e
E=`dirname $(realpath $0)` src=$E/src benchmarks=$E/benchmarks
# (>300s) 
python $src/epr_pdr.py -u $benchmarks/sll-merge.imp
# (>300s) 
python $src/epr_pdr.py -u $benchmarks/sll-sorted-merge.imp
# (>2000s) 
python $src/epr_pdr.py -u $benchmarks/sll-insertion-sort.imp
# (>300s) 
python $src/epr_pdr.py $benchmarks/safety-only/dll-delete.imp
# (>300s) 
python $src/epr_pdr.py $benchmarks/safety-only/dll-insert-at.imp
# (>600s) 
python $src/epr_pdr.py -u $benchmarks/sll-nested-flatten.imp
# (>300s) 
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-nested-flatten.imp
# (>300s) 
python $src/epr_pdr.py -u $benchmarks/sll-nested-split.imp
# (>1000s)
python $src/epr_pdr.py -u $benchmarks/csll-unchain.imp
# (>300s, but only due to formula construction)
python $src/epr_pdr.py -u $benchmarks/csll-insert.imp
# (>300s, some freeze occurs after the construction of TR)
python $src/epr_pdr.py $benchmarks/safety-only/csll-insert.imp
# (>600s)
python $src/epr_pdr.py -u $benchmarks/csll-reverse.imp
