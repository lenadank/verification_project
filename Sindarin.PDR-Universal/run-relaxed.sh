#!/bin/bash
set -e
E=`dirname "$(readlink "$0")"`
src=$E/src benchmarks=$E/benchmarks
for filename in $benchmarks/sll*; do
	python $src/relaxed_trace_analyzer.py $filename
done 
