import argparse
import sys

from . import calculator
from . import benchmark
from ..logging import LOG_LEVELS, init_logging


def init_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--loglevel', choices=LOG_LEVELS, default='WARNING')
    subparsers = parser.add_subparsers()
    calculator.add_subcommand_master(subparsers)
    calculator.add_subcommand_worker(subparsers)
    benchmark.add_subcommand_benchmark(subparsers)
    return parser


def cli():
    parser = init_parser()
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    init_logging(args.loglevel)
    args.func(args)
