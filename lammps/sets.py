import os
import json
import random

from .inputs import LammpsInput, LammpsScript

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class LammpsSet(LammpsInput):
    def __init__(self, config_filename, lammps_data, data_filename="in.data"):
        with open(os.path.join(MODULE_DIR, 'sets', config_filename + ".json")) as f:
            lammps_script = json.load(f, object_pairs_hook=LammpsScript)
        lammps_script['read_data'] = data_filename
        super().__init__(lammps_script, lammps_data)


class RelaxSet(LammpsSet):
    def __init__(self, lammps_data, user_lammps_settings=None, **kwargs):
        super().__init__('relax', lammps_data, **kwargs)
        if user_lammps_settings:
            self.lammps_script.update(user_lammps_settings)


class NVESet(LammpsSet):
    def __init__(self, lammps_data, initial_velocity_temp=298.17, user_lammps_settings=None, **kwargs):
        """ Make sure to initialize velocity for correct initial energy

        Example:

          velocity: [
             "all create 298 313159265 units box",
             "all zero linear units box"
          ]

        Initializes atoms to initial temperature of 298 and ensures
        zero momentum in the box.
        """
        super().__init__('nve', lammps_data, **kwargs)
        self.lammps_script['velocity'][0] = 'all create {:.3f} {} units box'.format(initial_velocity_temp, random.randint(0, 10000000))
        if user_lammps_settings:
            self.lammps_script.update(user_lammps_settings)


class NVTSet(NVESet):
    def __init__(self, lammps_data,
                 temp_start=298.17, temp_end=None, temp_damp=100.0,
                 user_lammps_settings=None, **kwargs):
        super().__init__(lammps_data, **kwargs)
        temp_end = temp_end or temp_start
        self.lammps_script['velocity'][0] = 'all create {:.3f} {} units box'.format(temp_start, random.randint(0, 10000000))
        self.lammps_script['fix'] = '1 all nvt temp {:.3f} {:.3f} {:.3f}'.format(temp_start, temp_end, temp_damp)
        if user_lammps_settings:
            self.lammps_script.update(user_lammps_settings)


class NPTSet(NVESet):
    def __init__(self, lammps_data,
                 temp_start=298.17, temp_end=None, temp_damp=100.0,
                 press_start=0.0, press_end=None, press_damp=1000.0,
                 user_lammps_settings=None, **kwargs):
        super().__init__(lammps_data, **kwargs)
        temp_end = temp_end or temp_start
        press_end = press_end or press_start
        self.lammps_script['velocity'][0] = 'all create {:.3f} {} units box'.format(temp_start, random.randint(0, 10000000))
        self.lammps_script['fix'] = '1 all npt temp {:.3f} {:.3f} {:.3f} iso {:.3f} {:.3f} {:.3f}'.format(
            temp_start, temp_end, temp_damp, press_start, press_end, press_damp)
        if user_lammps_settings:
            self.lammps_script.update(user_lammps_settings)