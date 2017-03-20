from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='lammps',
    version='0.0.1',
    description='Lammps Wrapper',
    long_description=long_description,
    url=None,
    author='Chris Ostrouchov',
    author_email='chris.ostrouchov+lammps_wrapper@gmail.com',
    classifiers=[
        'Programming Language :: Python :: 3.5',
    ],
    keywords='lammps wrapper',
    packages=find_packages(exclude=['docs', 'tests', 'notebooks']),
    install_requires=[
        'pymatgen',
    ],
    # entry_points={
    #     'console_scripts': [
    #         'lammps_wrapper=mattoolkit.__main__:main'
    #     ]
    # }
)
