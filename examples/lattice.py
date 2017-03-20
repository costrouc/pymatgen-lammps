import os
import subprocess

from lammps import RelaxSet, LammpsRun
from mgo import mgo_data, mgo_potential_settings


directory = 'runs/lattice_constant_0k'


def build():
    print('Creating Lammps Files')
    lammps_set = RelaxSet(mgo_data, user_lammps_settings=[
    ] + mgo_potential_settings)
    lammps_set.write_input(directory)


def run():
    print('Running Lammps Calculation')
    subprocess.call(['lammps', '-i', 'lammps.in'], cwd=directory, stdout=subprocess.PIPE)


def analysis():
    lammps_run = LammpsRun(
        os.path.join(directory, 'in.data'),
        lammps_log=os.path.join(directory, 'lammps.log'),
        lammps_dump=os.path.join(directory, 'mol.lammpstrj')
    )
    print('Final Lattice Constant')
    (a, b, c), (alpha, beta, gamma) = lammps_run.final_structure.lattice.lengths_and_angles
    print('Lengths', a / 5, b / 5, c / 5)
    print('Angles', alpha, beta, gamma)

def run_all():
    build()
    run()
    analysis()

# ====== Results ======
# Final Lattice Constant
# Lengths 4.19908 4.19908 4.19908
# Angles 90.0 90.0 90.0

if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'build':
        build()
    elif sys.argv[1] == 'run':
        run()
    elif sys.argv[1] == 'analysis':
        analysis()
    elif sys.argv[1] == 'all':
        run_all()
    else:
        print('must run command with build/run/analysis/all')
