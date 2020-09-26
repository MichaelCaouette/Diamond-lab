# -*- coding: utf-8 -*-
"""
Loads a Rabi pulse sequence and fit a parabola on the first dip to estimate the pi pulse time. 


Created on Mon Jun 17 10:38:46 2019

@author: AdrianS
"""

import spinmob as sm
import numpy as np
import matplotlib.pyplot as plt

# Load data and header file
d = sm.data.load(text="Load Rabi maaaan !",
                 filters="*.dat")


   
t   = d[0]
PL  = d[1]
PLe = np.sqrt(PL)
    
    
### Plot the data
plt.figure()
plt.errorbar(t, PL, PLe, fmt='o')
plt.plot(t, PL, 'k--')    


##User click at the left and at the right of the interval he wants the parabola to be fitted. 
pts = plt.ginput(2,timeout=0)
tmin = pts[0][0]
tmax = pts[1][0]
index = (t>tmin)*(t<tmax)
xForFit = t[index]
yForFit = PL[index]
yeForFit = PLe[index]

#Check if the region is the one we want. 
plt.plot(xForFit,yForFit)
    
    
### Define the fitter and fit function
fitter = sm.data.fitter()
fitter.set_functions('A*(x-x0)**2+B','A,x0,B')

### Get guesses
minimum_index = np.argmin(yForFit)
x0_guess = xForFit[minimum_index]
B_guess = yForFit[minimum_index]
A_guess = (yForFit[0]-B_guess)/(xForFit[0]-x0_guess)**2 #This is just solving A for the first point. 
fitter.set(A=A_guess, B=B_guess, x0=x0_guess)

#Set the data and fit
fitter.set_data(xForFit, yForFit, yeForFit)
fitter.fit()


### Get fit results

# previous fitter
#A, x0, B = fitter.results[0]
#A_e, x0_e, B_e = fitter.results[1].diagonal()**0.5
#
## New
#A = fitter.results.params['A'].value
#x0 = fitter.results.params['x0'].value 
#B = fitter.results.params['B'].value 
#A_e = fitter.results.params['A'].stderr 
#x0_e =fitter.results.params['x0'].stderr 
#B_e =fitter.results.params['B'].stderr 

# New new
A, x0, B = fitter.get_fit_values()
A_e, x0_e, B_e = fitter.get_fit_standard_errors()


#Compute cool stuff
maxPL = np.max(PL)
minPL = np.min(PL)
contrast = (maxPL-minPL)/maxPL

###Plot the fit and the original data
y = A*(xForFit-x0)**2+B
plt.figure()
plt.errorbar(t, PL/1000, PLe/1000, fmt='o')
label =( 'Parabola fit\nMinimum occurs at %.3f +- %.3f us'%(x0,x0_e)
       +'\nPi/min = %.2f MHz'%(3.14159/x0)
       +'\nContrast = (Max-Min)/Max = %.2f percent'%(contrast*100))
plt.plot(xForFit, y/1000, 'r-', linewidth=3.0, label=label) 
plt.xlabel('Time for the microwave pulse (us)')
plt.ylabel('Total Counts (Kcounts)')
plt.legend(loc='best')
plt.title(d.path, fontsize=8)




















