from collections import OrderedDict
from pymatgen import Structure, Lattice, Specie

from lammps import LammpsData, LammpsPotentials, LammpsScript, LammpsInput, LammpsSet

supercell = (10, 10, 10)
lattice = Lattice.from_parameters(4.2, 4.2, 4.2, 90, 90, 90)
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

lammps_script = LammpsScript([
    ('clear', ''),
    ('units', 'metal'),
    ('dimension', 3),
    ('boundary', 'p p p'),
    ('atom_style', 'full'),
    ('pair_style', 'buck/coul/long 10.0'),
    ('kspace_style', 'ewald 1.0e-5'),
    ('read_data', 'hello.data'),
    ('fix', '1 all box/relax iso 0.0 vmax 0.001'),
    ('thermo', 10),
    ('minimize', '1.0e-10 1.0e-10 2000 100000'),
])

lammps_input = LammpsInput(lammps_script, lammps_data)
lammps_input.write_input('hello1')

lammps_set = LammpsSet('minimize', lammps_data, user_lammps_settings=[
    ('pair_style', 'buck/coul/long 10.0'),
    ('kspace_style', 'ewald 1.0e-5'),
])
lammps_set.write_input('hello2')
