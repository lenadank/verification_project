## Platform Requirements ##

 * Python 2.7.x (default for Ubuntu Linux 12.04 and above, Mac OS X Lion and above)
 * Z3 (bundled, binaries for Ubuntu Linux 14.10)
 * PLY (bundled, architecture-independent)

## Running the Tool ##
`python relaxed_trace_analyzer.py filename`
to set the depth of the run (number of steps in the program) use -n option. for example:
`python relaxed_trace_analyzer.py filename -n 10`

## References ##

[1] Karbyshev et al., *Property-Directed Inference of Universal Invariants or Proving Their Absence*,
    in Computer Aided Verification (CAV) 2015.