import os
import json
import random

from .inputs import LammpsInput, LammpsScript
from .utils import structure_to_neb_input

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class LammpsSet(LammpsInput):
    def __init__(self, config_filename, lammps_data, data_filename='initial.data'):
        with open(os.path.join(MODULE_DIR, 'sets', config_filename + ".json")) as f:
            lammps_script = json.load(f, object_pairs_hook=LammpsScript)
        lammps_script['read_data'] = data_filename
        super().__init__(lammps_script, lammps_data)


class StaticSet(LammpsSet):
    def __init__(self, lammps_data, user_lammps_settings=None, **kwargs):
        super().__init__('static', lammps_data, **kwargs)
        if user_lammps_settings:
            self.lammps_script.update(user_lammps_settings)


class RelaxSet(LammpsSet):
    def __init__(self, lammps_data, relax_box=True, user_lammps_settings=None, **kwargs):
        super().__init__('relax', lammps_data, **kwargs)
        if not relax_box:
            self.lammps_script.update([('fix', [])])
        if user_lammps_settings:
            self.lammps_script.update(user_lammps_settings)


class NEBSet(LammpsSet):
    def __init__(self, lammps_data, final_structure, user_lammps_settings=None, **kwargs):
        super().__init__('neb', lammps_data, **kwargs)
        if user_lammps_settings:
            self.lammps_script.update(user_lammps_settings)
        self.final_structure = final_structure

    def write_input(self, output_dir, input_filename="lammps.in", make_dir=True):
        super().write_input(output_dir=output_dir, input_filename=input_filename,
                            make_dir=make_dir)

        # Write final structure for NEB calculation (uses linear interpolation)
        # TODO: Works for now
        with open(os.path.join(output_dir, 'last.coords'), 'w') as f:
            f.write(structure_to_neb_input(self.final_structure))


class NVESet(LammpsSet):
    def __init__(self, lammps_data, initial_temp=298.17, user_lammps_settings=None, **kwargs):
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
        if initial_temp:
            self.lammps_script['velocity'][0] = 'all create {:.3f} {} units box'.format(initial_temp, random.randint(0, 10000000))
        else:
            self.lammps_script['velocity'] = []
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


class NPHSet(NVESet):
    def __init__(self, lammps_data,
                 press_start=0.0, press_end=None, press_damp=1000.0,
                 initial_temp=None,
                 user_lammps_settings=None, **kwargs):
        super().__init__(lammps_data, **kwargs)
        press_end = press_end or press_start
        if initial_temp:
            self.lammps_script['velocity'][0] = 'all create {:.3f} {} units box'.format(initial_temp, random.randint(0, 10000000))
        else:
            self.lammps_script['velocity'] = []
        self.lammps_script['fix'] = '1 all nph iso {:.3f} {:.3f} {:.3f}'.format(press_start, press_end, press_damp)
        if user_lammps_settings:
            self.lammps_script.update(user_lammps_settings)
