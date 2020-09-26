# -*- coding: utf-8 -*-
"""
Created on Wed Jul  8 07:57:17 2020

Example of how to load the saturation curve

@author: Childresslab
"""



import spinmob as sm
import numpy as np


d = sm.data.load(text='Select Rabi data')

# Check the ckeys
print(d.ckeys)

# Get the axis names
label_s = []
for key in d.ckeys:
    label_s.append(key)
    
#Check the name of the headers
print(d.headers)    
    


# Plot them
import matplotlib.pyplot as plt

plt.figure(tight_layout=True)


for i in range(len(d)-1):
    
    t = d[0] # Time
    y = d[i+1] # Count
    ey = np.sqrt(y) # Error in the counts
    # Get the count rate
    dt = d.headers['dt_readout'] # count time in us
    rep = d.headers['repetition']
    nb_iter = d.headers['iteration']    
    count_rare  =  y*1e6/(dt*rep*nb_iter)
    ecount_rare = ey*1e6/(dt*rep*nb_iter)
    plt.errorbar(t,1e-3*count_rare,yerr=1e-3*ecount_rare,label=label_s[i+1])

plt.legend()    
plt.xlabel(label_s[0])
plt.ylabel('KCount/sec')

f = d.headers['Frequency']
p = d.headers['Power']
title = d.path+'\nPower %d dBm Freq %.4f GHz'%(p,f)
plt.title(title, fontsize=9)











