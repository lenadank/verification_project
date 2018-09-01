#!/usr/local/bin/python2.7
# encoding: utf-8
'''
report -- generates a table containing benchmark results and mesurements
'''

import sys
import linker  # @UnusedImport

from argparse import ArgumentParser
from pattern.collection.basics import OrderedSet

class TabularFormat:
    US = lambda x: [x] #usual_suspects
    ROW_HEADERS = [("(1)", []),
                   ("concat",        US('sll-concat.imp')),
                   ("create",        US('sll-create.imp')),
                   ("delete",        US('sll-delete-at.imp')),
                   ("delete-all",    US('sll-deleteAll.imp')),
                   ("filter",        US('sll-filter.imp')),
                   ("insert-at",     US('sll-insert-at.imp')),
                   ("insert",        US('sll-insert.imp')),
                   ("merge",         US('sll-merge.imp')),
                   ("reverse",       US('sll-reverse.imp')),
                   ("split",         US('sll-split.imp')),
                   ("uf-find",       US('uf-find.imp')),
                   ("uf-union",      US('uf-union.imp')),
                   ("(2)", []),
                   ("sorted-insert", US('sll-sorted-insert.imp')),
                   ("sorted-merge",  US('sll-sorted-merge.imp')),
                   ("bubble-sort",   US('sll-bubble-sort.imp')),
                   ("insertion-sort",US('sll-insertion-sort.imp')),
                   ("(3)", []),
                   ("create",        US('dll-create.imp')),
                   ("delete",        US('dll-delete.imp')),
                   ("insert-at",     US('dll-insert-at.imp')),
                   ("(4)", []),
                   ("nested-flatten", US('sll-nested-flatten.imp')),
                   ("nested-split",   US('sll-nested-split.imp')),
                   ("overlaid-delete",US('sll-shared-delete.imp')),
                   ("ladder",         US('sll-ladder.imp')),
                   ("(5)", []),
                   ("is-cycle",       US('csll-is-cycle.imp')),
                   ("last",           US('csll-last.imp')),
                   ("unchain",        US('csll-unchain.imp')),
                   ("insert",         US('csll-insert.imp')),
                   ("delete",         US('csll-delete-at.imp')),
                   ("reverse",        US('csll-reverse.imp')),
                   #("(6)", []),
                   #("stack-2*push", US('sll-conc-stack-2push.imp')),
                   #("stack-1*push,1*pop", US('sll-conc-stack-1push-1pop.imp')),
                   ]
    COL_HEADERS = ['time', 'N', '#Z3', '#clauses']
    GROUP_HEADERS = {"(1)": "Singly-linked lists",
                     "(2)": "Sorted singly-linked lists",
                     "(3)": "Doubly-linked lists",
                     "(4)": "Composite linked-list structures",
                     "(5)": "Restricted cyclic singly-linked lists",
                     "(6)": "Concurrent singly-linked lists"}

    VARIANTS = ["[univ]", "[safe][univ]", "[opt][safe]"]

    MACROS = {"*TO*": r"\Tout", "*AF*": r"\Afail"}

    @classmethod
    def header(cls):
        return ["benchmark"] + ([""] + [x[:4] for x in cls.COL_HEADERS]) * len(cls.VARIANTS)

    @classmethod
    def keys(cls, benchmark):
        return [benchmark + suffix for suffix in cls.VARIANTS]

    @classmethod
    def fmt(cls, val):
        if val == "": return ""
        return {int: "%5d", float: "%4.1f", str: "%-2s", tuple: "%2d (%d)"}[type(val)] % val
    
    @classmethod
    def part(cls, docentry):
        status = docentry.get("status", None)
        if status == "unknown": docentry = {'time': "*AF*"}
        if status == "timeout": docentry = {'time': "*TO*"}
        if status == "valid":
            n = docentry.get('#clauses', None)
            nuniv = docentry.get('#univ_clauses', None)
            if n and nuniv: docentry['#clauses'] = (n, nuniv)
        return [docentry.get(col_header, "")
                for col_header in cls.COL_HEADERS]


def main():
    '''Command line options.'''

    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]

    # Setup argument parser
    a = ArgumentParser(description=program_shortdesc)
    a.add_argument("shelf_filename", help="path to benchmarks.shelf file", metavar="path",
                   nargs="?",
                   default="benchmarks.shelf")
    #a.add_argument('-p', action='store_true',
    #               help="print experimental data for partial diagrams")
    a.add_argument('--latex', action='store_true',
                   help="generate table data in LaTeX format")
    a.add_argument('--list-filenames', action='store_true',
                   help="list the names of participating benchmark files and exit")

    # Process arguments
    args = a.parse_args()
    
    if args.list_filenames:
        import re
        e = re.compile(r"\[.*\]$")
        filenames = OrderedSet(e.sub('', bench)
                               for (row_header, keys) in TabularFormat.ROW_HEADERS
                               for bench in keys)
        
        for f in filenames: print f
            
        raise SystemExit
    
    F = TabularFormat

    #if args.p:
    #    F.VARIANTS = ["[part][univ]"]

    import shelve
    sh = shelve.open(args.shelf_filename)

    from ui.text.table import Table
    t = Table()
    t.header = F.header()

    for (row_header, benchmarks) in F.ROW_HEADERS:
        for benchmark in benchmarks:
            parts = [F.part(sh.get(key, {})) for key in F.keys(benchmark)]
            vals = [x for part in parts for x in [""] + part]
            vals += [""] * (len(t.header) - len(vals) - 1)
            t.data += [[row_header] +
                       [F.fmt(val) for val in vals]]
        if not benchmarks:
            t.data += [[row_header] + [""] * (len(t.header)-1)]

    if args.latex:
        expand = lambda x: F.MACROS.get(x,x).replace("*", r"{\times}")
        for row in t.data:
            if F.GROUP_HEADERS.has_key(row[0]):
                print r"\groupsep{%s}" % F.GROUP_HEADERS[row[0]]
            else:
                print "%-20s" % expand(row[0]), " & ", \
                    " & ".join(map(expand, row[1:])), \
                    "\\\\"
    else:
        print t
            


if __name__ == "__main__":
    sys.exit(main())
