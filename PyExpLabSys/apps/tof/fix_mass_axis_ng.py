# -*- coding: utf-8 -*-
"""
Created on Mon Dec 19 14:38:40 2016

@author: CeliaCailloux
Program to fix x-axis on TOF-spectra """

from __future__ import print_function
import sys
import matplotlib.pyplot as plt
import numpy as np
import MySQLdb as mysql
from lmfit.models import GaussianModel
from lmfit import Parameters, minimize
#from PyExpLabSys.common.supported_versions import python2_and_3
#python2_and_3(__file__)


amplitudes = {} #used to determine min. amp for DBT minor peaks
rel_amp = {} #saves the rel. amps of the DBT minor peaks in comparison with the main peak 
spectrum_details = {}#key: spectrum number, value: usefull

good_fit = False #determines the goodness of the fit. Three categories. See plot title

''' Correct the time for the respective masses '''
def correct_fit_values(fit_values, data, count_fit, good_fit):
    usefull = {} #key: mass, value: the succes of the fit (True or False)
    fail = []# saves the reason for which the fitting fails.
    if count_fit == 0: 
        x_search = 25 #For H2, He and H2O
    elif good_fit == False:
        x_search = 75 # If some masses are not found, the fitting range is expanded       
    else:
        x_search = 75
                       
    for mass in list(fit_values.keys()):
        values = locate_peak(mass, data, fit_values, x_search)    
        usefull[mass], pars, fail = fit_peak(mass, values, time = fit_values[mass])

        ''' if the fit didn't succeed the mass is deleted from 
        the values for fitting. "fail" contains information of 
        the reason for the non-succes '''
        if usefull[mass] == True:
            fit_values[mass] = pars['center'] #
        else: 
            del fit_values[mass] 
            #print('No peak found for mass: ', mass, 'due to criterias concerning', fail )    

    count_fit += 1
    
    return fit_values, usefull, count_fit

''' Determines the range of data used for fitting'''    
def locate_peak(mass, data, fit_values, x_search):
    values = {} #fitting values
    center = np.where(data[:, 0] > fit_values[mass])[0][0]
    values['x'] = data[center - x_search:center + x_search, 0]
    values['y'] = data[center - x_search:center + x_search, 1]
    return values
    
''' Fits a gaussian peak using lmfit '''
def fit_peak(mass, values, time):#time, mass, data, fit_values, x_search, count_fit):     
    
    '''Defines the theoretical peak '''
    '''not necesarry for the script'''
    '''
    mod_theory = GaussianModel()
    
    #initial guess for the parameters 
    sigma_theory = np.sqrt(0.00001/2)    
    amp_theory = max(values['y']*(sigma_theory*np.sqrt(2*np.pi)))

    pars_theory = mod_theory.make_params(amplitude = 
        amp_theory, center = time, sigma = sigma_theory)
        
    fit_theory = mod_theory.fit(values['y'], pars_theory, x=values['x'])
    '''
    '''Fits a gaussian oeak on raw data'''
    '''The fitting parameters are guessed by the lmfit guess-function '''
     
    mod_raw = GaussianModel()
    pars = mod_raw.guess(values['y'], x=values['x'])
       
    fit_result = mod_raw.fit(values['y'], pars, x=values['x'])
    
    success = fit_result.success
    pars = fit_result.params
    pars_values = pars.valuesdict()   #listing the parameters in a default dictionary
    
    amplitudes[mass] = determine_amplitudes(mass, pars_values)
    

    sigma_max =np.sqrt(1.0e-3/2) #empirically determined. 
    
    if (184.0347 in amplitudes.keys()):
        amp_min = determine_amp_min(mass, amplitudes[184.0347])
        A_min = amp_min/(pars_values['sigma']*np.sqrt(2*np.pi)) #conversion from lmfit amp and "regular" amp
        
                  
        if A_min < 5:# Empirically determined
            A_min = 5
        
        #rel_amp_temp = pars_values['amplitude']/amplitudes[184.0347]
        
        ''' Only saves the min relative amp. for each minor DBT due to research.
        Used to determine the min. amp. Can be printed in the end '''
        '''if rel_amp_temp < rel_amp[mass]: 
            rel_amp[mass] = rel_amp_temp'''
                    
    else:
        A_min = 15 # For H2, He, H2O and DBT main peak
        rel_amp[mass] = 1
        
    #converting from lmfit defined amp to regular amp A
    A = pars['amplitude']/(pars_values['sigma']*np.sqrt(2*np.pi))
    
    
    # validates the fitted parameters      
    usefull = True
    fail = []
    
    #print(pars['sigma'])
    

    
    if not A >= A_min:
        usefull = False
        fail.append('amp')
      
    if not pars_values['sigma'] < sigma_max:
        usefull = False
        fail.append('sigma')
       
    if not success == 1:
        usefull = False
        fail.append('succes')
       
    
    ''' plots raw data and fitted function '''
    
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.set_title(mass)
    ax.plot(values['x'], values['y'], 'k-')
    ax.plot(values['x'], fit_result.best_fit, 'r-')
    #ax.plot(values['x'], fit_result.init_fit, 'c-')
    
    plt.show()
    
    
    
    
    return usefull, pars_values, fail

