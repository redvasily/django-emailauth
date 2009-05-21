from distutils.core import setup
import os

# Compile the list of packages available, because distutils doesn't have
# an easy way to do this.
packages, data_files = [], []
root_dir = os.path.dirname(__file__)
if root_dir:
   os.chdir(root_dir)

for dirpath, dirnames, filenames in os.walk('emailauth'):
   # Ignore dirnames that start with '.'
   for i, dirname in enumerate(dirnames):
       if dirname.startswith('.'): del dirnames[i]
   if '__init__.py' in filenames:
       pkg = dirpath.replace(os.path.sep, '.')
       if os.path.altsep:
           pkg = pkg.replace(os.path.altsep, '.')
       packages.append(pkg)
   elif filenames:
       prefix = dirpath[len('emailauth/'):] # Strip package prefix
       for f in filenames:
           data_files.append(os.path.join(prefix, f))

setup(name='django-emailauth',
    version='0.1',
    description='User email authentication application for Django',
    author='Vasily Sulatskov',
    author_email='redvasily@gmail.com',
    url='http://github.com/redvasily/django-emailauth/tree/master/',
    download_url='http://cloud.github.com/downloads/redvasily/django-emailauth/django-emailauth-0.1.tar.gz',
    package_dir={
        'emailauth': 'emailauth',
    },
    packages=packages,
    package_data={
        'emailauth': data_files
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
)
