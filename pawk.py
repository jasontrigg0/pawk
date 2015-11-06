#!/usr/bin/env python
import sys
import optparse
import csv
import re
import itertools

def readCL():
    usagestr = "%prog"
    parser = optparse.OptionParser(usage=usagestr)
    parser.add_option("-f","--infile")
    parser.add_option("-b","--begin_code")
    parser.add_option("-g","--grep_code")
    parser.add_option("-p","--process_code", default="")
    parser.add_option("-e","--end_code")
    parser.add_option("-d","--delimiter", default=",")
    parser.add_option("--exceptions_allowed", action="store_true")
    parser.add_option("--set", help="load a file with no header, storing each line as an element of a set")

    options, args = parser.parse_args()
    if not options.infile:
        f_in = sys.stdin
    else:
        f_in = open(options.infile)

    return f_in, options.begin_code, options.grep_code, options.process_code, options.end_code, options.exceptions_allowed, options.delimiter, options.set



#####pyindent code#####
def pyindent(string):
    return '\n'.join(_pyindent_iter(string.split('\n')))

def _pyindent_iter(line_iter):
    indent_level = 0
    for l in (line_iter):
        # print l

        # substrings = _split_on_pystrings(l)
        #for i in range(10): if i % 2==0: print i; end; end; for i in range(5): print i; end; print 10
        # -->
        #["for i in range(10):", "if i % 2 == 0:", "print i;", "end;", "end;", "for i in range(5):", "print i;", "end;", "print 10"]

        #jtrigg@20150804: commenting below two lines to test out the _split function which should handle string literals better?
        # l2 = [i for i in re.split('(:[ $]|;[ ])',l) if i]
        # py_lines = [''.join([i for i in g if i]).strip() for g in _groupby(l2,2)]
        py_lines =  _split(l)
        py_lines = list(_paste_lambdas(py_lines))
        for l in py_lines:
            if l == "end;":
                indent_level -= 1
                continue
            if re.findall("^elif",l) or re.findall("^else",l) or re.findall("^except",l):
                indent_level -= 1
            yield ("    "*indent_level + l)
            if re.findall(":$",l):
                indent_level += 1
        # yield ("    "*indent_level + output_text)

def _split(s):
    """
    read a string representing python code and 
    'print "echo; echo;"'
    """
    out_list = []
    cur_substring = ""
    in_string_type = None
    for las, cur, nex in _threewise(s):
        cur_substring += cur
        if not in_string_type:
            if cur == '"' or cur == "'":
                # out_list.append((cur_substring,in_string_type))
                in_string_type = cur
                # cur_substring = cur
            elif (cur == ":" and nex == " "):
                out_list.append(cur_substring.strip())
                cur_substring = ""
            elif (cur == ";"):
                out_list.append(cur_substring.strip())
                cur_substring = ""
        else:
            if (cur == '"' or cur == "'") and las != "\\":
                #out_list.append((cur_substring,in_string_type))
                in_string_type = None
                #cur_substring = ""
    if cur_substring:
        out_list.append(cur_substring.strip())
    return out_list

        
def _paste_lambdas(match_list):
    """don't want newline after 'lambda x:'
    """
    for las, cur, nex  in _threewise(match_list):
        #TODO: replace with regex of exactly the characters allowed in python variable names (instead of strictly alphanumeric)?
        regex = "lambda[ 0-9A-Za-z]*:$"
        if las and re.findall(regex,las):
            continue
        elif re.findall(regex,cur):
            yield cur + " " + nex
        else:
            yield cur

def _threewise(iterable):
    """s -> (None, s0, s1), (s0, s1, s2), ... (sn-1, sn, None)
    example:
    for (las, cur, nex) in threewise(l):
    """
    a, b, c = itertools.tee(iterable,3)
    def prepend(val, l):
        yield val
        for i in l: yield i
    def postpend(val, l):
        for i in l: yield i
        yield val
    next(c,None)
    for _xa, _xb, _xc in itertools.izip(prepend(None,a), b, postpend(None,c)):
        yield (_xa, _xb, _xc)
            
        
#####end pyindent#####





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

def str_is_int(var):
    # if not isinstance(var, str) and np.isnan(var):
    #     return False
    if re.findall("^\d+$",var):
        return True
    else:
        return False

def is_int(var):
    return isinstance( var, ( int, long ) )

def str_is_float(var):
    try:
        f = float(var)
        # if np.isnan(f):
        #     return False
        return True
    except:
        return False



#dict_and_row function to return a tuple with both unprocessed row and csv.reader() output
#http://stackoverflow.com/questions/29971718/reading-both-raw-lines-and-dicionaries-from-csv-in-python
# class FileWrapper:
#   def __init__(self, f_in):
#     self.f_in = f_in
#     self.prev_line = None

#   def __iter__(self):
#     return self

#   def next(self):
#     self.prev_line = next(self.f_in).strip("\n\r")
#     return self.prev_line