''' Determines the amp from the lmfit gaussian peak fitting''' 
def determine_amplitudes(mass, pars_values):
    amplitudes[mass] = pars_values['amplitude']
    return amplitudes[mass]

''' Minimum amplitudes are determines empirically'''
def determine_amp_min(mass, DBT_main_amp):
    amp_min = {}
    amp_min[182.0190] = 0.001*DBT_main_amp#39.54 #12*C+6*H+S
    amp_min[183.0268] = 0.013*DBT_main_amp #0.04 empirically determined
    amp_min[184.0347] = 1*DBT_main_amp
    amp_min[185.0380] = 0.045*DBT_main_amp #0.105 
    amp_min[186.0305] = 0.012*DBT_main_amp #0.035
    return amp_min[mass]

''' time to mass conversion '''    
def x_axis_fit_func(pars, time):
    time = np.asarray(time)
    pars_v = pars.valuesdict()
    mass = pars_v['b']*(time-pars_v['a'])**2
    return mass

''' mass to time conversion '''
def mass_to_time(pars, mass):
    pars_v = pars.valuesdict()
    time = np.sqrt(mass/pars_v['b']) + pars_v['a']
    return time

''' time to mass function used for fitting the x_axis'''  
def residual(pars, time, mass):
    pars_v = pars.valuesdict()
    return pars_v['b']*(time-pars_v['a'])**2-mass

''' fits the x_axis by minimizing the residual() function'''    
def fit_x_axis(fit_values, pars):    
        
    time = np.asarray(list(fit_values.values()))
    mass = np.asarray(list(fit_values.keys()))
    
    result = minimize(residual, pars, args=(time, mass))
                          
    #print(fit_report(result))
    pars = result.params#.valuesdict()
        
    return pars

'''imports data from the surfcat database '''
def import_data(spectrum_number):
    database = mysql.connect(host="servcinf-sql.fysik.dtu.dk", user="tof",
                                       passwd="tof", db="cinfdata")
    cursor = database.cursor()
    cursor.execute("SELECT x * 1000000,y FROM xy_values_tof where measurement = " +
                   str(spectrum_number))
    data = np.array(cursor.fetchall())
    return data

''' fit_values changes. "count_fit" keeps hold.
1st He, H2, H2O
2ns DBT main peak
3rd DBT minor peak '''    
def determine_fit_values(count_fit, pars):
    fit_values = {}
    
    if count_fit == 0:
        fit_values[1.00794] = 2.568
        fit_values[2.01565] = 3.80
        fit_values[4.00260] = 5.525
        fit_values[18.01056] = 12.17
        
        return fit_values, count_fit
    elif count_fit == 1:
        fit_values[184.0347] = mass_to_time(pars, 184.0347)
        return fit_values, count_fit        
    else:        
        ''' 
        The mass-isotop distribution for DBT are found on the website 
        http://www.chemcalc.org/analyse?mf=C12H7S&peakWidth=0.001&msResolution=183027&resolution=0.001&referenceVersion=2013
        '''          
        fit_values[182.0190] = mass_to_time(pars, 182.0190) #39.54 #12*C+6*H+S
        fit_values[183.0268] = mass_to_time(pars, 183.0268) #12*C+7*H+S # double peak
        #fit_values[184.0347] = mass_to_time(pars, 184.0347) #12*C+8*H+S
        fit_values[185.0380] = mass_to_time(pars, 185.0380) #11*C+C_13+8*H+S
        fit_values[186.0305] = mass_to_time(pars, 186.0305) #12*C+8*H+S_34   

        return fit_values, count_fit

