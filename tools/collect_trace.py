#!/usr/bin/python
import os
import sys
import re
import time
import hashlib

TRACE_COOKIE='Traceback (most recent call last):'

def get_date(line):
    # remove colorations
    line = re.sub('\x1b[^m]*m', '', line.strip())
    return time.mktime(time.strptime(line[:19], "%Y-%m-%d %H:%M:%S")) + int(line[20:23]) / 1000.0

def dump_traceback(output_dir, in_file, tb_column):
    tb = []
    # Collect traceback
    while True:
        l = in_file.readline()
        if len(l) < tb_column:
            raise RuntimeError("Incorrect traceback")
        t = l[tb_column:].split()
        if not t or t[0] != 'File':
            break
        tb.append(l[tb_column:-1])
        l2 = in_file.readline()
        if len(l2) < tb_column:
            raise RuntimeError("Incorrect traceback")
        tb.append(l2[tb_column:-1])
    tb.append(l[tb_column:])

    # Compute hash
    tb_hash = []
    for t in map(lambda x: x.split(), tb):
        if t[0] == 'File':
            tb_hash.append("%s:%s-" % (t[1][1:-2], t[3][:-1]))
    tb_hash.append(l[tb_column:].split(':')[0])

    # Trace id
    trace_id = "%s %s" % (in_file.name, re.sub('\x1b[^m]*m', '', l[:tb_column]))

    # Store
    fn = "%s/trace-%s.log" % (output_dir, hashlib.md5("".join(tb_hash)).hexdigest()[:8])
    if not os.path.isfile(fn):
        print "[+] new trace: %s" % fn
        of = open(fn, "w")
        of.write("\n".join(tb))
        of.write("\nFound in:\n")
    else:
        if trace_id in open(fn).read():
            return l
        of = open(fn, "a")
    of.write("* %s\n" % trace_id)
    of.flush()
    of.close()
    return l

def main(argv):
    try:
        output_dir = argv[1]
        in_file = open(argv[2], 'r')
    except IndexError:
        print "usage: %s output_dir log_file" % argv[0]
        return

    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    l = in_file.readline()
    while l != '':
        if TRACE_COOKIE in l:
            try:
                l = dump_traceback(output_dir, in_file, l.index(TRACE_COOKIE))
            except RuntimeError:
                l = in_file.readline()
        else:
            l = in_file.readline()

if __name__ == "__main__":
    main(sys.argv)
