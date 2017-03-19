from pymatgen import Structure, Lattice, Specie

from lammps import LammpsData, LammpsPotentials, RelaxSet

supercell = (5, 5, 5)
a = 4.1990858 # From evaluation of potential
lattice = Lattice.from_parameters(a, a, a, 90, 90, 90)
mg = Specie('Mg', 1.4)
o = Specie('O', -1.4)
atoms = [mg, o]
sites = [[0, 0, 0], [0.5, 0.5, 0.5]]
structure = Structure.from_spacegroup(225, lattice, atoms, sites)


lammps_potentials = LammpsPotentials(pair={
    (mg, mg): '1309362.2766468062  0.104    0.0',
    (mg, o ): '9892.357            0.20199  0.0',
    (o , o ): '2145.7345           0.3      30.2222'
})

lammps_data = LammpsData.from_structure(structure * supercell, potentials=lammps_potentials, include_charge=True)

mgo_data = lammps_data
mgo_potential_settings = [
    ('pair_style', 'buck/coul/long 10.0'),
    ('kspace_style', 'ewald 1.0e-5'),
]
