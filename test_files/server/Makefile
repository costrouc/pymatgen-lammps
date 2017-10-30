all: master worker

master:
	pylammps -l INFO master -c config.json 2> master.log
worker:
	pylammps -l INFO worker -c config.json --command="lammps_ubuntu" --num-workers=1 2> worker.log
