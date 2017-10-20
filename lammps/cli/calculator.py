""" Example Config

{
   'master': 'tcp://localhost:8555'
}

"""
import json
import asyncio

import click
import zmq.asyncio

from . import cli
from ..calculator import LammpsWorker, LammpsMaster


def init_event_loop():
    loop = zmq.asyncio.ZMQEventLoop()
    asyncio.set_event_loop(loop)
    return loop


@cli.command()
@click.option('-m', '--master')
@click.option('-n', '--num-workers', type=int)
@click.option('-c', '--config', type=click.Path(exists=True))
def worker(master, num_workers, config):
    if config:
        with open(config) as f:
            config = json.load(f)
    else:
        config = {'master': master}
    master_uri = config.get('master', master)
    if master_uri is None:
        raise ValueError('must specify master uri')

    async def run_worker(worker):
        await worker.create()
        await worker.run()

    try:
        stop_event = asyncio.Event()
        loop = init_event_loop()
        worker = LammpsWorker(stop_event, master_uri, num_workers=num_workers, loop=loop)
        loop.run_until_complete(run_worker(worker))
    except KeyboardInterrupt:
        stop_event.set()


@cli.command()
@click.option('-m', '--master')
@click.option('-c', '--config', type=click.Path(exists=True))
def master(master, config):
    if config:
        with open(config) as f:
            config = json.load(f)
    else:
        config = {'master': master}
    master_uri = config.get('master')
    if master_uri is None:
        raise ValueError('must specify master uri')

    try:
        stop_event = asyncio.Event()
        scheduler = LammpsMaster(stop_event, master_uri, loop=init_event_loop())
        scheduler.run()
    except KeyboardInterrupt:
        stop_event.set()
