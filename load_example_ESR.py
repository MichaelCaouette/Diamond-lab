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



    
ts = d[0]*1e3
counts0 = d[1]
counts1 = d[2]
counts2 = d[3]



# Delay before laser turns on, ns
t_in = float(input("Give delay before laser turns on, (ns):\t"))
dt_readout = float(input("You want the contrasts for which readout duration (ns)?:\t"))

t_end = t_in + dt_readout

# Get the index on which we gonna sum up the counts
index = (ts>t_in)*(ts<t_end)

# Get the total counts from each states withing the readout duration
PC0 = np.sum(counts0[index])
PC1 = np.sum(counts1[index])
PC2 = np.sum(counts2[index])

# Compute the contrast
c1 = (PC0-PC1)/PC0
c2 = (PC0-PC2)/PC0

print('c1 = %f percent'%(c1*100) )
print('c2 = %f percent'%(c2*100) )


plt.figure()
plt.plot(ts, counts0)
plt.plot(ts, counts1)
plt.plot(ts, counts2)

plt.ylabel('Total counts')
plt.xlabel('Time after laser turned on (ns)')

plt.title(d.path, fontsize=8)

