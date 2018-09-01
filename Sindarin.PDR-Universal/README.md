# Universal PDR #

This is a tool implementing IC3 for property-directed loop-invariant inference in the
context of shape analysis. The utility of this approach is demonstrated on several
pointer programs manipulating linked lists and a few other linked data structures.

## Platform Requirements ##

 * Python 2.7.x (default for Ubuntu Linux 12.04 and above, Mac OS X Lion and above)
 * Z3 (bundled, binaries for Ubuntu Linux 14.10)
 * PLY (bundled, architecture-independent)

## Running the Tool ##

### Basic Usage ###

`$ python epr_pdr.py [-u] filename`

  `-u`  Turns on universal quantifiers in invariant inference
        (by default, only quantifier-free invariants are searched)

  `-h`, `--help` Displays a help message 

The `benchmarks/` directory contains an extensive set of sample programs to run the
tool on. In particular, it includes all the benchmarks from [1].

 * Full functional specifications (the left-most block of columns in
   Table 1(a)) are placed directly in `benchmarks/`.
 * Specifications for memory-safety properties are placed in 
   `benchmarks/safety-only`.
 * Examples where the tool proves the absence of a universal invariant
   (Table 1(b)) are placed in `benchmarks/no-universal`.
 * Examples for finding bugs (Table 1(c)) are placed in
   `benchmarks/bugs`.

For convenience, the four shell scripts `reruns-*.sh` are provided.

 * `reruns-short.sh` runs all the successfully verified benchmarks that finish 
   in under 5 minutes.
 * `reruns-long.sh` runs those that take longer than 5 minutes.
 * `reruns-timeout.sh` runs the benchmarks that timed out (notice that there is
   no built-in timeout, hit Ctrl+C to stop a long-running benchmark).
 * `reruns-other.sh` runs benchmarks where the tool can find a bug (Table 1(c))
   or prove the absence of a universal invariant (Table 1(b)).

### Reporting Results ###

On successful finish, the tool would print the total running time of Z3 calls,
the number of iterations needed, and the size of the resulted invariant in clauses.
The results are also recorded in `benchmarks.shelf`, which is a Python shelve file
(not human-readable), and can then be summarized by running:

`$ python report.py`

Notice that the table only contains results of the experiments that are part of [1],
Table 1(a). Other executions are still recorded, but are not shown in the table produced by 
`report.py`.

## References ##

[1] Karbyshev et al., *Property-Directed Inference of Universal Invariants or Proving Their Absence*,
    in Computer Aided Verification (CAV) 2015.