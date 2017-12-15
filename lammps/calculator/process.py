import os
import re
import asyncio
import shutil
import tempfile
import pickle
import logging
import time
import shlex

from ..output import LammpsDump, LammpsLog


class LammpsProcess:
    def __init__(self, command=None):
        self.directory = tempfile.mkdtemp()
        self.command = shlex.split(command or 'lammps')
        self.logger = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        if not shutil.which(self.command[0]): # simple test
            raise ValueError(f'lammps executable {self.command[0]} does not exist')

    async def create(self, pending_queue, completed_queue):
        self.process = await self.create_lammps_process()
        self.pending_queue = pending_queue
        self.completed_queue = completed_queue
        self._job_task = asyncio.ensure_future(self._handle_jobs())

    def shutdown(self):
        self.process.kill() # TODO: not very nice
        shutil.rmtree(self.directory)

    async def create_lammps_process(self):
        process =  await asyncio.create_subprocess_exec(
            *self.command, cwd=self.directory,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT)
        # check that lammps process started properly (using print statement)
        return process

    def _write_inputs(self, lammps_job_input):
        self.logger.debug(f'lammps job {lammps_job_input["id"]} writing stdin and files {lammps_job_input["files"].keys()}')
        for filename, content in lammps_job_input['files'].items():
            with open(os.path.join(self.directory, filename), 'w') as f:
                f.write(content)
        self.process.stdin.write((
            f'{lammps_job_input["stdin"]}'
            f'\nprint "====={lammps_job_input["id"]}====="\nclear\n'
        ).encode('utf-8'))
        self.process.stdin.write(b'\nprint "' + b'hack to force flush' * 500 + b'"\n')

    async def _monitor_job(self, lammps_job_output):
        lammps_job_buffer = []
        lammps_job_regex = re.compile(b"^={5}(.{32})={5}\n$")
        self.logger.debug(f'monitoring running lammps job {lammps_job_output["id"]}')
        async for line in self.process.stdout:
            match = lammps_job_regex.match(line)
            if match:
                if lammps_job_output['id'] != match.group(1).decode():
                    raise ValueError('job id does not match currently running job (should not happen)')
                lammps_job_output['stdout'] = b''.join(lammps_job_buffer)
                self.logger.debug(f'lammps job {lammps_job_output["id"]} completed')
                return True
            elif b'ERROR' in line:
                lammps_job_buffer.append(line)
                lammps_job_output['stdout'] = b''.join(lammps_job_buffer)
                self.logger.debug(f'lammps job {lammps_job_output["id"]} encountered error')
                raise ValueError('error executing script')
            elif b'hack to force flush' not in line:
                lammps_job_buffer.append(line)

    def _process_results(self, lammps_job_input, lammps_job_output):
        log_filename = 'log.lammps'
        dump_filename = None
        for line in lammps_job_input['stdin'].split('\n'):
            tokens = line.split()
            if len(tokens) == 0:
                continue
            if tokens[0] == 'log':
                log_filename = tokens[1]
            elif tokens[0] == 'dump':
                dump_filename = tokens[5]

        lammps_log = LammpsLog(os.path.join(self.directory, log_filename))
        if dump_filename is None and ({'forces', 'lattice', 'positions', 'velocities'} & lammps_job_input['properties'] != set()):
            raise ValueError('requested properties require dump file')
        elif dump_filename:
            lammps_dump = LammpsDump(os.path.join(self.directory, dump_filename))

        self.logger.debug(f'lammps job {lammps_job_input["id"]} properties {lammps_job_input["properties"]} being collected')
        if 'stress' in lammps_job_input['properties']:
            lammps_job_output['results']['stress'] = lammps_log.get_stress(-1).tolist()
        if 'energy' in lammps_job_input['properties']:
            lammps_job_output['results']['energy'] = lammps_log.get_energy(-1)
        if 'forces' in lammps_job_input['properties']:
            lammps_job_output['results']['forces'] = lammps_dump.get_forces(-1).tolist()
        if 'lattice' in lammps_job_input['properties']:
            lammps_job_output['results']['lattice'] = (lammps_dump.get_lammps_box(-1)).lattice.matrix.tolist()
        if 'positions' in lammps_job_input['properties']:
            lammps_job_output['results']['positions'] = lammps_dump.get_positions(-1).tolist()
        if 'velocities' in lammps_job_input['properties']:
            lammps_job_output['results']['velocities'] = lammps_dump.get_velocities(-1).tolist()

    async def _handle_jobs(self):
        while True:
            lammps_job_buffer = []
            client_id, message = await self.pending_queue.get()
            lammps_job_input = pickle.loads(message[0]) # lammps_job_input {id, stdin, files, properties}
            lammps_job_output = {'id': lammps_job_input['id'], 'stdout': None, 'results': {}, 'error': None}
            try:
                start_time = time.perf_counter()
                self._write_inputs(lammps_job_input)
                self.logger.debug(f'lammps job {lammps_job_output["id"]} writing inputs {time.perf_counter() - start_time} [sec]')
                start_time = time.perf_counter()
                await self._monitor_job(lammps_job_output) # job error restart lammps process
                self.logger.debug(f'lammps job {lammps_job_output["id"]} completed in {time.perf_counter() - start_time} [sec]')
                start_time = time.perf_counter()
                self._process_results(lammps_job_input, lammps_job_output)
                self.logger.debug(f'lammps job {lammps_job_output["id"]} processing results {time.perf_counter() - start_time} [sec]')
            except ValueError as error:
                if 'error executing script' in error.message:
                    self.logger.warning('restarting lammps process')
                    self.process.kill()
                    self.process = await self.create_lammps_process()
                lammps_job_output['error'] = error.message
            except Exception as e: # debugging (remove later)
                print(e)
            await self.completed_queue.put((client_id, [pickle.dumps(lammps_job_output)]))
            self.pending_queue.task_done()
