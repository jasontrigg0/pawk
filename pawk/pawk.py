import sys
import argparse
import csv
import re
import itertools
import io
from jtutils import is_int, str_is_int, str_is_float, to_days, to_years, rand, GroupBy, threewise, process_cfg
from collections import Counter
import six
import codecs

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f","--infile")
    parser.add_argument("-b","--begin_code",nargs="*")
    parser.add_argument("-g","--grep_code")
    parser.add_argument("-p","--process_code", nargs="*", default="")
    parser.add_argument("-e","--end_code", nargs="*")
    parser.add_argument("-d","--delimiter", default=",")
    parser.add_argument("--output_delimiter",default=",")
    parser.add_argument("-m","--multiline",action="store_true",help="allow the incoming csv to have multiline fields, ie newlines in the middle of fields")
    parser.add_argument("--exceptions_allowed", action="store_true")
    parser.add_argument("--set", help="load a file with no header, storing each line as an element of a set")
    return parser

def internal_args():
    return {"input":None}

#####pyindent code#####
def pyindent(string):
    return '\n'.join(_pyindent_iter(string.split('\n')))

def _pyindent_iter(line_iter):
    indent_level = 0
    for l in (line_iter):
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
    for las, cur, nex in threewise(s):
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
    for las, cur, nex  in threewise(match_list):
        #TODO: replace with regex of exactly the characters allowed in python variable names (instead of strictly alphanumeric)?
        regex = "lambda[ 0-9A-Za-z]*:$"
        if las and re.findall(regex,las):
            continue
        elif re.findall(regex,cur):
            yield cur + " " + nex
        else:
            yield cur

#####end pyindent#####


#dict_and_row function to return a tuple with both unprocessed row and csv.reader() output
def csvlist_and_raw(f_in, delimiter, multiline=False):
    #default max field size of ~131k crashes at times
    csv.field_size_limit(sys.maxsize)
    if multiline:
        f1, f2 = itertools.tee(f_in) #use f1 to return
        reader = csv.reader(f_in, delimiter=delimiter)
        for row in reader:
            output = six.StringIO()
            wr = csv.writer(output, delimiter=delimiter)
            wr.writerow(row)
            l = output.getvalue().strip()
            yield l, row
    else:
        for l in f_in:
            l = l.strip("\r\n")
            row = csv2row(l, delimiter=delimiter)
            yield l, row

class CSVRow(list):
    #Goal: echo $VAR | pawk
    #should be a no-op

    #To this end, store a list of csv fields,
    #along with information about whether
    #each field should:
    # - have quotes forcibly added
    #eg: echo '"a"' | pawk -p 'print(r[0])'
    #>>> a
    #eg: echo '"a"' | pawk
    #>>> "a"
    # - should prevent quotes from being added
    #eg echo '"a' | pawk -p 'print(r[0])'
    #>>> "a
    #echo '"a' | pawk
    #>>> "a
    # - or should have quotes added as a regular csv file would
    #eg echo '"a' | pawk -p 'r[0]="b,c"; write_line(r)'
    #>>> "b,c"
    #this information is stored in self._addquote, which is a list
    #of True|False|None holding this information for each field

    #extending python's list as here:
    #https://stackoverflow.com/a/8180577
    def __init__(self):
        super(CSVRow, self)
        self._addquote = []
    def __add__(self,other):
        return CSVRow(list.__add__(self,other))
    def __mul__(self,other):
        return CSVRow(list.__mul__(self,other))
    def __getitem__(self, item):
        result = list.__getitem__(self, item)
        try:
            return CSVRow(result)
        except TypeError:
            return result
    def __setitem__(self,key,value):
        self._addquote.__setitem__(key,None)
        return list.__setitem__(self,key,value)
    def append(self,value):
        self._addquote.append(None)
        return list.append(self,value)
    def extend(self,L):
        self._addquote.extend([None]*(len(L)))
        return list.extend(self,L)
    def insert(self,i,x):
        self._addquote.insert(i,None)
        return list.insert(self,i,x)
    def remove(self,x):
        idx = list.index(self,x)
        self._addquote.pop(idx)
        return list.remove(self,x)
    def pop(self,*args):
        if args:
            self._addquote.pop(args[0])
            return list.pop(self,args[0])
        else:
            self._addquote.pop()
            return list.pop(self)
    def sort(self,cmp=None,key=None,reverse=False):
        raise Exception("Sorting not implemented for pawk CSVRow")
    def reverse(self):
        self._addquote.reverse()
        return list.reverse(self)

