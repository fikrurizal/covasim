''' Test/example for changing from a constant viral
load to a simple time varying viral load.'''
import sciris as sc
import covasim as cv
import numpy as np
from scipy.special import kl_div

runs = 301
r0_const = np.zeros(runs)
r0_twolevel = np.zeros(runs)
r0_twolevel2 = np.zeros(runs)
base_pars = sc.objdict(
        n_days       = 12,   # Number of days to simulate
        asymp_factor = 1, # Multiply beta by this factor for asymptomatic cases
        diag_factor  = 1, # Multiply beta by this factor for diganosed cases -- baseline assumes complete isolation
        verbose = 0,
        pop_infected = 1
)
base_pars['dur'] = {}
base_pars['dur']['exp2inf']  = {'dist':'normal_int', 'par1':4, 'par2':0} # Duration from exposed to infectious
base_pars['dur']['inf2sym']  = {'dist':'normal_int', 'par1':0, 'par2':0} # Duration from infectious to symptomatic
base_pars['dur']['sym2sev']  = {'dist':'normal_int', 'par1':0, 'par2':0} # Duration from symptomatic to severe symptoms
base_pars['dur']['sev2crit'] = {'dist':'normal_int', 'par1':0, 'par2':0} # Duration from severe symptoms to requiring ICU

# Duration parameters: time for disease recovery
base_pars['dur']['asym2rec'] = {'dist':'normal_int', 'par1':0,  'par2':0} # Duration for asymptomatics to recover
base_pars['dur']['mild2rec'] = {'dist':'normal_int', 'par1':8,  'par2':0} # Duration from mild symptoms to recovered
base_pars['dur']['sev2rec']  = {'dist':'normal_int', 'par1':0, 'par2':0} # Duration from severe symptoms to recovered - leads to mean total disease time of
base_pars['dur']['crit2rec'] = {'dist':'normal_int', 'par1':0, 'par2':0} # Duration from critical symptoms to recovered
base_pars['dur']['crit2die'] = {'dist':'normal_int', 'par1':0,  'par2':0} # Duration from critical symptoms to death

base_pars['OR_no_treat']     = 1.0  # Odds ratio for how much more likely people are to die if no treatment available
base_pars['rel_symp_prob']   = 2.0  # Scale factor for proportion of symptomatic cases
base_pars['rel_severe_prob'] = 0  # Scale factor for proportion of symptomatic cases that become severe
base_pars['rel_crit_prob']   = 0  # Scale factor for proportion of severe cases that become critical
base_pars['rel_death_prob']  = 0  # Scale factor for proportion of critical cases that result in death
base_pars['prog_by_age']     = False    
    
for i in range(runs):
    # Configure the sim -- can also just use a normal dictionary
    pars = base_pars
    pars['rand_seed'] = i*np.random.rand()
    pars['viral_distro'] = {'dist':'constant'}
    print('Making sim ', i, '...')
    sim1 = cv.Sim(pars=pars)
    sim1.run()
    r0_const[i] = len(sim1.people[0].infected)
    pars['rand_seed'] = i*np.random.rand()
    pars['viral_distro'] = {'dist':'twolevel', 'frac':.5, 'ratio':2}
    sim2 = cv.Sim(pars=pars)
    sim2.run()
    r0_twolevel[i] = len(sim2.people[0].infected)
    pars['rand_seed'] = i*np.random.rand()
    pars['viral_distro'] = {'dist':'twolevel', 'frac':.3, 'ratio':3}
    sim3 = cv.Sim(pars=pars)
    sim3.run()
    r0_twolevel2[i] = len(sim3.people[0].infected)

print('R0 constant viral load: ', np.mean(r0_const), ' +- ', np.std(r0_const))
print('R0 two level viral load: ', np.mean(r0_twolevel), ' +- ', np.std(r0_twolevel))
print('R0 two level diff params: ', np.mean(r0_twolevel2), ' +- ', np.std(r0_twolevel2))

import matplotlib.pyplot as plt
hist1 = plt.hist(r0_const, bins=np.arange(-0.5, 11.5), density=True)
hist2 = plt.hist(r0_twolevel, bins=np.arange(-0.5, 11.5), density=True)
hist3 = plt.hist(r0_twolevel2, bins=np.arange(-0.5, 11.5), density=True)
plt.show()
assert(abs(np.mean(r0_const)-np.mean(r0_twolevel))<np.std(r0_const))
assert(abs(np.mean(r0_const)-np.mean(r0_twolevel2))<np.std(r0_const))
assert(abs(np.mean(r0_twolevel)-np.mean(r0_twolevel2))<np.std(r0_twolevel))
# taking the min because if the second distribution has a 0 where the first
# does not kl_div gives inf.
assert(min(sum(kl_div(hist1[0], hist2[0])), sum(kl_div(hist2[0], hist1[0])))<1)
assert(min(sum(kl_div(hist1[0], hist3[0])), sum(kl_div(hist3[0], hist1[0])))<1)
assert(min(sum(kl_div(hist2[0], hist3[0])), sum(kl_div(hist3[0], hist2[0])))<1)