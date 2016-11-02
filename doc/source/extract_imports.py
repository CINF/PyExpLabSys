
import re
import sys
import os
from collections import Counter
from os import path


HERE = path.abspath(path.dirname(__file__))
SOURCEDIR = path.join(HERE, '..', 'PyExpLabSys')
# This set of builtin modules created by joining together
# sys.builtin_module_names and pkgutil.iter_modules as per
# http://stackoverflow.com/questions/8370206/
# how-to-get-a-list-of-built-in-modules-in-python
BUILTIN_MODULES = set([
    '_ast', '_bisect', '_codecs', '_collections', '_datetime', '_elementtree', '_functools', '_heapq', '_imp', '_io', '_locale', '_md5', '_operator', '_pickle', '_posixsubprocess', '_random', '_sha1', '_sha256', '_sha512', '_signal', '_socket', '_sre', '_stat', '_string', '_struct', '_symtable', '_thread', '_tracemalloc', '_warnings', '_weakref', 'array', 'atexit', 'binascii', 'builtins', 'errno', 'faulthandler', 'fcntl', 'gc', 'grp', 'itertools', 'marshal', 'math', 'posix', 'pwd', 'pyexpat', 'select', 'spwd', 'sys', 'syslog', 'time', 'unicodedata', 'xxsubtype', 'zipimport', 'zlib', '__future__', '_bootlocale', '_collections_abc', '_dummy_thread', '_weakrefset', 'abc', 'base64', 'bisect', 'codecs', 'collections', 'copy', 'copyreg', 'distutils', 'encodings', 'fnmatch', 'functools', 'genericpath', 'hashlib', 'heapq', 'hmac', 'imp', 'importlib', 'io', 'keyword', 'linecache', 'locale', 'ntpath', 'operator', 'os', 'posixpath', 'random', 're', 'reprlib', 'rlcompleter', 'shutil', 'site', 'sre_compile', 'sre_constants', 'sre_parse', 'stat', 'struct', 'tarfile', 'tempfile', 'token', 'tokenize', 'types', 'warnings', 'weakref', 'CDROM', 'DLFCN', 'IN', 'TYPES', '_sysconfigdata_m', '_bz2', '_codecs_cn', '_codecs_hk', '_codecs_iso2022', '_codecs_jp', '_codecs_kr', '_codecs_tw', '_crypt', '_csv', '_ctypes', '_ctypes_test', '_curses', '_curses_panel', '_dbm', '_decimal', '_gdbm', '_hashlib', '_json', '_lsprof', '_lzma', '_multibytecodec', '_multiprocessing', '_opcode', '_sqlite3', '_ssl', '_testbuffer', '_testcapi', '_testimportmultiple', '_testmultiphase', '_tkinter', 'audioop', 'cmath', 'fpectl', 'mmap', 'nis', 'ossaudiodev', 'parser', 'readline', 'resource', 'termios', 'xxlimited', '_compat_pickle', '_compression', '_markupbase', '_osx_support', '_pydecimal', '_pyio', '_sitebuiltins', '_strptime', '_sysconfigdata', '_threading_local', 'aifc', 'antigravity', 'argparse', 'ast', 'asynchat', 'asyncio', 'asyncore', 'bdb', 'binhex', 'bz2', 'cProfile', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmd', 'code', 'codeop', 'colorsys', 'compileall', 'concurrent', 'configparser', 'contextlib', 'crypt', 'csv', 'ctypes', 'curses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis', 'doctest', 'dummy_threading', 'email', 'enum', 'filecmp', 'fileinput', 'formatter', 'fractions', 'ftplib', 'getopt', 'getpass', 'gettext', 'glob', 'gzip', 'html', 'http', 'idlelib', 'imaplib', 'imghdr', 'inspect', 'ipaddress', 'json', 'lib2to3', 'logging', 'lzma', 'macpath', 'macurl2path', 'mailbox', 'mailcap', 'mimetypes', 'modulefinder', 'multiprocessing', 'netrc', 'nntplib', 'nturl2path', 'numbers', 'opcode', 'optparse', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform', 'plistlib', 'poplib', 'pprint', 'profile', 'pstats', 'pty', 'py_compile', 'pyclbr', 'pydoc', 'pydoc_data', 'queue', 'quopri', 'runpy', 'sched', 'selectors', 'shelve', 'shlex', 'signal', 'sitecustomize', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver', 'sqlite3', 'ssl', 'statistics', 'string', 'stringprep', 'subprocess', 'sunau', 'symbol', 'symtable', 'sysconfig', 'tabnanny', 'telnetlib', 'test', 'textwrap', 'this', 'threading', 'timeit', 'tkinter', 'trace', 'traceback', 'tracemalloc', 'tty', 'turtle', 'typing', 'unittest', 'urllib', 'uu', 'uuid', 'venv', 'wave', 'webbrowser', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc', 'zipapp', 'zipfile', 'easy_install', 'pip', 'pkg_resources', 'setuptools', 'wheel', 'Queue']
)

RES = [
    re.compile(r' *import ([\w\.]*) *.*'),
    re.compile(r' *from ([\w\.]*) import .*'),
]


def find_module_in_line(line):
    """Find importes in a line"""
    for regexp in RES:
        match = regexp.match(line)
        if match:
            found = match.group(1)

            # Skip dependencies from PyExpLabSys
            for skip in ('PyExpLabSys', '.'):
                if found.startswith(skip):
                    return

            # Skip builtin modules
            base_module = found.split('.')[0]
            if base_module in BUILTIN_MODULES:
                return

            return base_module

def find_modules(source_file):
    """Find imports"""
    modules = Counter()
    with open(source_file) as file_:
        for line in file_:
            module = find_module_in_line(line)
            if module:
                modules[module] += 1
    return modules


def main():
    """The main function"""
    source_files = []
    for base, _, files in os.walk(SOURCEDIR):
        for file_ in files:
            if file_.endswith('.py'):
                source_files.append(path.join(base, file_))

    modules = Counter()
    for source_file in source_files:
        modules += find_modules(source_file)

    from pprint import pprint
    pprint(modules)
    print(len(modules))
    print(sum(modules.values()))

    
main()
