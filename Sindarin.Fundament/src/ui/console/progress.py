
import sys



def silly_progress(iterable):
    i = 0
    j = 0

    for item in iterable:
        yield item
        i += 1
        if i == 100:
            sys.stderr.write(".")
            i = 0
            j += 1
            if j == 100:
                sys.stderr.write("\n")
                j = 0
    sys.stderr.write("\n")