''' set initial relative amp for DBT peaks'''        
def determine_rel_amp():
    rel_amp[182.0190] = 1    
    rel_amp[183.0268] = 1
    rel_amp[184.0347] = 1
#    rel_amp[185.0380] = 1
    rel_amp[186.0305] = 1

''' prints the masses which failed to fit for each spectrum '''    
def print_non_fitted_masses(usefull):   
    s = ''
    print('The masses that where not fitted are: ')
    for mass, value in usefull.items():
        if value == False:
            s += ' ' +  str(mass)
    print(s)

''' checks wether the fit is good or bad'''       
def check_good_fit(usefull, count_fit):    
    good = {}
    
    if count_fit <= 3:   
        #check wether H2, He and H2O were all fitted     
        for mass, value in usefull.items():
            if mass < 100:
                good[mass] = value
        return all(value == True for value in good.values())
    else: # generally checks if some masses failed to fit
        return all(value == True for value in usefull.values())
        
def plot_to_check(time, mass, mass_corrected, pars_x_axis, data):
        fig = plt.figure()
        
        ''' Plots the spectrum and mass-correction! '''
        
        axis = fig.add_subplot(2, 1, 1)
        axis.plot(time, mass - mass_corrected, 'bo')
        axis = fig.add_subplot(2, 1, 2)
        
        x_fit = np.arange(0, 20, 0.01)
        axis.plot(time, mass, 'bo')
        axis.plot(x_fit, x_axis_fit_func(pars_x_axis, x_fit), 'k-')
        plt.show()
    
        #fig = plt.figure()
        axis = fig.add_subplot(1, 1, 1)
        axis.plot(x_axis_fit_func(pars_x_axis, data[:, 0]), data[:, 1], 'k-')
        axis.set_xlim(1, 300)
        #print(pars_x_axis)
        plt.show()
        
    
