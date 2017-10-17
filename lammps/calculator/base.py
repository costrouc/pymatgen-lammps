import uuid

class LammpsJob:
    def __init__(self, stdin, files=None, properties=None):
        self.id = uuid.uuid4().hex
        self.stdin = stdin
        self.files = files or {}
        self.properties = properties or set()
        self.stdout = None
        self.error = None
        self.results = {}

    def __hash__(self):
        return hash(self.id)

    def as_dict(self):
        return {
            'id': self.id,
            'stdin': self.stdin,
            'files': self.files,
            'properties': list(self.properties),
            'stdout': self.stdout,
            'error': self.error,
            'results': self.results
        }

    @classmethod
    def from_dict(cls, d):
        lammps_job = cls(d['stdin'], files=d['files'], properties=set(d['properties']))
        lammps_job.id = d['id']
        lammps_job.stdout = d['stdout']
        lammps_job.error = d['error']
        lammps_job.results = d['results']
