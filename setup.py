#!/usr/bin/env python
# pylint: disable=invalid-name,star-args

"""Setup file for PyExpLabSys"""

# 19:20 - 20:10
# 20:40 - 21:20
# 21:15 - 21:55

import codecs
import os
import re

from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))

###################################################################

NAME = "PyExpLabSys"
PACKAGES = find_packages(where=HERE)
META_PATH = os.path.join("PyExpLabSys", "__init__.py")
KEYWORDS = ["equipment", "serial", "drivers", "file parsers", "sockets"]
CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
    "Topic :: Scientific/Engineering",
    "Topic :: Scientific/Engineering :: Physics",
    "Topic :: System :: Hardware :: Hardware Drivers",
    "Topic :: Terminals :: Serial",
    "Topic :: Terminals :: Telnet",    
]
with open('requirements.txt') as file_:
    INSTALL_REQUIRES = [r.strip() for r in list(file_)]

###################################################################


def read(*parts):
    """
    Build an absolute path from *parts* and and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
    with codecs.open(os.path.join(HERE, *parts), "rb", "utf-8") as f:
        return f.read()


META_FILE = read(META_PATH)


def find_meta(meta):
    """
    Extract __*meta*__ from META_FILE.
    """
    meta_match = re.search(
        r"^__{meta}__ = ['\"]([^'\"]*)['\"]".format(meta=meta),
        META_FILE, re.M
    )
    if meta_match:
        return meta_match.group(1)
    raise RuntimeError("Unable to find __{meta}__ string.".format(meta=meta))


if __name__ == "__main__":
    setup(
        name=NAME,
        description=find_meta("description"),
        license=find_meta("license"),
        url=find_meta("uri"),
        version=find_meta("version"),
        author=find_meta("author"),
        author_email=find_meta("email"),
        maintainer=find_meta("author"),
        maintainer_email=find_meta("email"),
        keywords=KEYWORDS,
        long_description=read("README.rst"),
        packages=PACKAGES,
        zip_safe=False,
        classifiers=CLASSIFIERS,
        install_requires=INSTALL_REQUIRES,
    )
