import os
import subprocess

import numpy as np
from pymatgen import Structure, Lattice, Specie

from lammps import LammpsData, NPTSet, LammpsPotentials

supercell = (5, 5, 5)
a = 4.1990858 # From evaluation of potential
lattice = Lattice.from_parameters(a, a, a, 90, 90, 90)
mg = Specie('Mg', 1.4)
o = Specie('O', -1.4)
atoms = [mg, o]
sites = [[0, 0, 0], [0.5, 0.5, 0.5]]
structure = Structure.from_spacegroup(225, lattice, atoms, sites)


temperatures = np.linspace(300.0, 4000.0, 4)
directory = 'runs/thermal_expansion'
processors = '4'
lammps_command = 'lmp_mpi'


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


previous_structure = None
for temp in temperatures:
    temp_directory = os.path.join(directory, '{:.3f}'.format(temp))
    os.makedirs(temp_directory, exist_ok=True)

    if previous_structure is None:
        previous_structure = structure * supercell
    print('Initial Lattice Const:', previous_structure.lattice.a / 5)

    lammps_data = LammpsData.from_structure(previous_structure,
                                            potentials=lammps_potentials,
                                            include_charge=True)
    lammps_input = NPTSet(lammps_data,
                           temp_start=temp, temp_damp=1.0, press_damp=10.0,
                           user_lammps_settings=[
                               ('run', 10000),
                               ('dump', 'DUMP all custom 10000 mol.lammpstrj id type x y z vx vy vz mol'),
                               ('thermo', 100)
                           ] + mgo_potential_settings)
    print('Writing Lammps Input', temp)
    lammps_input.write_input(temp_directory)

    print('Running Lammps Calculation', temp)
    subprocess.call(['mpirun', '-n', processors, lammps_command, '-i', 'lammps.in'], cwd=temp_directory)

    print('Getting final structure', temp)
    lammps_final_data = LammpsData.from_file(os.path.join(temp_directory, 'final.data'))
    previous_structure = lammps_final_data.structure