def main():
    """Main function """
    max_mass_correction = {} 
    determine_rel_amp() #intializes all rel_amp[mass] to 1
    
    #x_axis fitting parameters 
    
    pars_a_good_fit = [] 
    pars_b_good_fit = [] 
    pars_a_ok_fit = []
    pars_b_ok_fit = []
    pars_a = [] 
    pars_b = []
    
    #records all spectrums that are analized
    spectra_list = []
    spectra_list_good_fit = []
    spectra_list_ok_fit = []
    spectra_list_rough_fit = []
            
    for spectrum_number in range(85598, 85610): 
        #spectrum_number = sys.argv[1]
        spectra_list.append(spectrum_number)
        
        #print("The entered spectrum number: ", spectrum_number)
        

        data = import_data(spectrum_number) #Imports one spectrum data from the surfcat database
        
        count_fit = 0 #counts the number x-axis (time_to_mass) fits
        
        #lmfit
        pars_x_axis = Parameters()
        
        good_fit = False #determines wether a fit is good
        
        fit_values, count_fit = determine_fit_values(count_fit, pars_x_axis)
       
        fit_values, usefull, count_fit = correct_fit_values(fit_values, data, count_fit, good_fit)
        
        
        
        good_fit = check_good_fit(usefull, count_fit)        
        
        #initial guessed paraneters for x-axis correction
        pars_x_axis.add_many(('a', 0.1, True), ('b', 0.1, True))                  
        pars_x_axis = fit_x_axis(fit_values, pars_x_axis) #x-axis conversion parameters (from time to mass)    
    
        ''' fitting for DBT main peak '''  
        
        DBTmain_fit_values, count_fit = determine_fit_values(count_fit, pars_x_axis) 
        DBTmain_fit_values, DBT_main_usefull, count_fit = correct_fit_values(DBTmain_fit_values, 
                                                                   data, count_fit, good_fit)
        good_fit = check_good_fit(usefull, count_fit)
        
        usefull.update(DBT_main_usefull)
        
        pars_x_axis = fit_x_axis(fit_values, pars_x_axis) #x-axis conversion parameters (from time to mass)    

        ''' fitting for the rest of DBT peaks '''
        
                                             
        if usefull[184.0347] == True:
            DBT_fit_values, count_fit = determine_fit_values(count_fit, pars_x_axis) 
            
            DBT_fit_values, DBT_usefull, count_fit = correct_fit_values(DBT_fit_values, 
                                                         data, count_fit, good_fit)        
            #sums all fit_values
            all_fit_values = {**DBTmain_fit_values, **fit_values, **DBT_fit_values}
            
            usefull.update(DBT_usefull)
        else:
            all_fit_values = fit_values
            usefull[182.0190] = False    
            usefull[183.0268] = False
            usefull[185.0380] = False
            usefull[186.0305] = False
            
        
        good_fit = check_good_fit(usefull, count_fit)
        
        #determines the x_axis conversion parametrs
        pars_x_axis = fit_x_axis(all_fit_values, pars_x_axis)

        time = list(all_fit_values.values())
        mass = list(all_fit_values.keys())
        mass_corrected = x_axis_fit_func(pars_x_axis, time)
        
        #save the maximum mass correction
        max_mass_correction[spectrum_number] = max(np.absolute(mass-mass_corrected))

        good_fit = check_good_fit(usefull, count_fit=100)
        
        pars_v = pars_x_axis.valuesdict()
        
        if good_fit == True: #Blue dots
            pars_a_good_fit.append(pars_v['a'])
            pars_b_good_fit.append(pars_v['b'])
            spectra_list_good_fit.append(spectrum_number)
        elif usefull[184.0347] == True:#red dots
            if not check_good_fit(DBT_usefull, count_fit = 100):
                pars_a_ok_fit.append(pars_v['a'])
                pars_b_ok_fit.append(pars_v['b'])
                spectra_list_ok_fit.append(spectrum_number) 
        else:    #green dots
            pars_a.append(pars_v['a'])
            pars_b.append(pars_v['b'])
            spectra_list_rough_fit.append(spectrum_number)
        
        #plots the entire spectrum and  mass-correction
        plot_to_check(time, mass, mass_corrected, pars_x_axis, data)
        
        amplitudes.clear()        
        good_fit == False
        #print_non_fitted_masses(usefull)
        spectrum_details[spectrum_number] = usefull
      
    count_fit = 100 #important for "check_good_fit()
    max_mass_correct = max(list(max_mass_correction.values()))
    
    print('max mass correction is: ', max_mass_correct)
    #print(rel_amp.items())
    for spectrum_number, usefull in spectrum_details.items():
        if not check_good_fit(usefull, count_fit):  
            print('Spectrum ', spectrum_number)
            print_non_fitted_masses(usefull)
    
    #plotting the parameters "a" and "b"
    
    fig = plt.figure()        
    axis = fig.add_subplot(2, 1, 1)
    
    #x_axis = np.arange(len(spectra_list))
    spectra_init = spectra_list[0]
    
    print('The green dots are the bad fits. The spectra with bad fits are: ', spectra_list_rough_fit)    
    
    spectra_list_good_fit[:] = [spectrum_number - spectra_init for spectrum_number in spectra_list_good_fit]
    spectra_list_ok_fit[:] = [spectrum_number - spectra_init for spectrum_number in spectra_list_ok_fit]    
    spectra_list_rough_fit[:] = [spectrum_number - spectra_init for spectrum_number in spectra_list_rough_fit]
    
    
    
    axis.set_title('a \n Blue dots are perfect fit \n Red dots lack one or more DBT minor peaks but not the DBT main peak \n Green dots are rough fit and lacks random peaks. See print!')
    axis.plot(spectra_list_good_fit, pars_a_good_fit, 'bo')
    axis.plot(spectra_list_ok_fit, pars_a_ok_fit, 'ro')
    axis.plot(spectra_list_rough_fit, pars_a, 'go')
    
    axis = fig.add_subplot(2, 1, 2)
    
    axis.set_title('b')
    axis.plot(spectra_list_good_fit, pars_b_good_fit, 'bo')
    axis.plot(spectra_list_ok_fit, pars_b_ok_fit, 'ro')
    axis.plot(spectra_list_rough_fit, pars_b, 'go')
    plt.show()
    

        
    '''This saves the new fitted curve!
    query = ('update measurements_tof set time=time, tof_p1_0=' + str(p1_x_axis[0]) +
             ', tof_p1_1=' + str(p1_x_axis[1]) + ', tof_p1_2=' + str(p1_x_axis[2]) +
             ' where id = ' + str(spectrum_number))
    if sys.argv[2] == 'yes':
        print(query)
        cursor.execute(query)'''

        
if __name__ == '__main__':
    main()
