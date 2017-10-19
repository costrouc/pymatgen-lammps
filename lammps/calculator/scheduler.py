# lammps scheduler (to be run as executable should be simple wrapper) easiest
# simple run function

import asyncio
import urllib.parse

from zmq_legos.mdp import Scheduler as MDPScheduler


class LammpsMaster:
    def __init__(self, stop_event, scheduler, loop=None):
        parsed = urllib.parse.urlparse(scheduler)
        self.mdp_scheduler = MDPScheduler(
            stop_event,
            protocol=parsed.scheme, port=parsed.port, hostname=parsed.hostname,
            loop=loop)

    def run(self):
        self.mdp_scheduler.run()

    def disconnect(self):
        self.mdp_scheduler.disconnect()
