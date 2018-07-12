import math

import numpy as np
import pymatgen as pmg


class LammpsBox:
    def __init__(self, xhi, yhi, zhi, xlo=0, ylo=0, zlo=0, xy=0, xz=0, yz=0, angles=None):
        self.xlo = xlo
        self.xhi = xhi
        self.ylo = ylo
        self.yhi = yhi
        self.zlo = zlo
        self.zhi = zhi
        self.xy = xy
        self.xz = xz
        self.yz = yz

    @classmethod
    def from_lattice(cls, lattice, origin=(0, 0, 0)):
        """Create a lammps box and symetry operations to map coordinates to
        lammps box

        Warning if lattice is too skewed LAMMPS will not work with
        it. So my advice is to always prefer the conventional unit cell.
        """
        a, b, c = lattice.abc
        xlo, ylo, zlo = origin
        xhi = a + xlo
        if lattice.is_orthogonal:
            yhi = b + ylo
            zhi = c + zlo
            xy, xz, yz = (0, 0, 0)
            rot_matrix = np.eye(3)
        else:
            m = lattice.matrix
            xy = np.dot(m[1], m[0] / a)
            yhi = np.sqrt(b ** 2 - xy ** 2) + ylo
            xz = np.dot(m[2], m[0] / a)
            yz = (np.dot(m[1], m[2]) - xy * xz) / (yhi - ylo)
            zhi = np.sqrt(c ** 2 - xz ** 2 - yz ** 2) + zlo
            rot_matrix = np.linalg.solve([[xhi - xlo, 0, 0],
                                          [xy, yhi - ylo, 0],
                                          [xz, yz, zhi - zlo]], m)
        symmop = pmg.SymmOp.from_rotation_and_translation(rot_matrix, origin)
        return cls(xlo=xlo, xhi=xhi,
                   ylo=ylo, yhi=yhi,
                   zlo=zlo, zhi=zhi,
                   xy=xy, xz=xz, yz=yz), symmop

    @property
    def lattice(self):
        lx = self.xhi - self.xlo
        ly = self.yhi - self.ylo
        lz = self.zhi - self.zlo
        xy, xz, yz = self.xy, self.xz, self.yz
        a = lx
        b = math.sqrt(ly**2 + xy**2)
        c = math.sqrt(lz**2 + xz**2 + yz**2)
        alpha = math.degrees(math.acos((xy * xz + ly * yz) / (b * c)))
        beta = math.degrees(math.acos(xz / c))
        gamma = math.degrees(math.acos(xy / b))
        return pmg.Lattice.from_parameters(a, b, c, alpha, beta, gamma)

    def as_dict(self):
        return {
            'xlo': self.xlo, 'xhi': self.xhi,
            'ylo': self.ylo, 'yhi': self.yhi,
            'zlo': self.zlo, 'zhi': self.zhi,
            'xy': self.xy, 'xz': self.xz, 'yz': self.yz
        }

    def __str__(self):
        return (
            '{} {} xlo xhi\n'
            '{} {} ylo yhi\n'
            '{} {} zlo zhi\n'
            '{} {} {} xy xz yz'
        ).format(self.xlo, self.xhi, self.ylo, self.yhi, self.zlo, self.zhi,
                 self.xy, self.xz, self.yz)


class LammpsPotentials:
    def __init__(self, pair, symbol_indicies=None):
        self.symbol_indicies = symbol_indicies
        self.pair_parameters = pair

    def __str__(self):
        symbol_indicies = self.symbol_indicies
        if symbol_indicies is None: # Generate temporary symbol indicies
            counter = 1
            for (s1, s2) in self.pair_parameters:
                if s1 not in symbol_indicies:
                    symbol_indicies[s1] = counter
                    counter += 1
                if s2 not in symbol_indicies:
                    symbol_indicies[s2] = counter
                    counter += 1

        # Dumb enforcement that i < j
        def ordered_atom_type(a1_type, a2_type):
            if a1_type < a2_type:
                return "{} {}".format(a1_type, a2_type)
            return "{} {}".format(a2_type, a1_type)

        return '\n'.join([
            'PairIJ Coeffs\n',
            '\n'.join(['{} {}'.format(ordered_atom_type(symbol_indicies[s1], symbol_indicies[s2]), parameters) for (s1, s2), parameters in self.pair_parameters.items()]),
        ])
