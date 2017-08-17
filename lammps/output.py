import re

import numpy as np
from pymatgen.core import Structure

from .core import LammpsBox
from .inputs import LammpsData


def fields_view(array, fields):
    return array.getfield(np.dtype(
        {name: array.dtype.fields[name] for name in fields}
    ))


class LammpsRun(object):
    """ Parse Lammps Run

    """
    def __init__(self, lammps_data, lammps_log=None, lammps_dump=None):
        # self.lammps_script would be nice to have as well
        self.lammps_data = LammpsData.from_file(lammps_data)
        self.lammps_log = LammpsLog(lammps_log) if lammps_log else None
        self.lammps_dump = LammpsDump(lammps_dump) if lammps_dump else None
        self._generate_maps()

    def _generate_maps(self):
        self._atom_index = []
        for atom in self.initial_structure:
            self._atom_index.append(atom.specie)

    def get_structure(self, index):
        if self.lammps_dump is None:
            raise ValueError('Requires lammps dump to get structures in md simulation')

        timestep = self.lammps_dump.trajectories[index]
        if any(p not in timestep['atoms'].dtype.names for p in ['x', 'y', 'z']):
            raise ValueError('Atom dumps must include x y z positions to get structures')

        lammps_box = LammpsBox(**timestep['box'])
        species = self._atom_index
        positions = np.array(fields_view(timestep['atoms'], ['x', 'y', 'z']).tolist())

        site_properties = {}
        if all(p in timestep['atoms'].dtype.names for p in ['vx', 'vy', 'vz']):
            site_properties['velocities'] = fields_view(timestep['atoms'], ['vx', 'vy', 'vz']).tolist()

        return Structure(lammps_box.lattice, species, positions, coords_are_cartesian=True, site_properties=site_properties)

    def get_forces(self, index):
        if self.lammps_dump is None:
            raise ValueError('Requires lammps dump to get forces in md simulation')
        return self.lammps_dump.get_forces(index)

    def get_stress(self, index):
        if self.lammps_log is None:
            raise ValueError('Requires lammps log to get stress in md simulation')
        return self.lammps_log.get_stress(index)

    def get_energy(self, index):
        if self.lammps_log is None:
            raise ValueError('Requires lammps log to get stress in md simulation')
        return self.lammps_log.get_energy(index)

    @property
    def final_structure(self):
        return self.get_structure(-1)

    @property
    def final_forces(self):
        return self.get_forces(-1)

    @property
    def final_stress(self):
        return self.get_stress(-1)

    @property
    def initial_structure(self):
        return self.lammps_data.structure


class LammpsDump(object):
    """
    Parse the lammps dump file to extract useful info about the system.
    """

    def __init__(self, filename):
        self.filename = filename
        self._parse_dump()

    @property
    def timesteps(self):
        return np.array([t['timestep'] for t in self.trajectories])

    def get_forces(self, index):
        timestep = self.trajectories[index]
        if any(p not in timestep['atoms'].dtype.names for p in ['fx', 'fy', 'fz']):
            raise ValueError('Atom dumps must include fx fy fz to get forces')

        return np.array(fields_view(timestep['atoms'], ['fx', 'fy', 'fz']).tolist())

    def _parse_dump(self):
        """
        parse dump file
        """
        self.trajectories = []

        with open(self.filename) as f:
            trajectory = {}
            while True:
                line = f.readline()
                if "ITEM: TIMESTEP" in line:
                    line = f.readline()
                    trajectory['timestep'] = int(line)
                elif "ITEM: NUMBER OF ATOMS" in line:
                    line = f.readline()
                    trajectory['natoms'] = int(line)
                elif "ITEM: BOX BOUNDS" in line:
                    # determine format
                    if "xy xz yz" in line: # triclinic format
                        xlo, xhi, xy = list(map(float, f.readline().split()))
                        ylo, yhi, xz = list(map(float, f.readline().split()))
                        zlo, zhi, yz = list(map(float, f.readline().split()))
                    else:
                        xlo, xhi = list(map(float, f.readline().split()))
                        ylo, yhi = list(map(float, f.readline().split()))
                        zlo, zhi = list(map(float, f.readline().split()))
                        xy, xz, yz = 0, 0, 0
                    trajectory['box'] = {
                        'xlo': xlo, 'xhi': xhi,
                        'ylo': ylo, 'yhi': yhi,
                        'zlo': zlo, 'zhi': zhi,
                        'xy': xy, 'xz': xz, 'yz': yz
                    }
                elif "ITEM: ATOMS" in line:
                    labels = line.split()[2:]
                    formats = [np.int64] * 2 + [np.float64] * (len(labels) - 2)

                    atom_items = []
                    for i in range(trajectory['natoms']):
                        line_data = f.readline().split()
                        line_data = [int(_) for _ in line_data[:2]] + [float(_) for _ in line_data[2:]]
                        atom_items.append(tuple(line_data))
                    trajectory['atoms'] = np.array(atom_items, dtype={'names': labels, 'formats': formats})
                    trajectory['atoms'] = np.sort(trajectory['atoms'], order='id')
                    self.trajectories.append(trajectory)
                    trajectory = {}
                else:
                    break


