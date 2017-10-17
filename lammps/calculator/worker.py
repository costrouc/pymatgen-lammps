import urllib.parse
import asyncio
import multiprocessing

from zmq_legos.mpd import Worker as MDPWorker

from .process import LammpsProcess
from .base import LammpsJob

class LammpsWorker:
    def __init__(self, scheduler, command=None, num_workers=None, loop=None):
        self.command = command
        self.num_workers = num_workers or multiprocessing.cpu_count()
        if self.num_workers > multiprocessing.cpu_count():
            raise ValueError('cannot have more workers than cpus')

        parsed = urllib.parse.urlparse(scheduler)
        stop_event = asyncio.Event()
        self.mdp_worker = MDPWorker(
            stop_event,
            max_messages=self.num_workers,
            protocol=parsed.schema, port=parsed.port, hostname=parsed.hostname,
            loop=loop)

    async def create(self):
        self._processes = []
        for _ in range(self.num_workers):
            process = LammpsProcess(command=self.command)
            await process.create(
                self.mdp_worker.queued_messages,
                self.mdp_worker.completed_messages) # need to adapt local version
            self._processes.append(process)

    def shutdown(self):
        for process in self._processes:
            process.shutdown()

    async def run(self):
        await self.mdp_worker.run('lammps.job')
