# An input file to testing purposes
import os
import random
import subprocess
from functools import reduce, partial
from math import gcd

import numpy as np
from pymatgen import Lattice

from lammps import LammpsBox, LammpsData, NVESet
from mgo import structure, lammps_potentials, mgo_potential_settings

directory = 'runs/test'

def plane_from_miller_index(lattice, miller_index):
    if len(miller_index) != 3:
        raise ValueError('miller indicies must have 3 integers')

    for index in miller_index:
        if not isinstance(index, int):
            raise ValueError('All miller indicies must be integers')

    zero_indicies = [i for i, index in enumerate(miller_index) if index == 0]
    if len(zero_indicies) == 3:
        raise ValueError('Cannot have all three indicies at zero')

    non_zero_indicies = [i for i, index in enumerate(miller_index) if index != 0]
    common_divisor = reduce(gcd, [miller_index[i] for i in non_zero_indicies[1:]], miller_index[non_zero_indicies[0]])

    point = miller_index[non_zero_indicies[0]] * lattice.matrix[0] / common_divisor
    vectors = [lattice.matrix[i] for i in zero_indicies]

    for i in range(len(non_zero_indicies) - 1):
        i1, i2 = non_zero_indicies[i], non_zero_indicies[i+1]
        p1 = lattice.matrix[i1] * miller_index[i1] / common_divisor
        p2 = lattice.matrix[i2] * miller_index[i2] / common_divisor
        vectors.append(p1 - p2)

    normal = np.cross(vectors[0], vectors[1])
    normal = normal / np.linalg.norm(normal)
    return point, normal


def distance_from_miller_index(site, miller_index):
    point, normal = plane_from_miller_index(site.lattice, miller_index)
    distance = np.dot(point - site.coords, normal) / np.linalg.norm(normal)
    return distance


input_structure = structure * (20, 10, 10)
sorted_structure = input_structure.get_sorted_structure(key=partial(distance_from_miller_index, miller_index=[1, 0, 0]))

# solid_region = LammpsBox.from_lattice(Lattice(np.dot(np.array([0.5, 1, 1]) * np.eye(3), input_structure.lattice.matrix)))

lammps_data = LammpsData.from_structure(sorted_structure, potentials=lammps_potentials, include_charge=True, include_velocities=False)
lammps_set = NVESet(lammps_data,
                    user_lammps_settings=[
                        # ('region', [
                        #     'solid/region prism {xlo} {xhi} {ylo} {yhi} {zlo} {zhi} {xy} {xz} {xy}'.format(**solid_region.as_dict())
                        # ]),
                        ('group', [
                            'solid/group id <= {}'.format(len(input_structure) // 2),
                            'liquid/group subtract all solid/group'
                        ]),
                        ('velocity', [
                            'all create 1000 {}'.format(random.randint(0, 10000000))
                            # 'liquid/group create 1000 {}'.format(random.randint(0, 10000000))
                        ]),
                        ('fix', [
                            '1 liquid/group nve'
                        ]),
                        ('run', 1000),
                        ('dump', 'DUMP all custom 10 mol.lammpstrj id type x y z vx vy vz mol'),
                        ('thermo', 100),
                        ('write_data', 'restart.data pair ij')
                    ] + mgo_potential_settings)
lammps_set.write_input(os.path.join(directory))
subprocess.call(['mpirun', '-n', '4', 'lammps', '-i', 'lammps.in'], cwd=directory)
final_datafile = LammpsData.from_file(os.path.join(directory, 'restart.data'))
