import os
import subprocess

from pymatgen.core import Specie, Structure, Lattice

from lammps import LammpsData, LammpsRun, LammpsPotentials, NPTSet

directory = 'runs/melting_point'
supercell = (10, 5, 5)
melting_point_guess = 3300 # Kelvin


a = 4.1990858 # From evaluation of potential
lattice = Lattice.from_parameters(a, a, a, 90, 90, 90)
mg = Specie('Mg', 1.4)
o = Specie('O', -1.4)
atoms = [mg, o]
sites = [[0, 0, 0], [0.5, 0.5, 0.5]]
structure = Structure.from_spacegroup(225, lattice, atoms, sites)
initial_structure = structure * supercell


lammps_potentials = LammpsPotentials(pair={
    (mg, mg): '1309362.2766468062  0.104    0.0',
    (mg, o ): '9892.357            0.20199  0.0',
    (o , o ): '2145.7345           0.3      30.2222'
})

mgo_potential_settings = [
    ('pair_style', 'buck/coul/long 10.0'),
    ('kspace_style', 'pppm 1.0e-5'),
]

# ============= Step A ===========
step_a_directory = os.path.join(directory, 'step_a')
lammps_data = LammpsData.from_structure(initial_structure,
                                        potentials=lammps_potentials,
                                        include_charge=True)
lammps_set = NPTSet(lammps_data,
                    temp_start=melting_point_guess, temp_damp=1.0, press_damp=10.0,
                    user_lammps_settings=[
                        ('run', 10000),
                        ('dump', 'DUMP all custom 10000 mol.lammpstrj id type x y z vx vy vz mol'),
                        ('thermo', 100),
                        ('write_data', 'restart.data pair ij')
                    ] + mgo_potential_settings)
lammps_set.write_input(step_a_directory)
subprocess.call(['mpirun', '-n', '2', 'lammps', '-i', 'lammps.in'], cwd=step_a_directory)
