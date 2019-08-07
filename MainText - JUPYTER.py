#Authors: Matthew Osmond <mmosmond@zoology.ubc.ca> & Ken A. Thompson <ken.thompson@zoology.ubc.ca>
#Description: The role of standing genetic variance in speciation

import numpy as np
import time
# import matplotlib.pyplot as plt
import csv
import math

######################################################################
##FUNCTIONS##
######################################################################

def fitness(phenos, theta, sigma):
	"""
	This function determines relative fitness
	"""
	dist = np.linalg.norm(phenos - theta, axis=1) #phenotypic distance from optimum
	w = np.exp(-0.5 * sigma * dist**2) #fitness
	return w

def shuffle_along_axis(a, axis):
	idx = np.random.rand(*a.shape).argsort(axis = axis)
	return np.take_along_axis(a,idx,axis = axis) 

def crossover(chromosome):
	
	c = np.random.randint(1, size = np.size(chromosome, 1)).reshape(1, np.size(chromosome, 1)) # create a random array to save the results of each loop
	
	x = 0
	while x < (N_adapts[0] * 2 + 1): 
		
		b = shuffle_along_axis(chromosome[x:(x+2)], axis = 0) #shuffle along columns in groups of 2. each group of 2 represents chrom1 an chrom2 of each individual 
		c = np.concatenate((c, b), axis = 0) #update what F1_after_recomb2 is after each loop of recombination 
		x+=2

	crossedover = c[1:(N_adapts[0] * 2 + 1)]

	return crossedover


def recomb(surv):
	"""
	This function creates offspring through pairing of parents (diploid) and recombination (i.e, meiosis)
	"""
	# crossing over within diploid parents to make gametes, input is 1000 rows, output also 1000 rows; n_loci columns
	surv_stacked = np.concatenate(np.stack((surv[0], surv[1]), axis = 1)) # this places the related rows together, 1st row of each together, then 2nd, then 3rd... - 4 loci. stacks the two arrays vertically 
	
	#recombination 
	c = np.random.randint(1, size = np.size(surv_stacked, 1)).reshape(1, np.size(surv_stacked, 1)) # create a random array to save the results of each loop

	x = 0
	while x < (N_adapts[0] * 2 + 1): 
		
		b = shuffle_along_axis(surv_stacked[x:(x+2)], axis = 0) #shuffle along columns in groups of 2. each group of 2 represents chrom1 an chrom2 of each individual 
		c = np.concatenate((c, b), axis = 0) #update what surv_stacked is after each loop of recombination 
		x+=2

	surv_stacked = c[1:(N_adapts[0] * 2 + 1)] #remove the empty array from the top surv_stacked, update surv_stacked accordingly. chrom1, chrom2, chrom1, chrom2 seklinde devam ediyor rowlar. 

	surv_chrom1 = surv_stacked[::2] #this selects every odd row - chrom1 of N_adapts number of individuals after shuffling, both parent1 and parent2. number of rows = N_adapts, number of columns = number of loci   
	surv_chrom2 = surv_stacked[1::2] #this selects every even row - chrom 2 of N_adapts number of individuals, both parent1 and parent2 

	surv_stacked = np.hstack((surv_chrom1, surv_chrom2)) #this horizontally places chrom1 and chrom2. each row is chrom1 and chrom2 of an individual. left part = chrom1, right part = chrom2
	
	# pick random pairs of parents 
	pairs = np.resize(np.random.choice(len(surv_stacked), size=len(surv_stacked), replace=False), (int(len(surv_stacked)/2), 2))

	#determine the gamates of parents 
	parent1_gamete1 = surv_chrom1[pairs[:, 0]] #pick the chrom1 of the parents (pick the related rows, 0th element of pairs )
	parent1_gamete2 = surv_chrom2[pairs[:, 0]]

	parent2_gamete1 = surv_chrom1[pairs[:, 1]]
	parent2_gamete2 = surv_chrom2[pairs[:, 1]]

	parent1 = np.vstack((parent1_gamete1, parent1_gamete2)) #vertically add the two gametes. this gives overall genotype of parents. each row is one gamete 
	parent2 = np.vstack((parent2_gamete1, parent2_gamete2))

	#from which parent offsprings inherit each allele
	off1_chroms = np.random.randint(2, size=(len(pairs), 2)) # from which chrom to draw for off1 [p1, p2] #gives an array of 1 and 0. number of rows = number of rows of pairs. number of columns = number of rows of surv_stacked
	off2_chroms = abs(1-off1_chroms) #opposite of rand for the other offspring (the other offspring inherits the alleles from the other parent for the related loci)

	off_chrom1 = np.stack((off1_chroms[:, 0], off2_chroms[:, 0]), axis = 1).reshape(N_adapts[0], 1)
	off_chrom2 = np.stack((off1_chroms[:, 1], off2_chroms[:, 1]), axis = 1).reshape(N_adapts[0], 1)

	#create the related indices 
	even_nums = np.repeat(np.arange(0, (N_adapts[0] - 1), 2), 2).reshape(N_adapts[0], 1) #produce a list of even numbers from 0 to Nadapts - 1, not including the stop. 

	off_chrom1_index = off_chrom1 + even_nums.reshape(N_adapts[0], 1)
	off_chrom2_index = off_chrom2 + even_nums.reshape(N_adapts[0], 1)

	off = np.hstack((parent1[(off_chrom1_index)], parent2[(off_chrom2_index)])).reshape(N_adapts[0], np.shape(parent1_gamete1)[1] * 2)       #(np.size(off1_chroms, 1))) #stack the same rows from two arrays together and reformat. each row is one offspring. 
	
	return off

