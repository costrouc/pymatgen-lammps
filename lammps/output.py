import re

import numpy as np
from pymatgen.core import Structure

from .core import LammpsBox
from .inputs import LammpsData


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
        positions = timestep['atoms'][['x', 'y', 'z']].view(np.float).reshape(-1, 3)

        site_properties = {}
        if all(p in timestep['atoms'].dtype.names for p in ['vx', 'vy', 'vz']):
            site_properties['velocities'] = (timestep['atoms'][['vx', 'vy', 'vz']].view(np.float).reshape(-1, 3)).tolist()

        return Structure(lammps_box.lattice, species, positions, coords_are_cartesian=True, site_properties=site_properties)

    def get_forces(self, index):
        if self.lammps_dump is None:
            raise ValueError('Requires lammps dump to get forces in md simulation')

        timestep = self.lammps_dump.trajectories[index]
        if any(p not in timestep['atoms'].dtype.names for p in ['fx', 'fy', 'fz']):
            raise ValueError('Atom dumps must include fx fy fz to get forces')

        timestep = self.lammps_dump.trajectories[index]
        return timestep['atoms'][['fx', 'fy', 'fz']].view(np.float).reshape(-1, 3)

    def get_stress(self, index):
        if self.lammps_log is None:
            raise ValueError('Requires lammps log to get stress in md simulation')

        timestep = self.lammps_log.thermo_data[-1]
        if any(p not in timestep.dtype.names for p in ['pxy', 'pxz', 'pyz', 'pxx', 'pyy', 'pzz']):
            raise ValueError('Atom dumps must include pxy, pxz, pyz, pxx, pyy, pzz to get forces')

        pxx = timestep['pxx']
        pyy = timestep['pyy']
        pzz = timestep['pzz']
        pxy = timestep['pxy']
        pxz = timestep['pxz']
        pyz = timestep['pyz']

        return np.array([
            [pxx, pxy, pxz],
            [pxy, pyy, pyz],
            [pxz, pyz, pzz]
        ])

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

    def __init__(self, log_file="log.lammps"):
        """
        Args:
            log_file (string): path to the loag file
        """
        self.log_file = log_file
        self._parse_log()

    @property
    def timesteps(self):
        return self.thermo_data['step'].view(np.float)

    def _parse_log(self):
        """
        Parse the log file for the thermodynamic data.
        Sets the thermodynamic data as a structured numpy array with field names
        taken from the the thermo_style command.
        """
        thermo_data = []
        thermo_pattern = None
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
                format = re.search('thermo_style.+', line)
                if format and not thermo_data:
                    fields = format.group().split()[2:]
                    thermo_pattern_string = "\s*([0-9eE\.+-]+)" + "".join(
                        ["\s+([0-9eE\.+-]+)" for _ in range(len(fields) - 1)])
                    thermo_pattern = re.compile(thermo_pattern_string)
                if thermo_pattern:
                    if thermo_pattern.search(line):
                        m = thermo_pattern.search(line)
                        thermo_data.append(
                            tuple([float(x) for i, x in enumerate(m.groups())]))
        thermo_data_dtype = np.dtype([(str(fld), np.float64) for fld in fields])
        self.thermo_data = np.array(thermo_data, dtype=thermo_data_dtype)
