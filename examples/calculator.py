import time
import asyncio

from lammps.calculator import LammpsCalculator


script = [
    ('log', 'lammps.log'),
    ('units', 'metal'),
    ('dimension', 3),
    ('boundary', 'p p p'),
    ('atom_style', 'full'),
    ('read_data', 'initial.data'),
    ('kspace_style', 'pppm 0.000010'),
    ('pair_style', 'buck/coul/long 10'),
    ('pair_coeff', [
        '1 1 1309362.2766468062 0.104 0.0',
        '1 2 9892.357 0.20199 0.0',
        '2 2 2145.7345 0.3 30.2222'
    ]),
    ('set', [
        'type 2 charge -1.400000',
        'type 1 charge 1.400000'
    ]),
    ('dump',  '1 all custom 1 mol.lammpstrj id type x y z fx fy fz'),
    ('dump_modify', '1 sort id'),
    ('thermo_style', 'custom step etotal pxx pyy pzz pxy pxz pyz'),
    ('run', 0)
]


async def main(loop):
    lammps_calculator = LammpsCalculator(cwd='/home/costrouc/scratch/python/asyncio-process/simple', max_workers=2, cmd=['lammps_serial'])
    await lammps_calculator._create()

    start = time.time()
    lammps_futures = []
    for i in range(10000):
        future = await lammps_calculator.submit(script)
        lammps_futures.append(future)
    results = await asyncio.gather(*lammps_futures)
    print('total time: ', time.time() - start)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