def mutate(off, u, alpha, n, mut):
	"""
	This function creates mutations and updates population
	"""
	rand3 = np.random.uniform(size = len(off)) #random uniform number in [0,1] for each offspring [or loci??]. (creates number of off random numbers as between 0 and 1) size = number of columns of off (number of individuals)
	nmuts = sum(rand3 < u_adapt) # mutate if random number is below mutation rate; returns number of new mutations. 
	whomuts = np.where(rand3 < u_adapt) #indices of mutants. each refer to the index of the individuals in the off matrix. 
	newmuts = np.random.normal(0, alpha, size = (nmuts, n)) #phenotypic effect of new mutations. 0=mean, alpha=sd (how far you from the mean) rows:nmuts coloumns=n. each pair is x and y coordinates. they tell you how far and which direction you go away from the origin 
	
	#pop = np.append(off, np.transpose(np.identity(len(off), dtype=int)[whomuts[0]]), axis=1) #add new loci and identify mutants. from the identity array, only pick the rows of individuls that had a lower nmuts value than alpha. then append them next to the individuals themselves. 
	pop_chrom1 = np.split(off, 2, axis = 1)[0] #split the off array into 2 column wise. left side chrom1, right is chrom2. 
	pop_chrom2 = np.split(off, 2, axis = 1)[1]
	
	#update pop_chrom1
	added_muts = np.transpose(np.identity(len(off), dtype=int)[whomuts[0]]) #pick the rows of mutated individuals from the identity array
	pop_chrom1 = np.append(pop_chrom1, added_muts, axis=1) #update pop_chrom1 by appending the mutation matrix

	#update pop_chrom2
	zero = np.zeros(N_adapts[0] * np.shape(added_muts)[1]).reshape(N_adapts[0], np.shape(added_muts)[1]).astype(int) #create an array of zeros. rows: n_adapts columns: same as added_muts. chrom2 doesnt mutate, so we add the zeros array. 
	pop_chrom2 = np.append(pop_chrom2, zero, axis = 1) #append zero array to chrom2

	#append pop_chrom1 and pop_chrom2 horizontally to make the pop matrix. each row is one individual. each row has the both chromosomes. left: chrom1 right: chrom2
	pop_genotype = np.append(pop_chrom1, pop_chrom2, axis = 1) #both chromosomes present

	pop_overall = (pop_chrom1 + pop_chrom2) / 2 #chromosomes averaged 

	mut = np.vstack((mut, newmuts)) #append effect of new mutations to mutation list

	return [pop_genotype, pop_overall, mut]

def which_index(pop):
	return np.array([
		i for i in range(len(pop))
		if pop[i] == False ])

