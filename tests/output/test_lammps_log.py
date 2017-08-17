from lammps.output import LammpsLog


def test_lammps_log_simple():
    log = LammpsLog('test_files/logs/simple.log')
    assert len(log.thermo_data) == 1
