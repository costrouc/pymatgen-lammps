master:
	pylammps -l INFO master -c config.json
worker:
	pylammps -l INFO worker -c config.json --command="lammps_ubuntu" --num-workers=2
