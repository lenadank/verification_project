## Platform Requirements ##

 * Python 2.7.x (default for Ubuntu Linux 12.04 and above, Mac OS X Lion and above)
 * Z3 (bundled, binaries for Ubuntu Linux 14.10)

############################
Z3 installation can be performed using this guide:

https://github.com/Z3Prover/z3
relevant section is:
Z3 bindings -> Python

## Running the Tool ##
`python relaxed_trace_analyzer.py filename`
to set the depth of the run (number of steps in the program) use -n option. for example:
`python relaxed_trace_analyzer.py filename -n 10`


executing on the sll-filter examples:
python relaxed_trace_analyzer.py Sindarin.PDR-Universal/benchmarks/sll-filter.imp -n=3


## References ##

[1] Karbyshev et al., *Property-Directed Inference of Universal Invariants or Proving Their Absence*,
    in Computer Aided Verification (CAV) 2015.

