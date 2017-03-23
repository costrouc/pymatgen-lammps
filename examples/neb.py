# Calculation of NEB Barrier of vacancy migration energy
import subprocess

from pymatgen import Structure, Lattice, Specie

from lammps import LammpsData, LammpsPotentials, NEBSet

supercell = (1, 1, 1)
a = 4.1990858 # From evaluation of potential
lattice = Lattice.from_parameters(a, a, a, 90, 90, 90)
mg = Specie('Mg', 1.4)
o = Specie('O', -1.4)
atoms = [mg, o]
sites = [[0, 0, 0], [0.5, 0.5, 0.5]]
structure = Structure.from_spacegroup(225, lattice, atoms, sites)

initial_structure = structure * supercell


directory = 'runs/neb'
initial_site = [0.0, 0.0, 0.0]
final_site = [0.0, 0.5, 0.5]

# Create Structures
first_structure = initial_structure
last_structure = initial_structure


lammps_potentials = LammpsPotentials(pair={
    (mg, mg): '1309362.2766468062  0.104    0.0',
    (mg, o ): '9892.357            0.20199  0.0',
    (o , o ): '2145.7345           0.3      30.2222'
})

mgo_potential_settings = [
    ('pair_style', 'buck/coul/long 10.0'),
    ('kspace_style', 'pppm 1.0e-5'),
]


lammps_data = LammpsData.from_structure(first_structure,
                                        potentials=lammps_potentials,
                                        include_charge=True)
lammps_set = NEBSet(lammps_data, last_structure, user_lammps_settings=[
] + mgo_potential_settings)
lammps_set.write_input(directory)
subprocess.call(['mpirun', '-n', '4', 'lmp_mpi', '-partition', '4x1', '-i', 'lammps.in'], cwd=directory)
