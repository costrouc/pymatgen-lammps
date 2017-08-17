from lammps.output import LammpsLog


def test_lammps_log_simple():
    log = LammpsLog('test_files/logs/simple.log')
    assert len(log.thermo_data) == 1


def test_lammps_log_multiple_runs():
    log = LammpsLog('test_files/logs/multiple_run.log')
    assert len(log.thermo_data) == 3


def test_lammps_log_normal():
    log = LammpsLog('test_files/logs/normal.log')
    assert len(log.thermo_data) == 2