class LammpsLog(object):
    """
    Parser for LAMMPS log file.
    """

    def __init__(self, log_file="lammps.log"):
        """
        Args:
            log_file (string): path to the loag file
        """
        self.log_file = log_file
        self._parse_log()

    @property
    def timesteps(self):
        return self.thermo_data['step'].view(np.float)

    def get_stress(self, index):
        timestep = self.thermo_data[index]
        if any(p not in timestep.dtype.names for p in ['Pxy', 'Pxz', 'Pyz', 'Pxx', 'Pyy', 'Pzz']):
            raise ValueError('Atom dumps must include Pxy, Pxz, Pyz, Pxx, Pyy, Pzz to get stress')

        pxx = timestep['Pxx']
        pyy = timestep['Pyy']
        pzz = timestep['Pzz']
        pxy = timestep['Pxy']
        pxz = timestep['Pxz']
        pyz = timestep['Pyz']

        return np.array([
            [pxx, pxy, pxz],
            [pxy, pyy, pyz],
            [pxz, pyz, pzz]
        ])

    def get_energy(self, index):
        timestep = self.thermo_data[index]
        if 'TotEng' not in timestep.dtype.names:
            raise ValueError('Atom dumps mult include TotEng to get total energy')
        return float(timestep['TotEng'])

    def _parse_log(self):
        """
        Parse the log file for the thermodynamic data.
        Sets the thermodynamic data as a structured numpy array with field names
        taken from the the thermo_style command.
        """
        thermo_int_styles = {
            'step', 'elapsed', 'elaplong', 'spcpu',
            'part', 'atoms', 'nbuild', 'ndanger'
        }

        thermo_header = []
        thermo_types = []
        thermo_data = []
        inside_thermo_block = False
        read_thermo_header = False
        with open(self.log_file, 'r') as logfile:
            for line in logfile:
                # timestep, the unit depedns on the 'units' command
                time = re.search('timestep\s+([0-9]+)', line)
                if time and not thermo_data:
                    self.timestep = float(time.group(1))

                # total number md steps
                steps = re.search('run\s+([0-9]+)', line)
                if steps and not thermo_data:
                    self.nmdsteps = int(steps.group(1))

                # logging interval
                thermo = re.search('thermo\s+([0-9]+)', line)
                if thermo and not thermo_data:
                    self.interval = float(thermo.group(1))

                # thermodynamic data, set by the thermo_style command
                if "Memory usage per processor = " in line or \
                   "Per MPI rank memory allocation" in line:
                    inside_thermo_block = True
                    read_thermo_header = False
                elif inside_thermo_block:
                    if not read_thermo_header:
                        if len(thermo_header) == 0:
                            thermo_header = line.split()
                            thermo_types = [np.int if h.lower() in thermo_int_styles else np.float for h in thermo_header]
                        else:
                            if thermo_header != line.split():
                                raise ValueError('Cannot parse log file where thermo_style changes from one run to next. We suggest doing multiple seperate calculations')
                        read_thermo_header = True
                    elif "Loop time of " in line:
                        inside_thermo_block = False
                        read_thermo_header = False
                    else:
                        thermo_data.append(tuple(t(v) for t, v in zip(thermo_types, line.split())))
        thermo_data_dtype = np.dtype([(header, nptype) for header, nptype in zip(thermo_header, thermo_types)])
        self.thermo_data = np.array(thermo_data, dtype=thermo_data_dtype)