def csv2row(csv_string, delimiter=",", quote_char='"'):
    #take a string representing one line from a csv
    #parse that line into a list of fields
    #taking care to properly handle quoting of fields containing the delimiter
    #and nested quotes
    row = CSVRow()

    #raw pieces from splitting on the delimiter:
    #some of the pieces will need to be combined to make the fields
    #eg: "a,b",c,d
    #has 4 pieces but only three fields
    #pieces = ['"a','b"','c','d']
    pieces = csv_string.split(delimiter)

    #store the pieces in the field currently being built up
    current_field = []
    inquote = False

    for p in pieces:
        #starts and ends with single quote -- all other quotes come in pairs
        #@example: "a""b"
        #@example: """"
        #@example: ""
        re_START_AND_END = '^{quote_char}([^{quote_char}]|{quote_char}{quote_char})*{quote_char}$'.format(**vars())

        #ends with single quote -- all other quotes come in pairs
        #@example: abcd"
        #@example: ""cd"
        re_END = '^([^{quote_char}]|{quote_char}{quote_char})*{quote_char}$'.format(**vars())

        #starts with a single quote -- all other quotes come in pairs
        #@example: "abcd
        #@example: "ab""
        re_START = '^{quote_char}([^{quote_char}]|{quote_char}{quote_char})*$'.format(**vars())
        if not inquote and re.findall(re_START_AND_END,p):
            #correctly formatted quoted rows
            row.append(p[1:-1].replace(quote_char+quote_char,quote_char))
            row._addquote[-1] = True
        elif not inquote and re.findall(re_START,p):
            inquote = True
            current_field.append(p[1:])
        elif inquote and re.findall(re_END,p):
            inquote = False
            current_field.append(p[:-1])
            x = ",".join(current_field).replace(quote_char+quote_char,quote_char)
            row.append(x)
            row._addquote[-1] = True
            current_field = []
        elif inquote:
            current_field.append(p)
        elif not inquote:
            row.append(p)
            row._addquote[-1] = False
            current_field = []
    if inquote:
        row.append(quote_char + current_field[0])
        row += current_field[1:]
        row._addquote[-len(current_field):] = [False] * len(current_field)
    return row

def row2csv(rout, delimiter = ",", quote_char='"', preserve_csvrow_input = True):
    #preserve_csvrow_input used to preserve pawk input if the user didn't do anything to a line
    #ie piping through pawk should be a no-op by default
    def add_quotes(r,addquote=None):
        #addquote may be True (must add quotes)
        #False (must not add quotes -- eg was an invalid input)
        #or None (add as in a regular csv)
        if addquote is False:
            return r
        elif addquote:
            r = r.replace(quote_char,quote_char*2)
            return quote_char + r + quote_char
        elif delimiter in r or quote_char in r:
            r = r.replace(quote_char,quote_char*2)
            return quote_char + r + quote_char
        else:
            return r
    if isinstance(rout,CSVRow) and preserve_csvrow_input:
        return delimiter.join([add_quotes(str(r),addquote) for r,addquote in zip(rout,rout._addquote)])
    else:
        return delimiter.join([add_quotes(str(r)) for r in rout])

def write_line(rout, delimiter = ",", preserve_csvrow_input = False):
    s = row2csv(rout, delimiter, preserve_csvrow_input = preserve_csvrow_input)
    sys.stdout.write(s + "\n")

#"[""Rusted hardware and rivets"",""Raw hem detail""]"

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


def _check_is_list(cfg, x):
    if not isinstance(cfg[x],list):
        raise Exception(str(x) + " must be a list")

