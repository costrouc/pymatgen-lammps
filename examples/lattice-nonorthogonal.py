"""Lammps does not like simulations that are very skewed.

Thus always use the conventional unit cell.
"""


# Calculation the Lattice Constant at 0 Kelvin
import os
import subprocess

from pymatgen import Structure, Lattice, Specie
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from pmg_lammps import RelaxSet, LammpsRun, LammpsData, LammpsPotentials


supercell = (5, 5, 5)
a = 4.1990858 # From evaluation of potential
lattice = Lattice.from_parameters(a, a, a, 90, 90, 90)
mg = Specie('Mg', 1.4)
o = Specie('O', -1.4)
atoms = [mg, o]
sites = [[0, 0, 0], [0.5, 0.5, 0.5]]
structure = Structure.from_spacegroup(225, lattice, atoms, sites)
spga = SpacegroupAnalyzer(structure)
structure = spga.get_primitive_standard_structure()
print(structure)

directory = 'runs/lattice'


lammps_potentials = LammpsPotentials(pair={
    (mg, mg): '1309362.2766468062  0.104    0.0',
    (mg, o ): '9892.357            0.20199  0.0',
    (o , o ): '2145.7345           0.3      30.2222'
})

lammps_data = LammpsData.from_structure(
    structure * supercell,
    potentials=lammps_potentials, include_charge=True)

mgo_potential_settings = [
    ('pair_style', 'buck/coul/long 10.0'),
    ('kspace_style', 'pppm 1.0e-5'),
]

print('======= Creating Lammps Files =========')
lammps_set = RelaxSet(lammps_data, user_lammps_settings=[
    ('box', 'tilt large')
] + mgo_potential_settings)
lammps_set.write_input(directory)

print('======= Running Lammps Calculation ========')
subprocess.call(['lammps', '-i', 'lammps.in'], cwd=directory)


print('====== Analyzing Calculation =========')
lammps_run = LammpsRun(
    os.path.join(directory, 'initial.data'),
    lammps_log=os.path.join(directory, 'lammps.log'),
    lammps_dump=os.path.join(directory, 'mol.lammpstrj')
)


print(lammps_run.final_structure.lengths_and_angles)
print('Final Lattice Constant')
(a, b, c), (alpha, beta, gamma) = lammps_run.final_structure.lattice.lengths_and_angles
print('Lengths', a / 5, b / 5, c / 5, 'Angstroms')
print('Angles', alpha, beta, gamma)