# def csvlist_and_raw(f_in, delimiter):
#     wrapper = FileWrapper(f_in)
#     #default max field size of ~131k crashes at times
#     csv.field_size_limit(sys.maxsize)
#     reader = csv.reader(wrapper, delimiter=delimiter)
#     for csvlist in reader:
#         yield wrapper.prev_line, csvlist


#new csvlist and raw function
def csvlist_and_raw(f_in, delimiter):
    for line in f_in:
        line = line.rstrip("\n")
        yield line, csv.reader([line], delimiter=delimiter).next()


#jtrigg@20151106 indexdict not being used currently -- see pd.py for this purpose
#fast-ish index dictionary:
#an ordered dictionary that can be accessed by string keys
#or index values
# class IndexDict():
#     def __init__(self, keyhash, values):
#         self._keyhash = keyhash
#         self._values = values
#     def __setitem__(self, key, value):
#         if is_int(key):
#             #'key' is actually an index, 
#             #must be an already existing item
#             self._values[key] = value
#         else:
#             len_vals = len(self._values)
#             index = self._keyhash.get(key,len_vals)
#             if index >= len(self._values):
#                 self._keyhash[key] = len(self._values)
#                 self._values.append(value)
#             else:
#                 self._values[index] = value
#     def __getitem__(self, key):
#         if isinstance(key, slice):
#             return self._values.__getitem__(key)
#         elif is_int(key):
#             return self._values.__getitem__(key)
#         elif key in self._keyhash:
#             index = self._keyhash[key]
#             return self._values.__getitem__(index)
#         else:
#             raise Exception("Couldn't find value {0} in IndexDict".format(key))
#     def get(self, key, default=None):
#         try:
#             return self.__getitem__(key)
#         except:
#             if default is not None:
#                 return default
#             else:
#                 raise
#     def __str__(self):
#         return dict((k,self._values[v]) for k,v in self._keyhash.items() if v < len(self._values[v])).__str__()
#     def __len__(self):
#         return len(self._values)
#     def keys(self):
#         return self._keyhash.keys()
#     def values(self):
#         return self._values


def write_line(rout):
    # if isinstance(rout, IndexDict):
    #     rout = rout.values()
    # sys.stdout.write(','.join(rout) + '\n')
    # csv.writer(sys.stdout, lineterminator= '\n').writerows([rout],quoting=csv.QUOTE_NONE)
    csv.writer(sys.stdout, lineterminator= '\n').writerows([rout])

def proc_field(f):
    try:
        int(f)
        return int(f)
    except:
        pass
    return f

def gen_grep_code(grep_code):
    if grep_code:
        grep_string = re.findall("^/(.*)/$",grep_code)
        if grep_string:
            grep_string = grep_string[0]
            grep_code = 're.findall("{grep_string}",",".join(l))'.format(**vars())
    return grep_code

# @profile
def process(f_in, begin_code, grep_code, process_code, end_code, exceptions_allowed, delimiter,load_set):
    hdr = None
    has_exceptions = False
    has_printed_incomplete_line = False
    do_write = process_code and ("print" in process_code or "write_line" in process_code)
    if begin_code:
        begin_code = compile(begin_code,'','exec')
    if grep_code:
        grep_code = compile(grep_code,'','eval')
    if process_code:
        process_code = compile(process_code,'','exec')
    if end_code:
        end_code = compile(end_code,'','exec')
    if begin_code:
        exec(begin_code)

    if load_set:
        s = set(l.strip() for l in open(load_set))
        
    for i,(l,_csvlist) in enumerate(csvlist_and_raw(f_in, delimiter = delimiter)):
        r = _csvlist
        try:
            # print r,process_code
            if grep_code and not eval(grep_code):
                continue
            if process_code:
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
            write_line(r)
            
    if end_code:
        exec(end_code)
            

# def soup(s):
#     from bs4 import BeautifulSoup
#     return BeautifulSoup(s, "lxml")

# def soup_get(s,index_list, default=""):
#     if not isinstance(index_list, list):
#         index_list = [index_list]
#     try:
#         out = soup(s).findAll("body")[0].contents[0]
#         for i in index_list:
#             out = out.contents[i]
#         return out
#     except:
#         return default
    
if __name__ == "__main__":
    f_in, begin_code, grep_code, process_code, end_code, exceptions_allowed, delimiter, load_set = readCL()
    #following two lines solve 'Broken pipe' error when piping
    #script output into head
    from signal import signal, SIGPIPE, SIG_DFL
    signal(SIGPIPE,SIG_DFL)

    if begin_code:
        begin_code = pyindent(begin_code)
    if grep_code:
        grep_code = pyindent(grep_code)
    if process_code:
        process_code = pyindent(process_code)
    #preprocess /.*/ syntax
    grep_code = gen_grep_code(grep_code)

    process(f_in,begin_code,grep_code,process_code,end_code,exceptions_allowed,delimiter,load_set)
