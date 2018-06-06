# Not related to lammps the least bit but needed for sorting structures
from functools import reduce
from math import gcd

import numpy as np


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


def structure_to_neb_input(structure):
    return '\n'.join([
        '{}'.format(len(structure)),
        '\n'.join(['{} {} {} {}'.format(i+1, *site.coords) for i, site in enumerate(structure)])
    ])