def remove_muts(pop, mut): #here pop is the same thing as off
	"""
	This function creates mutations and updates population
	"""
	#convert mut from a list to an array 
	mut = np.array(mut)

	#split the pop into chrom1 and chrom2. 
	pop_chrom1 = np.split(pop, 2, axis = 1)[0]
	pop_chrom2 = np.split(pop, 2, axis = 1)[1]

	chrom1_zero = np.where(~pop_chrom1.any(axis = 0))[0] #find the columns that are all zeros
	chrom2_zero = np.where(~pop_chrom2.any(axis = 0))[0]

	remove = np.intersect1d(chrom1_zero, chrom2_zero) #find the indices where the two arrays have 0 in the same columns 

	if len(remove) == 0:
		pop_genotype = [pop_chrom1, pop_chrom2]

	else: 
		pop_chrom1 = np.delete(pop_chrom1, remove, 1) # delete the columns that are all zeros 
		pop_chrom2 = np.delete(pop_chrom2, remove, 1)
		pop_genotype = [pop_chrom1, pop_chrom2] #horizontally reattach the chromosomes and make the pop

		mut = np.delete(mut, remove, 0) #remove the lost loci by removing the related rows

	pop_overall = (pop_chrom1 + pop_chrom2) / 2 
	
	return[pop_genotype, pop_overall, mut]


######################################################################
##UNIVERSAL PARAMETERS##
######################################################################

nreps = 1 #number of replicates for each set of parameters
ns = [2] #phenotypic dimensions (positive integer >=1)
n = 2

######################################################################
##PARAMETERS FOR ADAPTING POPULATIONS##
######################################################################

N_adapts = [200] #number of diploid individuals (positive integer)
N_adapt = 200

alpha_adapt = 0.1 #mutational sd (positive real number)
alpha = alpha_adapt

u_adapt = 0.01 #mutation probability per generation per genome (0<u<1). if this is 0.5, this means half of the population is likely to mutate 

sigma_adapt = [1] #selection strengths
sigma_adapt = 1

opt_dist = 1 #distance to optima

n_angles = 2 #number of angles between optima to simulate (including 0 and 180) (>=2)

maxgen = 500 #total number of generations populations adapt for

# dominance = ['no_dom', 'variable']

######################################################################
##PARAMETERS FOR HYBRIDS##
######################################################################

nHybrids = 200 #number of hybrids to make at end of each replicate

######################################################################
##FUNCTION FOR POPULATIONS TO ADAPT##
######################################################################


#set n-dependent parameters
theta1 = np.append(opt_dist,[0]*(n-1)) #set one optima to be fixed
angles = [math.pi*x/(n_angles-1) for x in range(n_angles)] #angles to use (in radians)
if n == 2:
	theta2_list = np.array([[opt_dist*math.cos(x), opt_dist*math.sin(x)] for x in angles]) #optima to use
elif n > 2:
	theta2_list = np.array([np.append([opt_dist*math.cos(x), opt_dist*math.sin(x)], [0]*(n-2)) for x in angles]) #optima to use
theta2 = theta1

