#!/usr/bin/env python
import optparse
import csv
import sys
import re
import itertools

def readCL():
    usagestr = "%prog"
    parser = optparse.OptionParser(usage=usagestr)
    parser.add_option("-f","--infile")
    parser.add_option("-a","--add_list",help="csv of column names to add")
    parser.add_option("-c","--keep_list",help="csv of column names or indices. Can include currently non-existent columns")
    parser.add_option("-C","--drop_list",help="csv of column names or indices")
    parser.add_option("-b","--begin_code")
    parser.add_option("-g","--grep_code")
    parser.add_option("-p","--process_code")
    parser.add_option("-e","--exceptions_allowed", action="store_true")

    options, args = parser.parse_args()
    if not options.infile:
        f_in = sys.stdin
    else:
        f_in = open(options.infile)

    add_list = process_cut_csv(options.add_list)
    keep_list = process_cut_csv(options.keep_list)
    drop_list = process_cut_csv(options.drop_list)

    return f_in, add_list, keep_list, drop_list, options.begin_code, options.grep_code, options.process_code, options.exceptions_allowed



#utility functions
def is_int(var):
    return isinstance( var, ( int, long ) )

def str_is_float(var):
    try:
        f = float(var)
        if np.isnan(f):
            return False
        return True
    except:
        return False

def str_is_int(var):
    if not isinstance(var, str) and np.isnan(var):
        return False
    if re.findall("^\d+$",var):
        return True
    else:
        return False



#code to read multiline python
def groupby(l,n):
    return itertools.izip_longest(* ( (iter(l),) * n) )

def python_indent(string):
    return '\n'.join(_python_indent_iter(string.split('\n')))

def _python_indent_iter(line_iter):
    indent_level = 0
    for l in (line_iter):
        # print l

        #for i in range(10): if i % 2==0: print i; end; end; for i in range(5): print i; end; print 10
        # -->
        #["for i in range(10):", "if i % 2 == 0:", "print i;", "end;", "end;", "for i in range(5):", "print i;", "end;", "print 10"]
        l2 = [i for i in re.split("(:[ $]|;)",l) if i]
        py_lines = [''.join([i for i in g if i]).strip() for g in groupby(l2,2)]

        for l in py_lines:
            if l == "end;":
                indent_level -= 1
                continue
            if re.findall("^elif",l) or re.findall("^else",l) or re.findall("^except",l):
                indent_level -= 1
            yield ("    "*indent_level + l)
            if re.findall(":$",l):
                indent_level += 1





def process_cut_csv(i,delim=","):
    if i:
        i = i.split(',')
        return list(process_cut_list(i))
    else:
        return None

def process_cut_list(l, delim=","):
    for i in l:
        if "-" in i:
            x,y = i.split('-')
            for r in range(int(x),int(y)+1):
                yield r
        elif str_is_int(i):
            yield int(i)
        else:
            yield i


#fast-ish index dictionary:
#an ordered dictionary that can be accessed by string keys
#or index values
class IndexDict():
    def __init__(self, keyhash, values):
        self._keyhash = keyhash
        self._values = values
    def __setitem__(self, key, value):
        if is_int(key):
            #'key' is actually an index, 
            #must be an already existing item
            self._values[key] = value
        else:
            len_vals = len(self._values)
            index = self._keyhash.get(key,len_vals)
            if index >= len(self._values):
                self._keyhash[key] = len(self._values)
                self._values.append(value)
            else:
                self._values[index] = value
    def __getitem__(self, key):
        if isinstance(key, slice):
            return self._values.__getitem__(key)
        elif is_int(key):
            return self._values.__getitem__(key)
        elif key in self._keyhash:
            index = self._keyhash[key]
            return self._values[index]
        else:
            raise Exception("Couldn't find value {0} in IndexDict".format(key))
    def __str__(self):
        return dict((k,self._values[v]) for k,v in self._keyhash.items() if v < len(self._values[v])).__str__()
    def __len__(self):
        return len(self._values)
    def keys(self):
        return self._keyhash.keys()
    def values(self):
        return self._values


def write_line(rout):
    if isinstance(rout, IndexDict):
        rout = rout.values()
    sys.stdout.write(','.join(rout) + '\n')
    # csv.writer(sys.stdout, lineterminator= '\n').writerows([rout],quoting=csv.QUOTE_NONE)


def gen_grep_code(grep_code):
    if grep_code:
        grep_string = re.findall("^/(.*)/$",grep_code)
        if grep_string:
            grep_string = grep_string[0]
            grep_code = 're.findall("{grep_string}",",".join(l))'.format(**vars())
    return grep_code

def gen_outhdr(hdr, add_list, keep_list, drop_list):
    outhdr = hdr[:]
    if keep_list:
        if not add_list:
            add_list = [x for x in keep_list if x not in hdr and not is_int(x)]
        tmp_dict = dict(list(enumerate(outhdr)) + zip(outhdr,outhdr))
        outhdr = [tmp_dict[x] for x in keep_list]
    if add_list:
        outhdr += add_list
    if drop_list:
        outhdr = [x for ix,x in enumerate(outhdr) if (ix not in drop_list and x not in drop_list)]
    return outhdr


#main loop
# @profile
def process(f_in, add_list, keep_list, drop_list, begin_code, grep_code, process_code, exceptions_allowed):
    hdr = None
    has_exceptions = False
    do_write = process_code and ("print" in process_code or "write_line" in process_code)
    if begin_code:
        begin_code = compile(begin_code,'','exec')
    if grep_code:
        grep_code = compile(grep_code,'','eval')
    if process_code:
        process_code = compile(process_code,'','exec')

    if begin_code:
        exec(begin_code)
    for i,l in enumerate(csv.reader(f_in)):
        if not hdr:
            hdr = l[:]
            hdrhash = dict((ix,i) for i,ix in enumerate(hdr))
            outhdr = gen_outhdr(hdr, add_list, keep_list, drop_list)
            #r on the first line is just a dictionary from outhdr -> outhdr
            r = IndexDict(dict(zip(outhdr,range(len(outhdr)))),outhdr[:])
        else:
            if len(l) > len(hdr) and not do_write:
                print "WARNING: incomplete line"
            if not l:
                l = [''] * len(hdr)
            r = IndexDict(hdrhash,l) #IndexDict can be accessed by string or index (all keys must be strings)

        try:
            if grep_code and i>0 and not eval(grep_code):
                continue

            #do_write on every line including header
            #otherwise skip the header
            if do_write or (process_code and i>0):
                exec(process_code)
        except:
            if not exceptions_allowed:
                raise
            else:
                if not has_exceptions:
                    sys.stderr.write("WARNING: exception" + '\n')
                    has_exceptions = True
                continue

        if not do_write:
            rout = [str(r[h]) for h in outhdr]
            write_line(rout)



if __name__ == "__main__":
    f_in, add_list, keep_list, drop_list, begin_code, grep_code, process_code, exceptions_allowed = readCL()
    
    if begin_code:
        begin_code = python_indent(begin_code)
    if grep_code:
        grep_code = python_indent(grep_code)
    if process_code:
        process_code = python_indent(process_code)

    #preprocess /.*/ syntax
    grep_code = gen_grep_code(grep_code)

    process(f_in,add_list,keep_list,drop_list,begin_code,grep_code,process_code,exceptions_allowed)
