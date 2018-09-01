#!/bin/bash
set -e
E=`dirname $(realpath $0)` src=$E/src benchmarks=$E/benchmarks
python $src/epr_pdr.py -u $benchmarks/sll-concat.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-concat.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-concat.imp
python $src/epr_pdr.py -u $benchmarks/sll-create.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-create.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-create.imp
python $src/epr_pdr.py -u $benchmarks/sll-delete-at.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-delete-at.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-delete-at.imp
python $src/epr_pdr.py -u $benchmarks/sll-deleteAll.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-deleteAll.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-deleteAll.imp
python $src/epr_pdr.py -u $benchmarks/sll-filter.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-filter.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-filter.imp
python $src/epr_pdr.py -u $benchmarks/sll-insert-at.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-insert-at.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-insert-at.imp
python $src/epr_pdr.py -u $benchmarks/sll-insert.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-insert.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-insert.imp
# (>300s) python $src/epr_pdr.py -u $benchmarks/sll-merge.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-merge.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-merge.imp
python $src/epr_pdr.py -u $benchmarks/sll-reverse.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-reverse.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-reverse.imp
python $src/epr_pdr.py -u $benchmarks/sll-split.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-split.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-split.imp
python $src/epr_pdr.py -u $benchmarks/uf-find.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/uf-find.imp
python $src/epr_pdr.py    $benchmarks/safety-only/uf-find.imp
python $src/epr_pdr.py -u $benchmarks/uf-union.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/uf-union.imp
# (TO) python $src/epr_pdr.py $benchmarks/safety-only/uf-union.imp
python $src/epr_pdr.py -u $benchmarks/sll-sorted-insert.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-sorted-insert.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-sorted-insert.imp
# (>300s) python $src/epr_pdr.py -u $benchmarks/sll-sorted-merge.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-sorted-merge.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-sorted-merge.imp
python $src/epr_pdr.py -u $benchmarks/sll-bubble-sort.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-bubble-sort.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-bubble-sort.imp
# (>2000s) python $src/epr_pdr.py -u $benchmarks/sll-insertion-sort.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-insertion-sort.imp
# (TO) python $src/epr_pdr.py $benchmarks/safety-only/sll-insertion-sort.imp
python $src/epr_pdr.py -u $benchmarks/dll-create.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/dll-create.imp
python $src/epr_pdr.py    $benchmarks/safety-only/dll-create.imp
python $src/epr_pdr.py -u $benchmarks/dll-delete.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/dll-delete.imp
# (>300s) python $src/epr_pdr.py $benchmarks/safety-only/dll-delete.imp
python $src/epr_pdr.py -u $benchmarks/dll-insert-at.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/dll-insert-at.imp
# (>300s) python $src/epr_pdr.py $benchmarks/safety-only/dll-insert-at.imp
# (>600s) python $src/epr_pdr.py -u $benchmarks/sll-nested-flatten.imp
# (>300s) python $src/epr_pdr.py -u $benchmarks/safety-only/sll-nested-flatten.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-nested-flatten.imp
# (>300s) python $src/epr_pdr.py -u $benchmarks/sll-nested-split.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-nested-split.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-nested-split.imp
python $src/epr_pdr.py -u $benchmarks/sll-shared-delete.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-shared-delete.imp
# (TO) python $src/epr_pdr.py $benchmarks/safety-only/sll-shared-delete.imp
python $src/epr_pdr.py -u $benchmarks/sll-ladder.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/sll-ladder.imp
python $src/epr_pdr.py    $benchmarks/safety-only/sll-ladder.imp
python $src/epr_pdr.py -u $benchmarks/csll-is-cycle.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/csll-is-cycle.imp
python $src/epr_pdr.py    $benchmarks/safety-only/csll-is-cycle.imp
python $src/epr_pdr.py -u $benchmarks/csll-last.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/csll-last.imp
python $src/epr_pdr.py    $benchmarks/safety-only/csll-last.imp
# (>1000s) python $src/epr_pdr.py -u $benchmarks/csll-unchain.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/csll-unchain.imp
python $src/epr_pdr.py    $benchmarks/safety-only/csll-unchain.imp
# (>300s) python $src/epr_pdr.py -u $benchmarks/csll-insert.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/csll-insert.imp
# (>300s, freeze happens) python $src/epr_pdr.py $benchmarks/safety-only/csll-insert.imp
# (>600s) python $src/epr_pdr.py -u $benchmarks/csll-reverse.imp
python $src/epr_pdr.py -u $benchmarks/csll-delete-at.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/csll-delete-at.imp
python $src/epr_pdr.py    $benchmarks/safety-only/csll-delete-at.imp
python $src/epr_pdr.py -u $benchmarks/safety-only/csll-reverse.imp
python $src/epr_pdr.py    $benchmarks/safety-only/csll-reverse.imp

