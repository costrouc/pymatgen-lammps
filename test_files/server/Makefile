all: master worker

master:
	pylammps -l DEBUG master -c config.json 2> master.log
worker:
	pylammps -l DEBUG worker -c config.json --command="lammps_ubuntu" --num-workers=1 2> worker.log
