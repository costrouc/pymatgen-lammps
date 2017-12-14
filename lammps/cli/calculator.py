""" Example Config

{
   'master': 'tcp://localhost:8555'
}

"""
import os
import json
import asyncio
import socket
import urllib.parse

import zmq.asyncio
from ..calculator import LammpsWorker, LammpsMaster


def filename_type(filename):
    if not os.path.isfile(filename):
        raise argparse.ArgumentTypeError(f'path {filename} is not a file')
    return filename


def add_subcommand_worker(subparsers):
    parser = subparsers.add_parser('worker', help='start lammps calculator worker')
    parser.set_defaults(func=handle_subcommand_worker)
    parser.add_argument('-m', '--master', help='uri of lammps master')
    parser.add_argument('-n', '--num-workers', type=int)
    parser.add_argument('--command')
    parser.add_argument('-c', '--config', type=filename_type)


def add_subcommand_master(subparsers):
    parser = subparsers.add_parser('master', help='start lammps calculator master')
    parser.set_defaults(func=handle_subcommand_master)
    parser.add_argument('-m', '--master', help='uri of lammps master')
    parser.add_argument('-c', '--config', type=filename_type)


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


def handle_subcommand_worker(args):
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    else:
        config = {'master': args.master}
    master_uri = config.get('master', master)
    if master_uri is None:
        raise ValueError('must specify master uri')

    async def run_worker(worker):
        await worker.create()
        await worker.run()

    try:
        stop_event = asyncio.Event()
        loop = init_event_loop()
        worker = LammpsWorker(stop_event, normalize_uri(master_uri), num_workers=args.num_workers, command=args.command, loop=loop)
        loop.run_until_complete(run_worker(worker))
    except KeyboardInterrupt:
        stop_event.set()
        loop.run_until_complete(worker.shutdown())


def handle_subcommand_master(args):
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    else:
        config = {'master': args.master}
    master_uri = config.get('master')
    if master_uri is None:
        raise ValueError('must specify master uri')

    try:
        stop_event = asyncio.Event()
        scheduler = LammpsMaster(stop_event, normalize_uri(master_uri), loop=init_event_loop())
        scheduler.run()
    except KeyboardInterrupt:
        stop_event.set()
