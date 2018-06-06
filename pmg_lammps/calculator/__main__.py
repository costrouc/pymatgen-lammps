import logging
import multiprocessing

import asyncio
import zmq.asyncio

# from .client import LammpsDistributedClient
from .worker import LammpsWorker
from .scheduler import LammpsMaster


MASTER_URI = "tcp://127.0.0.1:8555"


def init_logging():
    logging.basicConfig(level=logging.INFO)


def init_event_loop():
    loop = zmq.asyncio.ZMQEventLoop()
    asyncio.set_event_loop(loop)
    return loop


def init_scheduler(stop_event):
    try:
        init_logging()

        scheduler = LammpsMaster(stop_event, MASTER_URI, loop=init_event_loop())
        scheduler.run()
    except KeyboardInterrupt:
        stop_event.set()


def init_worker(stop_event):
    async def run_worker(worker):
        await worker.create()
        await worker.run()

    try:
        init_logging()
        loop = init_event_loop()
        worker = LammpsWorker(stop_event, MASTER_URI, num_workers=4, loop=loop)
        loop.run_until_complete(run_worker(worker))
    except KeyboardInterrupt:
        stop_event.set()


def main():
    try:
        stop_event = multiprocessing.Event()
        worker_process = multiprocessing.Process(target=init_worker, args=(stop_event,))
        scheduler_process = multiprocessing.Process(target=init_scheduler, args=(stop_event,))
        worker_process.start()
        scheduler_process.start()
        scheduler_process.join()
    except KeyboardInterrupt:
        exit(0)
    finally:
        stop_event.set()


if __name__ == "__main__":
    main()
