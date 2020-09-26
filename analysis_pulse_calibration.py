# -*- coding: utf-8 -*-
"""
Created on Mon Dec 12 11:12:16 2016

Check the contrast between two spin state initialization. 

@author: Adrian Solyom modified by Michael
"""

import spinmob as sm
import numpy as np
import matplotlib.pyplot as plt



# Open data file
d = sm.data.load(text="Load spin contrast data :3",
                 filters="*.dat")
# Check the ckeys
print(d.ckeys)
print(d.headers)

# Set the followings to tru for showing vertical liones for the time
show_laser_raise_fall = False
show_RF1_raise_fall   = True
show_RF2_raise_fall   = True
    
rep     = d.headers['repetition']
nb_iter = d.headers['iteration']
    
ts = d[0]
counts = d[1]/rep/nb_iter # This will be the count per readout

plt.figure()
plt.plot(ts, counts)

if show_laser_raise_fall:
    cmax = np.max(counts)
    ton  = d.headers['t_laser_raise']
    toff = d.headers['t_laser_fall']
    plt.plot([ton, ton]  , [0, cmax], label='Laser ON')
    plt.plot([toff, toff], [0, cmax], label='Laser OFF')
if show_RF1_raise_fall:
    cmax = np.max(counts)
    ton  = d.headers['t_RF1_raise']
    toff = d.headers['t_RF1_fall']
    plt.plot([ton, ton]  , [0, cmax], label='RF1 ON')
    plt.plot([toff, toff], [0, cmax], label='RF1 OFF')
if show_RF2_raise_fall:
    cmax = np.max(counts)
    ton  = d.headers['t_RF2_raise']
    toff = d.headers['t_RF2_fall']
    plt.plot([ton, ton]  , [0, cmax], label='RF2 ON')
    plt.plot([toff, toff], [0, cmax], label='RF2 OFF') 
       
plt.legend()
plt.ylabel('Count per readout')
plt.xlabel('Time after laser turned on (us)')
f = d.headers['Frequency']
p = d.headers['Power']
title = d.path+'\nPower %d dBm Freq %.4f GHz'%(p,f)
plt.title(title, fontsize=10)

