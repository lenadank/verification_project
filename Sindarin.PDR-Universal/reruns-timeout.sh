#!/bin/bash
E=`dirname $(realpath $0)` src=$E/src benchmarks=$E/benchmarks
# (TO) 
python $src/epr_pdr.py $benchmarks/safety-only/uf-union.imp
# (TO) 
python $src/epr_pdr.py $benchmarks/safety-only/sll-insertion-sort.imp
# (TO) 
python $src/epr_pdr.py $benchmarks/safety-only/sll-shared-delete.imp
