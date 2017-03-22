import random
import os
import subprocess

from pymatgen.core import Specie, Structure, Lattice
import numpy as np

from lammps import LammpsData, LammpsRun, LammpsPotentials, NPTSet, NVESet, LammpsBox

directory = 'runs/melting_point'
supercell = np.array([5, 5, 5], dtype=np.int)
# Inital Guess 3150
# Iter 1: 3010 K
melting_point_guess = 3010 # Kelvin


a = 4.1990858 # From evaluation of potential
lattice = Lattice.from_parameters(a, a, a, 90, 90, 90)
mg = Specie('Mg', 1.4)
o = Specie('O', -1.4)
atoms = [mg, o]
sites = [[0, 0, 0], [0.5, 0.5, 0.5]]
structure = Structure.from_spacegroup(225, lattice, atoms, sites)


initial_structure = structure * (supercell * np.array([2, 1, 1], dtype=np.int))

lammps_potentials = LammpsPotentials(pair={
    (mg, mg): '1309362.2766468062  0.104    0.0',
    (mg, o ): '9892.357            0.20199  0.0',
    (o , o ): '2145.7345           0.3      30.2222'
})

mgo_potential_settings = [
    ('pair_style', 'buck/coul/long 10.0'),
    ('kspace_style', 'pppm 1.0e-5'),
]

# =============== Step A ==============
# NPT raise solid phase to estimated melting point
step_a_directory = os.path.join(directory, 'step_a')
lammps_data = LammpsData.from_structure(initial_structure, potentials=lammps_potentials, include_charge=True)
lammps_set = NPTSet(lammps_data,
                    temp_start=melting_point_guess, temp_damp=10.0, press_damp=100.0,
                    user_lammps_settings=[
                        ('run', 200000),
                        ('dump', 'DUMP all custom 10000 mol.lammpstrj id type x y z vx vy vz mol'),
                        ('thermo', 100),
                        ('write_data', 'restart.data pair ij')
                    ] + mgo_potential_settings)
lammps_set.write_input(step_a_directory)
# subprocess.call(['mpirun', '-n', '4', 'lammps', '-i', 'lammps.in'], cwd=step_a_directory)
step_a_final_dump = LammpsData.from_file(os.path.join(step_a_directory, 'restart.data'))


# ============ Step B ==============
# NVT Fix solid atoms, melt liquid atoms 2x melting point
solid_region = LammpsBox.from_lattice(Lattice(np.dot(np.array([0.5, 1, 1]) * np.eye(3), step_a_final_dump.structure.lattice.matrix)))

step_b_directory = os.path.join(directory, 'step_b')
lammps_data = LammpsData.from_structure(step_a_final_dump.structure, potentials=lammps_potentials, include_charge=True, include_velocities=True)
lammps_set = NVESet(lammps_data,
                    user_lammps_settings=[
                        ('region', [
                            'solid/region prism {xlo} {xhi} {ylo} {yhi} {zlo} {zhi} {xy} {xz} {xy}'.format(**solid_region.as_dict())
                        ]),
                        ('group', [
                            'solid/group region solid/region',
                            'liquid/group subtract all solid/group'
                        ]),
                        ('velocity', [
                            'liquid/group create {:.3f} {}'.format(melting_point_guess * 2, random.randint(0, 10000000))
                        ]),
                        ('fix', [
                            '1 liquid/group nvt temp {0:.3f} {0:.3f} 50.0'.format(melting_point_guess * 2)
                        ]),
                        ('run', 200000),
                        ('dump', 'DUMP all custom 10000 mol.lammpstrj id type x y z vx vy vz mol'),
                        ('thermo', 100),
                        ('write_data', 'restart.data pair ij')
                    ] + mgo_potential_settings)
lammps_set.write_input(step_b_directory)
# subprocess.call(['mpirun', '-n', '4', 'lammps', '-i', 'lammps.in'], cwd=step_b_directory)
step_b_final_dump = LammpsData.from_file(os.path.join(step_b_directory, 'restart.data'))


# ============= Step C ============
# NPT Fix solid atoms, cool liquid atoms to estimated melting point
# only allow expansion in x axis
solid_region = LammpsBox.from_lattice(Lattice(np.dot(np.array([0.5, 1, 1]) * np.eye(3), step_b_final_dump.structure.lattice.matrix)))

step_c_directory = os.path.join(directory, 'step_c')
lammps_data = LammpsData.from_structure(step_b_final_dump.structure, potentials=lammps_potentials, include_charge=True, include_velocities=True)
lammps_set = NVESet(lammps_data,
                    user_lammps_settings=[
                        ('region', [
                            'solid/region prism {xlo} {xhi} {ylo} {yhi} {zlo} {zhi} {xy} {xz} {xy}'.format(**solid_region.as_dict())
                        ]),
                        ('group', [
                            'solid/group region solid/region',
                            'liquid/group subtract all solid/group'
                        ]),
                        ('velocity', [
                            'liquid/group create {:.3f} {}'.format(melting_point_guess, random.randint(0, 10000000))
                        ]),
                        ('fix', [
                            'freeze solid/group setforce 0.0 0.0 0.0',
                            '1 liquid/group npt temp {0:.3f} {0:.3f} 50.0 x 0.0 0.0 1000.0'.format(melting_point_guess)
                        ]),
                        ('run', 200000),
                        ('dump', 'DUMP all custom 10000 mol.lammpstrj id type x y z vx vy vz mol'),
                        ('thermo', 100),
                        ('write_data', 'restart.data pair ij')
                    ] + mgo_potential_settings)
lammps_set.write_input(step_c_directory)
# subprocess.call(['mpirun', '-n', '4', 'lammps', '-i', 'lammps.in'], cwd=step_c_directory)
step_c_final_dump = LammpsData.from_file(os.path.join(step_c_directory, 'restart.data'))


# ============= Step D ============
# NPH Allow to equilibrium temperature
print('============== STEP D =============')

step_d_directory = os.path.join(directory, 'step_d')

lammps_data = LammpsData.from_structure(step_c_final_dump.structure, potentials=lammps_potentials, include_charge=True)
lammps_set = NVESet(lammps_data,
                    user_lammps_settings=[
                        ('velocity', 'all create {:.3f} {}'.format(melting_point_guess, random.randint(0, 10000000))),
                        ('fix', '1 all nph x 0.0 0.0 1000.0'),
                        ('run', 300000),
                        ('dump', 'DUMP all custom 10000 mol.lammpstrj id type x y z vx vy vz mol'),
                        ('thermo', 100),
                        ('write_data', 'restart.data pair ij')
                    ] + mgo_potential_settings)
lammps_set.write_input(step_d_directory)
subprocess.call(['mpirun', '-n', '4', 'lammps', '-i', 'lammps.in'], cwd=step_d_directory)
step_d_final_dump = LammpsData.from_file(os.path.join(step_d_directory, 'restart.data'))
