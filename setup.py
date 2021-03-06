 #!/usr/bin/env python
 # -*- coding: utf-8 -*-

import os
from distutils.core import setup

#import __version__
execfile('src/minimalkb/__init__.py')

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='minimalKB',
      version=__version__,
      license='BSD',
      description='A SQLite-backed minimalistic knowledge based for robotic application. Mostly KB-API conformant.',
      long_description=readme(),
      classifiers=[
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
      ],
      author='Séverin Lemaignan',
      author_email='severin.lemaignan@epfl.ch',
      url='https://github.com/severin-lemaignan/minimalkb',
      requires=['pysqlite', 'rdflib'],
      package_dir = {'': 'src'},
      packages=['minimalkb', 'minimalkb/backends', 'minimalkb/services'],
      scripts=['bin/minimalkb'],
      data_files=[('share/ontologies', ['share/ontologies/' + f for f in os.listdir('share/ontologies')]),
                  ('share/doc/minimalkb', ['LICENSE', 'README.md']),
                  ]
      )