# @profile
def pawk(input_cfg=None):
    cfg = process_cfg(input_cfg, parser(), internal_args())
    if input_cfg and not cfg["input"] and not cfg["infile"]:
        raise Exception("Couldn't find input for pawk")
    if sys.stdin.isatty() and (not cfg["input"]) and (not cfg["infile"]):
        sys.stderr.write("WARNING: pawk using /dev/stdin as default input file (-f) but nothing seems to be piped in..." + "\n")

    #for non commandline, capture the sys.stdout
    backup = None
    if input_cfg: # not running from pawk script
        backup = sys.stdout
        sys.stdout = six.StringIO()

    if cfg["input"]:
        f_in = six.StringIO(cfg["input"])
    elif not cfg["infile"]:
        #https://stackoverflow.com/a/4554329
        sys.stdin = codecs.getreader('utf8')(sys.stdin.detach(), errors='ignore')
        f_in = sys.stdin
    else:
        if sys.version_info[0] >= 3:
            f_in = open(cfg["infile"],errors='ignore') #don't crash on invalid unicode
        else:
            f_in = open(cfg["infile"])
    if cfg["delimiter"] == "TAB":
        cfg["delimiter"] = '\t'
    elif cfg["delimiter"] == "\\t":
        cfg["delimiter"] = '\t'


    hdr = None
    has_exceptions = False
    has_printed_incomplete_line = False
    #jtrigg@20160102 try out only writing when there's no -p option
    # do_write = cfg["process_code"] and ("print" in cfg["process_code"] or "write_line" in cfg["process_code"])
    do_write = cfg["process_code"]
    if cfg["set"]:
        s = set(l.strip() for l in open(cfg["set"]))


    begin_code = None
    process_code = None
    end_code = None
    grep_code = None


    if cfg["begin_code"]:
        _check_is_list(cfg,"begin_code")
        begin_code = [pyindent(c) for c in cfg["begin_code"]]
        begin_code = [compile(code,'','exec') for code in begin_code]
    if cfg["grep_code"]:
        if isinstance(cfg["grep_code"],list):
            raise Exception("grep_code can't be list")
        #preprocess /.*/ syntax
        grep_code = gen_grep_code(cfg["grep_code"])
        grep_code = pyindent(grep_code)
        grep_code = compile(grep_code,'','eval')
    if cfg["process_code"]:
        _check_is_list(cfg,"process_code")
        process_code = [pyindent(c) for c in cfg["process_code"]]
        process_code = [compile(code,'','exec') for code in process_code]
    if cfg["end_code"]:
        _check_is_list(cfg,"end_code")
        end_code = [pyindent(c) for c in cfg["end_code"]]
        end_code = [compile(code,'','exec') for code in end_code]
    if begin_code:
        for code in begin_code:
            #NOTE: this code appears in a couple places
            #but it breaks if it's wrapped in a function because exec()
            #uses the existing environment
            try:
                exec(code)
            except:
                if backup:
                    sys.stdout = backup
                raise

    for i,(l,_csvlist) in enumerate(csvlist_and_raw(f_in, cfg["delimiter"], multiline=cfg["multiline"])):
        # sys.stderr.write(str(i) + "\n")
        # sys.stderr.write(str(l) + "\n")
        # raise
        r = _csvlist
        try:
            # print r,process_code
            if grep_code:
                try:
                    if not eval(grep_code):
                        continue
                except:
                    if backup:
                        sys.stdout = backup
                    raise
            if process_code:
                for code in process_code:
                    try:
                        exec(code)
                    except:
                        if backup:
                            sys.stdout = backup
                        raise
        except:
            if not cfg["exceptions_allowed"]:
                raise
            else:
                if not has_exceptions:
                    sys.stderr.write("WARNING: exception" + '\n')
                    has_exceptions = True
                continue
        if not do_write:
            if cfg["output_delimiter"] != cfg["delimiter"]:
                write_line(r, cfg["output_delimiter"], preserve_csvrow_input = False)
            else:
                write_line(r, cfg["output_delimiter"])

    if end_code:
        for code in end_code:
                try:
                    exec(code)
                except:
                    if backup:
                        sys.stdout = backup
                    raise

    #for sys.stdout
    if input_cfg: #not running from the pawk script
        out = sys.stdout.getvalue()
        sys.stdout = backup
        return out

def test_csv_identity():
    test_cases = ['a,",",b',
         '["Rusted hardware and rivets","Raw hem detail"]',
         '"[""Rusted hardware and rivets"",""Raw hem detail""]"',
         '"["Rusted hardware and rivets","Raw hem detail"]"',
         '""""',
         '"a","b","c"',
         '"a"b",c,d',
         '"""',
         '""a,"'
         ]
    for t in test_cases:
        row = csv2row(t)
        s = row2csv(row)
        assert(s == t)
