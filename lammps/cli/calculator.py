""" Example Config

{
   'master': 'tcp://localhost:8555'
}

"""
import json
import asyncio
import socket
import urllib.parse

import click
import zmq.asyncio

from . import cli
from ..calculator import LammpsWorker, LammpsMaster


def init_event_loop():
    loop = zmq.asyncio.ZMQEventLoop()
    asyncio.set_event_loop(loop)
    return loop

def normalize_uri(uri):
    parsed_uri = urllib.parse.urlparse(uri)
    hostname = socket.gethostbyname(parsed_uri.hostname)
    if parsed_uri.port:
        parsed_uri = parsed_uri._replace(netloc=f'{hostname}:{parsed_uri.port}')
    else:
        parsed_uri = parsed_uri._replace(netloc=f'{hostname}')
    return urllib.parse.urlunparse(parsed_uri)

@cli.command()
@click.option('-m', '--master')
@click.option('-n', '--num-workers', type=int)
@click.option('--command')
@click.option('-c', '--config', type=click.Path(exists=True))
def worker(master, num_workers, command, config):
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
        worker = LammpsWorker(stop_event, normalize_uri(master_uri), num_workers=num_workers, command=command, loop=loop)
        loop.run_until_complete(run_worker(worker))
    except KeyboardInterrupt:
        stop_event.set()
        loop.run_until_complete(worker.shutdown())



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
        scheduler = LammpsMaster(stop_event, normalize_uri(master_uri), loop=init_event_loop())
        scheduler.run()
    except KeyboardInterrupt:
        stop_event.set()
