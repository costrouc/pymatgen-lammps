# Lammps Wrapper

<table>
<tr>
  <td>Latest Release</td>
  <td><img src="https://img.shields.io/pypi/v/pymatgen-lammps.svg" alt="latest release"/></td>
</tr>
<tr>
  <td></td>
  <td><img src="https://anaconda.org/costrouc/pymatgen-lammps/badges/version.svg" alt="latest release" /></td>
</tr>
<tr>
  <td>License</td>
  <td><img src="https://img.shields.io/pypi/l/lammps-cython.svg" alt="license" /></td>
</tr>
<tr>
  <td>Build Status</td>
  <td> <a href="https://travis-ci.org/costrouc/pymatgen-lammps"> <img
src="https://api.travis-ci.org/costrouc/pymatgen-lammps.svg?branch=master"
alt="travis ci pipeline status" /> </a> </td>
</tr>
</table>


This is a package that I wrote to write input files for LAMMPS and
analyze them because I was not happy with the one built inside of
`pymatgen`. It has built in calculators for running many lammps
calculations in parallel (many short small LAMMPS calculations). 

Now that I have put some serious effort into my cython wrapper to
LAMMPS. I would recommend it instead. You get significantly better
performance and LAMMPS is now built into the python
process. [lammps-cython](https://github.com/costrouc/lammps-cython).
