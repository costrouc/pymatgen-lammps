import subprocess
from collections import deque
from concurrent.futures import Future
import uuid

from .inputs import LammpsScript


class LammpsExecutor:
    """ An implementation that tries to run lammps as a calculator

    This is a good idea for lots of calculations that run in a short
    period of time.
    """
    def __init__(self, command, num_processes=1, cwd=None):
        self._num_processes = num_processes
        self.command = command or ['lammps']
        self.count = 0

        self._process = subprocess.Popen(self.command, cwd=cwd,
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)

    def _submit(self, script):
        """submit task to pool of processes"""
        pass

    def submit(self, script):
        if not isinstance(script, LammpsScript):
            script = LammpsScript(script)
        script['clear'] = ''
        script['print'] = str(uuid.uuid4())
