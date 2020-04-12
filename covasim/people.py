'''
Defines the Person class and functions associated with making people.
'''

#%% Imports
import numpy as np
from . import utils as cvu
from . import defaults as cvd
from . import base as cvb


# Specify all externally visible functions this file defines
__all__ = ['People']



class People(cvb.BasePeople):
    '''
    A class to perform all the operations on the people.
    '''

    def __init__(self, pars=None, pop_size=None, **kwargs):
        super().__init__(pars, pop_size)

        # Set person properties -- mostly floats
        for key in self.keylist.person:
            if key == 'uid':
                self[key] = np.arange(self.pop_size, dtype=object)
            else:
                self[key] = np.full(self.pop_size, np.nan, dtype=self._default_dtype)

        # Set health states -- only susceptible is true by default -- booleans
        for key in self.keylist.states:
            if key == 'susceptible':
                self[key] = np.full(self.pop_size, True, dtype=bool)
            else:
                self[key] = np.full(self.pop_size, False, dtype=bool)

        # Set dates and durations -- both floats
        for key in self.keylist.dates + self.keylist.durs:
            self[key] = np.full(self.pop_size, np.nan, dtype=self._default_dtype)

        # Store the dtypes used
        self._dtypes = {key:self[key].dtype for key in self.keys()} # Assign all to float by default
        self._lock = True # Stop further attributes from being set

        # Set any values, if supplied
        if 'contacts' in kwargs:
            self.add_contacts(kwargs.pop('contacts'))
        for key,value in kwargs.items():
            self.set(key, value)

        return


    def set_prognoses(self, pars=None):
        ''' Set the prognoses for each person based on age '''
        if pars is None:
            pars = self.pars

        def find_cutoff(age_cutoffs, age):
            return np.argmax(age_cutoffs > age)  # Index of the age bin to use

        prognoses = pars['prognoses']
        age_cutoffs = prognoses['age_cutoffs']
        inds = np.fromiter((find_cutoff(age_cutoffs, this_age) for this_age in self.age), dtype=np.int32, count=len(self))
        self.symp_prob   = self.pars['rel_symp_prob']   * prognoses['symp_probs'][inds]
        self.severe_prob = pars['rel_severe_prob'] * prognoses['severe_probs'][inds]
        self.crit_prob   = pars['rel_crit_prob']   * prognoses['crit_probs'][inds]
        self.death_prob  = pars['rel_death_prob']  * prognoses['death_probs'][inds]
        return


    def update_states(self, t):
        ''' Perform all state updates '''

        counts = {key:0 for key in cvd.new_result_flows}

        # if self.count('severe') > n_beds:
        #     bed_constraint = True

        # For storing the interim values since used in every subsequent calculation
        self._isexp = cvu.true(self.exposed)
        self.t = t
        self.verbose = True # TODO

        counts['new_infectious']  += self.check_infectious() # For people who are exposed and not infectious, check if they begin being infectious
        counts['new_symptomatic'] += self.check_symptomatic()
        # counts['new_severe']      += self.check_severe()
        # counts['new_critical']    += self.check_critical()
        # counts['new_deaths']      += self.check_death()
        # counts['new_recoveries']  += self.check_recovery()
        # counts['new_quarantined'] += self.check_quar(t=t) # Update if they're quarantined

        return counts


    # def update_contacts(self, t):
    #     # Set community contacts

    #             if 'c' in self['contacts']:
    #         n_comm_contacts = self['contacts']['c'] # Community contacts; TODO: make less ugly
    #     else:
    #         n_comm_contacts = 0

    #     person_contacts = person.contacts
    #     if n_comm_contacts:
    #         community_contact_inds = cvu.choose(max_n=pop_size, n=n_comm_contacts)
    #         person_contacts['c'] = community_contact_inds


    # def stuff():
    #     thisbeta = beta * \
    #                (asymp_factor if not person.symptomatic else 1.) * \
    #                (diag_factor if person.diagnosed else 1.)

    #                    this_beta_layer = thisbeta *\
    #                               beta_layers[ckey] *\
    #                               (quar_trans_factor[ckey] if person.quarantined else 1.) # Reduction in onward transmission due to quarantine


    #     # Determine who gets infected
    #     for ckey in self.contact_keys:
    #         contact_ids = person_contacts[ckey]
    #         if len(contact_ids):

    #             transmission_inds = cvu.bf(this_beta_layer, contact_ids)
    #             for contact_ind in transmission_inds: # Loop over people who get infected
    #                 target_person = self.people[contact_ind]
    #                 if target_person.susceptible: # Skip people who are not susceptible

    #                     # See whether we will infect this person
    #                     infect_this_person = True # By default, infect them...
    #                     if target_person.quarantined:
    #                         infect_this_person = cvu.bt(quar_acq_factor) # ... but don't infect them if they're isolating # DJK - should be layer dependent!
    #                     if infect_this_person:
    #                         new_infections += target_person.infect(t, bed_constraint, source=person) # Actually infect them
    #                         sc.printv(f'        Person {person.uid} infected person {target_person.uid}!', 2, verbose)

    # asymp_factor     = self['asymp_factor']
    #     diag_factor      = self['diag_factor']
    #     quar_trans_factor= self['quar_trans_factor']
    #     quar_acq_factor  = self['quar_acq_factor']
    #     quar_period      = self['quar_period']
    #     beta_layers      = self['beta_layers']
    #     n_beds           = self['n_beds']
    #     bed_constraint   = False




    def make_susceptible(self, inds):
        """
        Make person susceptible. This is used during dynamic resampling
        """
        for key in self.keylist.states:
            if key == 'susceptible':
                self[key][inds] = True
            else:
                self[key][inds] = False

        for key in self.keylist.dates + self.keylist.durs:
            self[key][inds] = np.nan

        return


    #%% Methods for updating state

    def check_infectious(self):
        ''' Check if they become infectious '''
        ni_inds  = cvu.ifalse(self.infectious, self._isexp)
        bi_inds  = cvu.idefined(self.date_symptomatic, ni_inds)
        inf_inds = cvu.itrue(self.t >= self.date_infectious, bi_inds)
        self.infectious[inf_inds] = True
        if self.verbose:
            print('i am infec')
            print('exp', self._isexp)
            print('not', ni_inds)
            print('date', self.date_symptomatic[ni_inds])
            print('become', bi_inds)
            print(len(inf_inds))
            print(inf_inds)
        return len(inf_inds)


    def check_symptomatic(self):
        ''' Check for new progressions to symptomatic '''
        ns_inds   = cvu.ifalse(self.symptomatic, self._isexp)
        bs_inds   = cvu.idefined(self.date_symptomatic, ns_inds)
        symp_inds = cvu.itrue(self.t >= self.date_symptomatic, bs_inds)
        self.symptomatic[symp_inds] = True
        if self.verbose:
            print('i am symp')
            print(len(symp_inds))
            print(symp_inds)
        return len(symp_inds)


    def check_severe(self):
        ''' Check for new progressions to severe '''
        not_severe     = cvu.false(self.severe[self._is_exposed])
        becomes_severe = cvu.defined(self.date_severe[not_severe])
        severe_inds    = cvu.true(self.t >= self.date_severe[becomes_severe])
        self.severe[severe_inds] = True
        if self.verbose:
            print('i am sev')
            print(len(severe_inds))
            print(severe_inds)
        return len(severe_inds)


    def check_critical(self):
        ''' Check for new progressions to critical '''
        not_critical     = cvu.false(self.critical[self._is_exposed])
        becomes_critical = cvu.defined(self.date_critical[not_critical])
        critical_inds    = cvu.true(self.t >= self.date_critical[becomes_critical])
        self.critical[critical_inds] = True
        if self.verbose:
            print('i am crit')
            print(len(critical_inds))
            print(critical_inds)
        return len(critical_inds)


    def check_recovery(self):
        ''' Check if an infected person has recovered '''
        will_recover   = cvu.defined(self.date_recovered[self._is_exposed])
        recovered_inds = cvu.true(self.t >= self.date_recovered[will_recover])
        self.exposed[recovered_inds]     = False
        self.infectious[recovered_inds]  = False
        self.symptomatic[recovered_inds] = False
        self.severe[recovered_inds]      = False
        self.critical[recovered_inds]    = False
        self.recovered[recovered_inds]   = True
        if self.verbose:
            print('i am recov')
            print(len(recovered_inds))
            print(recovered_inds)
        return len(recovered_inds)


    def check_death(self):
        ''' Check whether or not this person died on this timestep  '''
        will_die   = cvu.defined(self.date_dead[self._is_exposed])
        dead_inds = cvu.true(self.t >= self.date_dead[will_die])
        self.exposed[dead_inds]     = False
        self.infectious[dead_inds]  = False
        self.symptomatic[dead_inds] = False
        self.severe[dead_inds]      = False
        self.critical[dead_inds]    = False
        self.recovered[dead_inds]   = False
        self.dead[dead_inds]        = True
        if self.verbose:
            print('i am dead')
            print(len(dead_inds))
            print(dead_inds)
        return len(dead_inds)


    def check_diagnosed(self):
        ''' Check for new diagnoses '''
        not_diagnosed     = cvu.false(self.diagnosed[self._is_exposed])
        becomes_diagnosed = cvu.defined(self.date_diagnosed[not_diagnosed])
        diagnosed_inds    = cvu.true(self.t >= self.date_diagnosed[becomes_diagnosed])
        self.diagnosed[diagnosed_inds] = True
        if self.verbose:
            print('i am diag')
            print(len(diagnosed_inds))
            print(diagnosed_inds)
        return len(diagnosed_inds)


    # def check_quar_begin(self, quar_period=None):
    #     ''' Check for whether someone has been contacted by a positive'''
    #     if (quar_period is not None) and (self.date_known_contact is not None) and (t >= self.date_known_contact):
    #         # Begin quarantine
    #         was_quarantined = self.quarantined
    #         self.quarantine(t, quar_period)
    #         self.date_known_contact = None # Clear
    #         return not was_quarantined
    #     return 0


    # def check_quar_end(self):
    #     ''' Check for whether someone is isolating/quarantined'''
    #     if self.quarantined and (self.end_quarantine is not None) and (t >= self.end_quarantine):
    #         self.quarantined = False # Release from quarantine
    #         self.end_quarantine = None # Clear end quarantine time
    #         #sc.printv(f'Released {self.uid} from quarantine', 2, verbose)
    #     return self.quarantined



    #%% Methods to make events occur (infection and diagnosis)

    def infect(self, inds, t, bed_constraint=None, source=None, verbose=True):
        """
        Infect this person and determine their eventual outcomes.
            * Every infected person can infect other people, regardless of whether they develop symptoms
            * Infected people that develop symptoms are disaggregated into mild vs. severe (=requires hospitalization) vs. critical (=requires ICU)
            * Every asymptomatic, mildly symptomatic, and severely symptomatic person recovers
            * Critical cases either recover or die

        Args:
            inds (array): array of people to infect
            t (int): current timestep
            bed_constraint: (bool) whether or not there is a bed available for this person
            source: (Person instance), if None, then it was a seed infection

        Returns:
            count (int): number of people infected
        """
        n_infections = len(inds)
        durpars = self.pars['dur']
        self.susceptible[inds]    = False
        self.exposed[inds]        = True
        self.date_exposed[inds]   = t

        # Deal with bed constraint if applicable
        if bed_constraint is None: bed_constraint = False

        # Calculate how long before this person can infect other people
        self.dur_exp2inf[inds]     = cvu.sample(**durpars['exp2inf'], size=n_infections)
        self.date_infectious[inds] = self.dur_exp2inf[inds] + t
        print('hiiiii infectiuos dates')
        print(inds)
        print(self.dur_exp2inf)
        print(self.date_infectious)

        # Use prognosis probabilities to determine what happens to them
        is_symp = cvu.binomial_arr(self.symp_prob[inds]) # Determine if they develop symptoms
        symp_inds = inds[is_symp]
        asymp_inds = inds[~is_symp] # Asymptomatic
        print('hiiiii2 symptomatic')
        print(symp_inds) # TODO WHY EMPTY
        print(asymp_inds)

        # CASE 1: Asymptomatic: may infect others, but have no symptoms and do not die
        dur_asym2rec = cvu.sample(**durpars['asym2rec'], size=len(asymp_inds))
        self.date_recovered[asymp_inds] = self.date_infectious[asymp_inds] + dur_asym2rec  # Date they recover
        self.dur_disease[asymp_inds] = self.dur_exp2inf[asymp_inds] + dur_asym2rec  # Store how long this person had COVID-19
        print('hiiiii3 asymptomatic')
        print(self.date_recovered)
        print(self.dur_disease)

        # CASE 2: Symptomatic: can either be mild, severe, or critical
        n_symp_inds = len(symp_inds)
        self.dur_inf2sym[symp_inds] = cvu.sample(**durpars['inf2sym'], size=n_symp_inds) # Store how long this person took to develop symptoms
        self.date_symptomatic[symp_inds] = self.date_infectious[symp_inds] + self.dur_inf2sym[symp_inds] # Date they become symptomatic
        is_sev = cvu.binomial_arr(self.severe_prob[symp_inds]) # See if they're a severe or mild case
        sev_inds = symp_inds[is_sev]
        mild_inds = symp_inds[~is_sev] # Not severe
        print('hiiiii4 sev/mild')
        print(sev_inds)
        print(mild_inds)

        # CASE 2.1: Mild symptoms, no hospitalization required and no probaility of death
        dur_mild2rec = cvu.sample(**durpars['mild2rec'], size=len(mild_inds))
        self.date_recovered[mild_inds] = self.date_symptomatic[mild_inds] + dur_mild2rec  # Date they recover
        self.dur_disease[mild_inds] = self.dur_exp2inf[mild_inds] + self.dur_inf2sym[mild_inds] + dur_mild2rec  # Store how long this person had COVID-19
        print('hiiiii5 mild recovery')
        print(self.date_recovered)
        print(self.dur_disease)


        # CASE 2.2: Severe cases: hospitalization required, may become critical
        self.dur_sym2sev[sev_inds] = cvu.sample(**durpars['sym2sev'], size=len(sev_inds)) # Store how long this person took to develop severe symptoms
        self.date_severe[sev_inds] = self.date_symptomatic[sev_inds] + self.dur_sym2sev[sev_inds]  # Date symptoms become severe
        is_crit = cvu.binomial_arr(self.crit_prob[sev_inds])  # See if they're a critical case
        crit_inds = sev_inds[is_crit]
        non_crit_inds = sev_inds[~is_crit]
        print('hiiiii6 crit/noncrit')
        print(crit_inds)
        print(non_crit_inds)

        # CASE 2.2.1 Not critical - they will recover
        dur_sev2rec = cvu.sample(**durpars['sev2rec'], size=len(non_crit_inds))
        self.date_recovered[non_crit_inds] = self.date_severe[non_crit_inds] + dur_sev2rec  # Date they recover
        self.dur_disease[non_crit_inds] = self.dur_exp2inf[non_crit_inds] + self.dur_inf2sym[non_crit_inds] + self.dur_sym2sev[non_crit_inds] + dur_sev2rec  # Store how long this person had COVID-19
        print('hiiiii7 crit recovery')
        print(self.date_recovered)
        print(self.dur_disease)


        # CASE 2.2.2: Critical cases: ICU required, may die
        self.dur_sev2crit[crit_inds] = cvu.sample(**durpars['sev2crit'], size=len(crit_inds))
        self.date_critical[crit_inds] = self.date_severe[crit_inds] + self.dur_sev2crit[crit_inds]  # Date they become critical
        this_death_prob = self.death_prob[crit_inds] * (self.pars['OR_no_treat'] if bed_constraint else 1.) # Probability they'll die
        is_dead = cvu.binomial_arr(this_death_prob)  # Death outcome
        dead_inds = crit_inds[is_dead]
        alive_inds = crit_inds[~is_dead]
        print('hiiiii8 alive/dead')
        print(dead_inds)
        print(alive_inds)

        # CASE 2.2.2.1: Did not die
        dur_crit2rec = cvu.sample(**durpars['crit2rec'], size=len(alive_inds))
        self.date_recovered[alive_inds] = self.date_critical[alive_inds] + dur_crit2rec # Date they recover
        self.dur_disease[alive_inds] = self.dur_exp2inf[alive_inds] + self.dur_inf2sym[alive_inds] + self.dur_sym2sev[alive_inds] + self.dur_sev2crit[alive_inds] + dur_crit2rec  # Store how long this person had COVID-19
        print('hiiiii9 did not die')
        print(self.date_recovered)
        print(self.dur_disease)

        # CASE 2.2.2.2: Did die
        dur_crit2die = cvu.sample(**durpars['crit2die'], size=len(dead_inds))
        self.date_dead[dead_inds] = self.date_critical[dead_inds] + dur_crit2die # Date of death
        self.dur_disease[dead_inds] = self.dur_exp2inf[dead_inds] + self.dur_inf2sym[dead_inds] + self.dur_sym2sev[dead_inds] + self.dur_sev2crit[dead_inds] + dur_crit2die   # Store how long this person had COVID-19
        print('hiiiii10 died')
        print(self.date_dead)
        print(self.dur_disease)

        if verbose:
            print(len(inds))
            print(inds)
            print(self.exposed.sum())
            print(self.infectious.sum())

        # if source:
        #     self.infected_by = source.uid
        #     source.infected.append(self.uid)

        return n_infections # For incrementing counters


    # def trace_dynamic_contacts(self, trace_probs, trace_time, ckey='c'):
    #     '''
    #     A method to trace a person's dynamic contacts, e.g. community
    #     '''
    #     if ckey in self.contacts:
    #         this_trace_prob = trace_probs[ckey]
    #         new_contact_keys = cvu.bf(this_trace_prob, self.contacts[ckey])
    #         self.dyn_cont_ppl.update({nck:trace_time[ckey] for nck in new_contact_keys})
    #     return


    # def trace_static_contacts(self, trace_probs, trace_time):
    #     '''
    #     A method to trace a person's static contacts, e.g. home, school, work
    #     '''
    #     contactable_ppl = {}  # Store people that are contactable and how long it takes to contact them
    #     for ckey in self.contacts.keys():
    #         if ckey != 'c': # Don't trace community contacts - it's too hard, because they change every timestep
    #             these_contacts = self.contacts[ckey]
    #             if len(these_contacts):
    #                 this_trace_prob = trace_probs[ckey]
    #                 new_contact_keys = cvu.bf(this_trace_prob, these_contacts)
    #                 contactable_ppl.update({nck: trace_time[ckey] for nck in new_contact_keys})

    #     return contactable_ppl


    # def test(self, t, test_sensitivity, loss_prob=0, test_delay=0):
    #     '''
    #     Method to test a person.

    #     Args:
    #         t (int): current timestep
    #         test_sensitivity (float): probability of a true positive
    #         loss_prob (float): probability of loss to follow-up
    #         test_delay (int): number of days before test results are ready

    #     Returns:
    #         Whether or not this person tested positive
    #     '''
    #     self.tested = True

    #     if self.date_tested is None: # First time tested
    #         self.date_tested = [t]
    #     else:
    #         self.date_tested.append(t) # They're been tested before; append new test date. TODO: adjust testing probs based on whether a person's a repeat tester?

    #     if self.infectious and cvu.bt(test_sensitivity):  # Person was tested and is true-positive
    #         needs_diagnosis = not self.date_diagnosed or self.date_diagnosed and self.date_diagnosed > t+test_delay
    #         if needs_diagnosis and not cvu.bt(loss_prob): # They're not lost to follow-up
    #             self.date_diagnosed = t + test_delay
    #         return 1
    #     else:
    #         return 0


    # def quarantine(self, t, quar_period):
    #     '''
    #     Quarantine a person starting on day t
    #     If a person is already quarantined, this will extend their quarantine
    #     '''
    #     self.quarantined = True

    #     new_end_quarantine = t + quar_period
    #     if self.end_quarantine is None or self.end_quarantine is not None and new_end_quarantine > self.end_quarantine:
    #         self.end_quarantine = new_end_quarantine

    #     #sc.printv(f'Person {self.uid} has been quarantined until {self.end_quarantine}', 2, self.verbose)

    #     return


