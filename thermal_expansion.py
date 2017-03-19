import os
import subprocess

import numpy as np

from mgo import mgo_potential_settings, lammps_potentials, supercell, structure
from lammps import LammpsRun, LammpsData, NPTSet

temperatures = np.linspace(1e-3, 4000.0, 400)
directory = 'runs/thermal_expansion'


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
                           temp_start=temp, temp_damp=10.0, press_damp=100.0,
                           user_lammps_settings=[
                               ('run', 100000),
                               ('dump', 'DUMP all custom 10000 mol.lammpstrj id type x y z vx vy vz mol'),
                               # ('thermo_style', 'custom step vol temp ke pe etotal press pxy pxz pyz pxx pyy pzz'),
                               ('thermo', 100)
                           ] + mgo_potential_settings)
    print('Writing Lammps Input', temp)
    lammps_input.write_input(temp_directory)

    print('Running Lammps Calculation', temp)
    subprocess.call(['mpirun', '-n', '2', 'lammps', '-i', 'lammps.in'], cwd=temp_directory, stdout=subprocess.PIPE)
    print('Getting final structure', temp)
    lammps_run = LammpsRun(
        os.path.join(temp_directory, 'in.data'),
        lammps_log=os.path.join(temp_directory, 'lammps.log'),
        lammps_dump=os.path.join(temp_directory, 'mol.lammpstrj')
    )
    previous_structure = lammps_run.final_structure
