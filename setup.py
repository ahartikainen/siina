from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='siina',
    version='0.1.0a0',
    description='Pure Python library for Ground Penetrating Radar (GPR): IO, processing and visualization',
    #long_description='',
    url='https://github.com/ahartikainen/siina',
    author='Ari Hartikainen',
    license='Apache-2.0',
    classifiers=[
        'Development Statut :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Physics',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='ground penetrating radar gpr io',
    
    packages=find_packages(exclude=['docs', 'tests']),

    install_requires=[
        'numpy', 
        'scipy',
        ],
)
