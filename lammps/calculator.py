import asyncio
import uuid
import re
import itertools
import multiprocessing

from .inputs import LammpsScript


class LammpsCalculator:
    def __init__(self, cwd='.', cmd=None, max_workers=1):
        self._max_workers = max_workers
        if self._max_workers > multiprocessing.cpu_count():
            raise ValueError('cannot have more workers than max number of cpus')
        self.cwd = cwd
        self.cmd = cmd or ['lammps']

    async def _create(self):
        self._pending_queue = asyncio.Queue()
        self._processes = []
        for i in range(self._max_workers):
            process = _LammpsProcess(cwd=self.cwd, cmd=self.cmd)
            await process._create()
            self._processes.append(process)
        self._round_robin_processes = itertools.cycle(self._processes)

    async def submit(self, script):
        if not isinstance(script, LammpsScript):
            script = LammpsScript(script)
        unique_uuid = uuid.uuid4()
        future = asyncio.Future()
        item = {'id': unique_uuid.hex, 'script': script, 'future': future}
        process = next(self._round_robin_processes)
        await process.pending_queue.put(item)
        return future


class _LammpsProcess:
    def __init__(self, cwd, cmd):
        self.cwd = cwd
        self.cmd = cmd

    async def _create(self):
        self._process = await asyncio.create_subprocess_exec(
            *self.cmd, cwd=self.cwd,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        self.pending_queue = asyncio.Queue()
        self.running_queue = asyncio.Queue()
        self.completed_queue = asyncio.Queue()
        self._stdout_task = asyncio.ensure_future(self._handle_stdout(self._process))
        self._stdin_task = asyncio.ensure_future(self._handle_stdin(self._process))

    @property
    def num_running(self):
        return self.pending_queue.qsize() + self.running_queue.qsize()

    async def _handle_stdout(self, process):
        lammps_job_buffer = []
        lammps_job_regex = re.compile(b"^={5}(.{32})={5}\n$")
        count = 0
        async for line in process.stdout:
            match = lammps_job_regex.match(line)
            if match:
                item = await self.running_queue.get()
                if item['id'] != match.group(1).decode():
                    raise ValueError('jobs ran out of order (should not happend)')
                item['future'].set_result(''.join(lammps_job_buffer))
                await self.completed_queue.put(item)
                lammps_job_buffer = []
                self.running_queue.task_done()
            elif b'ERROR:' in line:
                print(line.decode())
                lammps_job_buffer.append(line.decode())
            elif b'hack to force flush' not in line:
                lammps_job_buffer.append(line.decode())

    async def _handle_stdin(self, process):
        while True:
            item = await self.pending_queue.get()
            if item is None:
                break
            process.stdin.write(str(item['script']).encode() + b'\nprint "=====%s====="\nclear\n' % item['id'].encode())
            if self.pending_queue.empty():
                process.stdin.write(b'print "' + b'hack to force flush ' * 200 + b'"\n')
            await self.running_queue.put(item)
            self.pending_queue.task_done()
        process.stdin.write_eof()
