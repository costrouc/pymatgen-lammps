# Calculation the Elastic Constants from given deformations
import os
import subprocess

from pymatgen import Structure, Lattice, Specie
from pymatgen.analysis.elasticity import DeformedStructureSet, Strain, Stress, ElasticTensor

from pmg_lammps import RelaxSet, LammpsLog, LammpsData, LammpsPotentials


supercell = (5, 5, 5)
a = 4.1990858 # From evaluation of potential
lattice = Lattice.from_parameters(a, a, a, 90, 90, 90)
mg = Specie('Mg', 1.4)
o = Specie('O', -1.4)
atoms = [mg, o]
sites = [[0, 0, 0], [0.5, 0.5, 0.5]]
structure = Structure.from_spacegroup(225, lattice, atoms, sites)
initial_structure = structure * supercell

directory = 'runs/elastic'
num_normal = 10
num_shear = 10
max_normal = 0.03
max_shear = 0.08

lammps_potentials = LammpsPotentials(pair={
    (mg, mg): '1309362.2766468062  0.104    0.0',
    (mg, o ): '9892.357            0.20199  0.0',
    (o , o ): '2145.7345           0.3      30.2222'
})

mgo_potential_settings = [
    ('pair_style', 'buck/coul/long 10.0'),
    ('kspace_style', 'pppm 1.0e-5'),
]

print('Performing Strained Calculations')
strained_structures = []
deformation_set = DeformedStructureSet(structure, nd=max_normal, ns=max_shear,
                     num_norm=num_normal, num_shear=num_shear)
for i, deformation in enumerate(deformation_set.deformations):
    deformation_directory = os.path.join(directory, str(i))
    print('Deformation', i)
    strain = Strain.from_deformation(deformation)
    strained_structure = deformation.apply_to_structure(initial_structure)

    lammps_data = LammpsData.from_structure(strained_structure, potentials=lammps_potentials,
                                            include_charge=True)

    lammps_set = RelaxSet(lammps_data, relax_box=False, user_lammps_settings=[
    ] + mgo_potential_settings)
    lammps_set.write_input(deformation_directory)
    subprocess.call(['lammps', '-i', 'lammps.in'], cwd=deformation_directory, stdout=subprocess.PIPE)

    lammps_log = LammpsLog(os.path.join(deformation_directory, 'lammps.log'))
    stress = Stress(lammps_log.get_stress(-1))

    strained_structures.append({
        'strain': strain,
        'structrure': strained_structure,
        'stress': stress / -10000.0 # bar to GPa
    })

strains = [defo['strain'] for defo in strained_structures]
stresses = [defo['stress'] for defo in strained_structures]
elastic = ElasticTensor.from_pseudoinverse(strains, stresses)

print('Stiffness Tensor')
for row in elastic.voigt:
    print('{:+8.1f} {:+8.1f} {:+8.1f} {:+8.1f} {:+8.1f} {:+8.1f}\n'.format(*row))

print('Shear Modulus G_V', elastic.g_voigt)
print('Shear Modulus G_R', elastic.g_reuss)
print('Shear Modulus G_vrh', elastic.g_vrh)

print('Bulk Modulus K_V', elastic.k_voigt)
print('Bulk Modulus K_R', elastic.k_reuss)
print('Bulk Modulus K_vrh', elastic.k_vrh)

print('Elastic Anisotropy', elastic.universal_anisotropy)
print('Poisons Ration', elastic.homogeneous_poisson)
