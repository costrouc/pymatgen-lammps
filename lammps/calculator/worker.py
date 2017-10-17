import os
import re
import uuid
import asyncio
import multiprocessing
import tempfile

from ..output import LammpsDump, LammpsLog


class LammpsJob:
    def __init__(self, stdin, files=None, properties=None):
        self.id = uuid.uuid4().hex
        self.future = asyncio.Future()
        self.stdin = stdin
        self.files = files or {}
        self.properties = properties or set()
        self.stdout = None
        self.results = {}


class LammpsWorker:
    def __init__(self, cwd=None, cmd=None, num_workers=None):
        self.cwd = cwd or '.'
        self.cmd = cmd or ['lammps']
        self.num_workers = num_workers or multiprocessing.cpu_count()
        if num_workers > multiprocessing.cpu_count():
            raise ValueError('cannot have more workers than cpus')

    async def create(self):
        self._pending_queue = asyncio.Queue()
        self.completed_queue = asyncio.Queue()
        for _ in range(self.num_workers):
            tempdir = tempfile.mkdtemp()
            process = LammpsProcess(cwd=tempdir, cmd=self.cmd)
            await process.create(self._pending_queue, self.completed_queue)

    async def submit(self, stdin, files=None, properties=None):
        lammps_job = LammpsJob(stdin=stdin, files=files, properties=properties)
        await self._pending_queue.put(lammps_job)
        return lammps_job


class LammpsProcess:
    def __init__(self, cwd=None, cmd=None):
        self.cwd = cwd or '.'
        self.cmd = cmd or ['lammps']

    async def create(self, pending_queue, completed_queue):
        self.process = await self.create_lammps_process()
        self.pending_queue = pending_queue
        self.completed_queue = completed_queue
        self._job_task = asyncio.ensure_future(self._handle_job())

    async def create_lammps_process(self):
        return await asyncio.create_subprocess_exec(
            *self.cmd, cwd=self.cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT)

    def _write_inputs(self, lammps_job):
        for filename, content in lammps_job.files.items():
            with open(os.path.join(self.cwd, filename), 'wb') as f:
                f.write(content)
        self.process.stdin.write((
            f'{lammps_job.stdin}'
            f'\nprint "====={lammps_job.id}====="\nclear\n'
        ).encode('utf-8'))
        self.process.stdin.write(b'\nprint "' + b'hack to force flush' * 500 + b'"\n')

    async def _monitor_job(self, lammps_job):
        lammps_job_buffer = []
        lammps_job_regex = re.compile(b"^={5}(.{32})={5}\n$")
        async for line in self.process.stdout:
            match = lammps_job_regex.match(line)
            if match:
                if lammps_job.id != match.group(1).decode():
                    raise ValueError('jobs ran out of order (should not happen)')
                lammps_job.stdout = b''.join(lammps_job_buffer)
                return True
            elif b'ERROR' in line:
                lammps_job_buffer.append(line)
                lammps_job.stdout = b''.join(lammps_job_buffer)
                raise ValueError('error executing script')
            elif b'hack to force flush' not in line:
                lammps_job_buffer.append(line)

    def _process_results(self, lammps_job):
        log_filename = 'log.lammps'
        dump_filename = None
        for line in lammps_job.stdin.split('\n'):
            tokens = line.split()
            if len(tokens) == 0:
                continue
            if tokens[0] == 'log':
                log_filename = tokens[1]
            elif tokens[0] == 'dump':
                dump_filename = tokens[5]

        lammps_log = LammpsLog(os.path.join(self.cwd, log_filename))
        if dump_filename is None and ({'forces'} & lammps_job != set()):
            raise ValueError('requested properties require dump file')
        elif dump_filename:
            lammps_dump = LammpsDump(os.path.join(self.cwd, dump_filename))

        if 'stress' in lammps_job.properties:
            lammps_job.results['stress'] = lammps_log.get_stress(-1).tolist()
        if 'energy' in lammps_job.properties:
            lammps_job.results['energy'] = lammps_log.get_energy(-1)
        if 'forces' in lammps_job.properties:
            lammps_job.results['forces'] = lammps_dump.get_forces(-1).tolist()

    async def _handle_job(self):
        """ Job: {id, script, status, stdout}

        """
        while True:
            lammps_job_buffer = []
            lammps_job = await self.pending_queue.get()
            self._write_inputs(lammps_job)
            try:
                await self._monitor_job(lammps_job) # job error restart lammps process
                self._process_results(lammps_job)
                lammps_job.future.set_result(True)
            except ValueError as error:
                if 'error executing script' in error.message:
                    self.process.kill()
                    self.process = await self.create_lammps_process()
                lammps_job.future.set_result(False)
            await self.completed_queue.put(lammps_job)
            self.pending_queue.task_done()