#loop over optima
j = 0
while j < len(theta2_list):
	
	#set optima
	theta2 = theta2_list[j]

	# #set up plot of hybrid load versus number of ancestral mutations (n_muts)
	# plt.axis([0, max(n_mut_list)+1, 0, 0.1])
	# plt.ylabel('hybrid load at generation %d (mean $\pm$ SD of %d replicates)' %(maxgen,nreps))
	# plt.xlabel('number of ancestral mutations')
	# plt.ion()

	#loop over all replicates
	rep = 0
	while rep < nreps:

		#found identical populations
		popfound1 = np.array([[1]] * N_adapt) #this creates an array of 1 coloumn of ones and N_adapt times rows. 
		popfound2 = np.array([[1]] * N_adapt) 
		popfound = np.column_stack((popfound1, popfound2)) # create a diploid genotype. #of columns= #of chromosomes 

		mut = np.array([[0] * n]) #similar to above. filled with zeroes. number of coloumns: n. rows: 1. convert to a list 

		[pop1, mut1] = [popfound, mut] # this creates pop and mut arrays for both parents. they are the same because we start from the same point. 
		[pop2, mut2] = [popfound, mut] # mut1 = how farther you go from the origin due to mutations in pop1. same for mut2

		# mut1_1 = np.split(mut1, 2, axis = 0)[0]
		# mut1_2 = np.split(mut1, 2, axis = 0)[0]

		# mut2_1 = np.split(mut2, 2, axis = 0)[0]
		# mut2_2 = np.split(mut2, 2, axis = 0)[0]

		pop1_chrom1 = popfound1 # genotype of 1st chromosome of pop1
		pop1_chrom2 = popfound1 # genotype of 2nd chromosome of pop1

		pop2_chrom1 = popfound2 # 1st chromosome of pop2
		pop2_chrom2 = popfound2 # 2nd chromosome of pop2

		pop1_overall = ((pop1_chrom1 + pop1_chrom2) / 2 ) # two chromosomes of pop1 averaged
		pop2_overall = ((pop2_chrom1 + pop2_chrom2) / 2 ) # two chromosomes of pop2 averaged
		
		# intitialize generation counter
		gen = 0

		# run until maxgen
		while gen < maxgen + 1:

			# genotype to phenotype (diploid):
			phenos1 = np.dot(pop1_overall, mut1) #sum mutations held by each individual
			phenos2 = np.dot(pop2_overall, mut2) #sum mutations held by each individual

			# phenotype to fitness
			w1 = fitness(phenos1, theta1, sigma_adapt)
			w2 = fitness(phenos2, theta2, sigma_adapt)

			# wright-fisher (multinomial) sampling
			parents1 = np.random.multinomial(N_adapt, w1/sum(w1))
			off1_chrom1 = np.repeat(pop1_overall, parents1, axis = 0) 
			off1_chrom2 = np.repeat(pop1_overall, parents1, axis = 0)
			off1 = [off1_chrom1, off1_chrom2]
			
			parents2 = np.random.multinomial(N_adapt, w2/sum(w2)) # number of times each parent chosen
			off2_chrom1 = np.repeat(pop2_overall, parents2, axis = 0) # offspring genotypes of pop2
			off2_chrom2 = np.repeat(pop2_overall, parents2, axis = 0)
			off2 = [off2_chrom1, off2_chrom2]

			# mating and recombination
			off1 = recomb(off1)
			off2 = recomb(off2)

			[pop1_genotype, pop1_overall, mut1] = mutate(off1, u_adapt, alpha_adapt, n, mut1)
			[pop2_genotype, pop2_overall, mut2] = mutate(off2, u_adapt, alpha_adapt, n, mut2)

			#create the dominance coefficient array (h)
			#pick random numbers (float) between 0 and 1. pick as many as the number of rows. of mut. only 1 column.
			#replace the values 0.5 with the h. 
			
			# h_pop1 = np.random.uniform(low = 0, high = 1, size = len(pop1_overall[pop1_overall == 0.5]))
			# pop1_overall[pop1_overall == 0.5] = h_pop1

			# h_pop2 = np.random.uniform(low = 0, high = 1, size = len(pop2_overall[pop2_overall == 0.5]))
			# pop2_overall[pop2_overall == 0.5] = h_pop2

			# remove lost mutations (all zero columns in pop)
			[pop1_genotype, pop1_overall, mut1] = remove_muts(pop1_genotype, mut1)
			[pop2_genotype, pop2_overall, mut2] = remove_muts(pop2_genotype, mut2)

			# go to next generation
			gen += 1

		#HYBRIDIZATION - always choose parents from different populations 

		#genotype of hybrids

		pop1_chrom1 = pop1_genotype[0]
		pop1_chrom2 = pop1_genotype[1]

		pop2_chrom1 = pop2_genotype[0]
		pop2_chrom2 = pop2_genotype[1]
		
		#make the zero matrices
		pop1_zero1 = np.zeros(len(pop1_chrom1) * pop2_chrom1.shape[1]).reshape(len(pop2_chrom1), pop2_chrom1.shape[1])
		pop1_zero2 = np.zeros(len(pop1_chrom2) * pop2_chrom2.shape[1]).reshape(len(pop2_chrom2), pop2_chrom2.shape[1])

		pop2_zero1 = np.zeros(len(pop2_chrom1) * pop1_chrom1.shape[1]).reshape(len(pop1_chrom1), pop1_chrom1.shape[1])
		pop2_zero2 = np.zeros(len(pop2_chrom2) * pop1_chrom2.shape[1]).reshape(len(pop1_chrom2), pop1_chrom2.shape[1])


		#attach the zero matrices
		pop1_chrom1_has0 = np.hstack((pop1_chrom1, pop1_zero1))
		pop1_chrom2_has0 = np.hstack((pop1_chrom2, pop1_zero2))

		pop2_chrom1_has0 = np.hstack((pop2_zero1, pop2_chrom1))
		pop2_chrom2_has0 = np.hstack((pop2_zero2, pop2_chrom2))

		#make pairs
		pairs_hybrid = np.resize(np.random.choice(len(pop1_chrom1), size=len(pop1_chrom1), replace=False), (int(len(pop1_chrom1)/2), 2))

		#pick the related chromosomes of the pairs  
		pop1_chrom1_hy = pop1_chrom1_has0[pairs_hybrid[:, 0]]
		pop1_chrom2_hy = pop1_chrom2_has0[pairs_hybrid[:, 0]]

		pop2_chrom1_hy = pop2_chrom1_has0[pairs_hybrid[:, 1]]
		pop2_chrom2_hy = pop2_chrom2_has0[pairs_hybrid[:, 1]]

		#recombination:
		#randomly pick 0, 1, 2, or 3 to decide which pairs to match 

		num = np.random.randint(2, size = 1).tolist()

		if num[0] == 0:
			F1_before_recomb1 = np.concatenate(np.stack((pop1_chrom1_hy, pop2_chrom1_hy), axis = 1))
			F1_after_recomb1 = crossover(F1_before_recomb1)
			F1_after_recomb1_chrom1 = F1_after_recomb1[::2] #picks every other odd row, chrom1
			F1_after_recomb1_chrom2 = F1_after_recomb1[1::2] #picks every other even row, chrom2

			
			F1_before_recomb2 = np.concatenate(np.stack((pop1_chrom2_hy, pop2_chrom2_hy), axis = 1))
			F1_after_recomb2 = crossover(F1_before_recomb2)
			F1_after_recomb2_chrom1 = F1_after_recomb2[::2] #picks every other odd row, chrom1
			F1_after_recomb2_chrom2 = F1_after_recomb2[1::2] #picks every other even row, chrom2


		elif num[0] == 1:
			F1_before_recomb1 = np.concatenate(np.stack((pop1_chrom1_hy, pop2_chrom2_hy), axis = 1))
			F1_after_recomb1 = crossover(F1_before_recomb1)
			F1_after_recomb1_chrom1 = F1_after_recomb1[::2] #picks every other odd row, chrom1
			F1_after_recomb1_chrom2 = F1_after_recomb1[1::2] #picks every other even row, chrom2

			F1_before_recomb2 = np.concatenate(np.stack((pop1_chrom2_hy, pop2_chrom1_hy), axis = 1))
			F1_after_recomb2 = crossover(F1_before_recomb2)
			F1_after_recomb2_chrom1 = F1_after_recomb2[::2] #picks every other odd row, chrom1
			F1_after_recomb2_chrom2 = F1_after_recomb2[1::2] #picks every other even row, chrom2

		#hybrid phenotypes
		mut_hybrid = np.vstack((mut1, mut2))

		#averaged hybrid genotypes to calculate the hybrid phenotypes 
		hybrid_overall_recomb1 = (F1_after_recomb1_chrom2 + F1_after_recomb1_chrom1) / 2
		hybrid_overall_recomb2 = (F1_after_recomb2_chrom2 + F1_after_recomb2_chrom1) / 2

		hybrid_overall_all = np.vstack((hybrid_overall_recomb1, hybrid_overall_recomb2)) #stack all hybrids phenos. each row is one individual. 
		
		#dominance coefficient: 
		# h_hybrid = np.random.uniform(low = 0, high = 1, size = len(hybrid_overall_all[hybrid_overall_all == 0.5]))
		# hybrid_overall_all[hybrid_overall_all == 0.5] = h_hybrid

		hybrid_pheno = np.dot(hybrid_overall_all, mut_hybrid)


		# #save hybrid phenotype data (to make hybrid clouds)
		pheno_data = np.column_stack([np.array([i+1 for i in range(len(hybrid_pheno))]), np.array([rep+1]*len(hybrid_pheno)), np.array([round(angles[j]*180/math.pi,2)]*len(hybrid_pheno)), np.array([opt_dist * (2*(1-math.cos(angles[j])))**(0.5)]*len(hybrid_pheno)), hybrid_pheno]) #make hybrid phenotype data (with a bunch of identifiers in front of each phenotype)
		np.savetxt(fileHandle_B, pheno_data, fmt='%.3f', delimiter=',') #save

		#save summary data
		write_data_to_output(fileHandle_A, [round(angles[j]*180/math.pi,2), rep+1, opt_dist * (2*(1-math.cos(angles[j])))**(0.5)]) #rhfit was in the equation, but i removed. juy 26

		#print an update
		print('N = %d, sigma = %.2f, n=%d, angle=%r, rep=%d' %(N_adapt, sigma_adapt, n, round(angles[j]*180/math.pi,2), rep+1)) 