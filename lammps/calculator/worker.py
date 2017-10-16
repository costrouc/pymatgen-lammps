import os
import re
import uuid
import asyncio
import multiprocessing


class LammpsJob:
    def __init__(self, stdin, additional_files=None):
        self.id = uuid.uuid4().hex
        self.future = asyncio.Future()
        self.stdin = stdin
        self.additional_files = additional_files or {}
        self.stdout = None

# TODO add results parsing capability

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
            process = LammpsProcess(cwd=self.cwd, cmd=self.cmd)
            await process.create(self._pending_queue, self.completed_queue)

    async def submit(self, stdin, additional_files=None):
        lammps_job = LammpsJob(stdin=stdin, additional_files=additional_files or {})
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

    async def _handle_job(self):
        """ Job: {id, script, status, stdout}

        """
        lammps_job_regex = re.compile(b"^={5}(.{32})={5}\n$")
        while True:
            lammps_job_buffer = []
            lammps_job = await self.pending_queue.get()
            for filename, content in lammps_job.additional_files.items():
                with open(os.path.join(self.cwd, filename), 'wb') as f:
                    f.write(content)
            self.process.stdin.write((
                f'{lammps_job.stdin}'
                f'\nprint "====={lammps_job.id}====="\nclear\n'
            ).encode('utf-8'))
            self.process.stdin.write(b'\nprint "' + b'hack to force flush' * 500 + b'"\n')
            async for line in self.process.stdout:
                match = lammps_job_regex.match(line)
                if match:
                    if lammps_job.id != match.group(1).decode():
                        raise ValueError('jobs ran out of order (should not happen)')
                    lammps_job.stdout = b''.join(lammps_job_buffer)
                    lammps_job.future.set_result(True)
                    break
                elif b'ERROR' in line:
                    lammps_job_buffer.append(line)
                    lammps_job.stdout = b''.join(lammps_job_buffer)
                    lammps_job.future.set_result(False)
                    # reset lammps process
                    self.process.kill()
                    self.process = await self.create_lammps_process()
                    break
                elif b'hack to force flush' not in line:
                    lammps_job_buffer.append(line)
            await self.completed_queue.put(lammps_job)
            self.pending_queue.task_done()
