import multiprocessing
import asyncio
import urllib.parse
import json

from zmq_legos.mpd import Client as MDPClient

from .process import LammpsProcess
from .base import LammpsJob


class LammpsLocalClient:
    def __init__(self, command=None, num_workers=None):
        self.command = command
        self.num_workers = num_workers or multiprocessing.cpu_count()
        if num_workers > multiprocessing.cpu_count():
            raise ValueError('cannot have more workers than cpus')

    async def create(self):
        self._pending_queue = asyncio.Queue()
        self.completed_queue = asyncio.Queue()
        self._processes = []
        for _ in range(self.num_workers):
            process = LammpsProcess(command=self.command)
            await process.create(self._pending_queue, self.completed_queue)
            self._processes.append(process)

    def shutdown(self):
        for process in self._processes:
            process.shutdown()

    async def submit(self, stdin, files=None, properties=None):
        lammps_job = LammpsJob(stdin=stdin, files=files, properties=properties)
        lammps_job.future = asyncio.Future()
        await self._pending_queue.put(lammps_job)
        return lammps_job.future


class LammpsDistributedClient:
    def __init__(self, scheduler, loop=None):
        parsed = urllib.parse.urlparse(scheduler)
        self.mdp_client = MDPClient(
            protocol=parsed.schema, port=parsed.port, hostname=parsed.hostname
            loop=loop)
        self.lammps_jobs = {}

    async def create(self):
        self._completed_jobs_task = asyncio.ensure_future(self._handle_completed())

    async def submit(self, stdin, files=None, properties=None):
        lammps_job = LammpsJob(stdin=stdin, files=files, properties=properties)
        future = asyncio.Future()
        self.lammps_jobs[lammps_job.id] = {'future': future}
        message = json.dumps(lammps.job.as_dict()).encode('utf-8')
        await self.mdp_client.submit('lammps.job', [message])
        return future

    def shutdown(self):
        pass

    async def _handle_completed(self):
        while True:
            service, message = await self.mdp_client.get()
            lammps_job = LammpsJob.from_dict(json.loads(message[0].decode('utf-8')))
            (self.lammps_jobs.pop(lammps_job.id)['future']).set_result(lammps_job)
