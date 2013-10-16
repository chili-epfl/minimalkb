 #!/usr/bin/env python
 # -*- coding: utf-8 -*-

import os
from distutils.core import setup

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='minimalKB',
      version='0.2',
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
      install_requires=['sqlite3'],
      package_dir = {'': 'src'},
      packages=['minimalkb'],
      scripts=['bin/minimalkb'],
      data_files=[('share/ontologies', ['share/ontologies/' + f for f in os.listdir('share/ontologies')]),
                  ('share/doc/minimalkb', ['LICENSE', 'README.md']),
                  ]
      )
