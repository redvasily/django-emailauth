#!/usr/bin/env python

from os import path, environ
from os.path import abspath, dirname, join
import sys

try:
    from extrapath import append_path, prepend_path
except ImportError:
    append_path = []
    prepend_path = []

example_dir = dirname(abspath(__file__))
emailauth_dir = dirname(dirname(example_dir))

prepend_path.extend([example_dir, emailauth_dir])

for p in reversed(prepend_path):
    sys.path.insert(0, p)

sys.path.insert(0, path.dirname(path.realpath(path.dirname(__file__))))

for p in append_path:
    sys.path.append(p)

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)
