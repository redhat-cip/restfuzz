#!/bin/env python

import hashlib

TRACE_COOKIE='Traceback (most recent call last):'


def collect_traceback(in_file):
    tb = []
    # Look for traceback
    while True:
        l = in_file.readline()
        if not l:
            return False
        if TRACE_COOKIE in l:
            break

    # Collect traceback
    tb_column = l.index(TRACE_COOKIE)
    while True:
        l = in_file.readline()
        if len(l) < tb_column:
            break
            #raise RuntimeError("Incorrect traceback")
        t = l[tb_column:].split()
        if not t or t[0] != 'File':
            break
        tb.append(l[tb_column:-1])
        l2 = in_file.readline()
        if len(l2) < tb_column:
            break
            #raise RuntimeError("Incorrect traceback")
        tb.append(l2[tb_column:-1])
    tb.append(l[tb_column:])

    if len(tb) < 2:
        return None

    # Compute traceback hash
    tb_hash = []
    for t in map(lambda x: x.split(), tb):
        if not t:
            break
        if t[0] == 'File':
            tb_hash.append("%s:%s-" % (t[1][1:-2], t[3][:-1]))
    tb_hash.append(l[tb_column:].split(':')[0])
    tb_hash_str = hashlib.md5("".join(tb_hash)).hexdigest()[:8]

    # Trace id
    trace_id = "%s %s" % (in_file.name, l[:tb_column])

    return tb_hash_str, trace_id, "\n".join(tb)


def main():
    # Extract traceback from log file
    import sys
    o = open(sys.argv[1])
    uniq_tb = set()
    while True:
        l = collect_traceback(o)
        if l is False:
            break
        elif l is None:
            continue
        if l[0] not in uniq_tb:
            print "Uniq tb:", l[1]
            print l[2]
        else:
            print "Known tb:", l[1]
        uniq_tb.add(l[0])

if __name__ == "__main__":
    main()
