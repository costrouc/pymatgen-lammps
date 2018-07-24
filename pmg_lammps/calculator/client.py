import multiprocessing
import asyncio
import urllib.parse
import pickle
import uuid
import logging


from .process import LammpsProcess


class LammpsLocalClient:
    def __init__(self, command=None, num_workers=None):
        self.command = command
        self.logger = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.num_workers = num_workers or multiprocessing.cpu_count()
        if num_workers > multiprocessing.cpu_count():
            raise ValueError('cannot have more workers than cpus')
        self.lammps_jobs = {}

    async def create(self):
        self._pending_queue = asyncio.Queue()
        self._completed_queue = asyncio.Queue()
        self._processes = []
        self.logger.info(f'creating {self.num_workers} lammps processes')
        for _ in range(self.num_workers):
            process = LammpsProcess(command=self.command)
            await process.create(self._pending_queue, self._completed_queue)
            self._processes.append(process)
        self._completed_jobs_task = asyncio.ensure_future(self._handle_completed())

    async def _handle_completed(self):
        while True:
            client_id, message = await self._completed_queue.get()
            lammps_job_output = pickle.loads(message[0])
            (self.lammps_jobs.pop(lammps_job_output['id'])).set_result(lammps_job_output)

    def shutdown(self):
        for process in self._processes:
            process.shutdown()

    async def submit(self, stdin, files=None, properties=None):
        lammps_job_input = {
            'id': uuid.uuid4().hex,
            'stdin': stdin,
            'files': files or {},
            'properties': properties or set()
        }
        future = asyncio.Future()
        self.lammps_jobs[lammps_job_input['id']] = future
        await self._pending_queue.put((b'client_id', [pickle.dumps(lammps_job_input)]))
        return future


class LammpsDistributedClient:
    def __init__(self, scheduler, loop=None):
        from zmq_legos.mdp import Client as MDPClient

        parsed = urllib.parse.urlparse(scheduler)
        self.mdp_client = MDPClient(protocol=parsed.scheme, port=parsed.port, hostname=parsed.hostname, loop=loop)
        self.logger = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.lammps_jobs = {}

    async def create(self):
        self._completed_jobs_task = asyncio.ensure_future(self._handle_completed())

    async def submit(self, stdin, files=None, properties=None):
        lammps_job_input = {
            'id': uuid.uuid4().hex,
            'stdin': stdin,
            'files': files or {},
            'properties': properties or set()
        }
        future = asyncio.Future()
        self.lammps_jobs[lammps_job_input['id']] = future
        await self.mdp_client.submit(b'lammps.job', [pickle.dumps(lammps_job_input)])
        self.logger.debug(f'lammps job {lammps_job_input["id"]} submitted')
        return future

    def shutdown(self):
        pass

    async def _handle_completed(self):
        while True:
            service, message = await self.mdp_client.get()
            lammps_job_output = pickle.loads(message[0])
            self.logger.debug(f'lammps job {lammps_job_output["id"]} completed')
            (self.lammps_jobs.pop(lammps_job_output['id'])).set_result(lammps_job_output)
