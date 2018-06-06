# Lammps Wrapper

This is a package that I wrote to write input files for LAMMPS and
analyze them because I was not happy with the one built inside of
`pymatgen`. It has built in calculators for running many lammps
calculations in parallel (many short small LAMMPS calculations). 

Now that I have put some serious effort into my cython wrapper to
LAMMPS. I would recommend it instead. You get significantly better
performance and LAMMPS is now built into the python
process. [lammps-cython](https://gitlab.com/costrouc/lammps-cython).
