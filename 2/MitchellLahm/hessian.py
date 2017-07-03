from Molecule import Molecule
import os, sys, shutil
import numpy as np
mol = Molecule('molecule.xyz')
mol.to_bohr()
if os.path.isdir('DISPS'):
	os.system('rm -r DISPS')

# Storing template
with open('template.dat','r') as my_file:
	template = my_file.read()

# Function that generates directories with input files and ref geom for displacements
def generate_inputs(mol, template, disp_size = 0.005, directory = "DISPS"):
	N = mol.natom
	end = 3 * N * (3 * N + 1)
	os.mkdir(directory)
	directory = os.getcwd() + '/' + directory + '/molecule.xyz'
	shutil.copyfile('molecule.xyz', directory)
	directory = "DISPS"
	os.chdir(directory)
	for i in range(end):
		mol1 = mol.copy()
		ind = i / 10
		r = i % 10
		directory = str(i)
		os.mkdir(directory)
		os.chdir(directory)
		# Single coord shift
		if r < 3:
			mol1.geom[ind/N][ind%N] += (r - 1) * disp_size
		# Double coord shift
		elif r < 6 and r > 2:
			mol1.geom[ind/N][ind%N] += (r - 4) * disp_size
		elif r < 8 and r > 5:
			print i
			print r
			print ind/N, ind%N
			mol1.geom[ind/N][ind%N] += (r - 6) * disp_size
			
		"""else:
			print 'test' """
		with open('disp.xyz','w') as my_file:
			my_file.write(repr(mol1))
		os.chdir('..')

# Function that walks through the directories and executes a command in each	
"""def run_jobs(mol, command = "psi4", directory = "DISPS"):
	N = mol.natom
	end = 3 * N * (3 * N * 1)
	list = os.listdir(directory)
	os.chdir(directory)
	for i in list:
		os.chdir(str(i))
		os.system(command)
		os.chdir("..")
		
# Function that grabs 
def helper_function():
	return None

# Function that builds the Hessian matrix
def build_hessian(mol, energy_prefix, disp_size = 0.005, directory = "DISPS"):
	return None"""
	
generate_inputs(mol, template)
# run_jobs(mol)
