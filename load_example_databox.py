# -*- coding: utf-8 -*-
"""
Created on Wed Jul  8 07:57:17 2020

Example of how to load the saturation curve

@author: Childresslab
"""



import spinmob as sm
import numpy as np


d = sm.data.load(text='Select saturation curve ;)')

# Check the ckeys
print(d.ckeys)

# Get the axis names
label_s = []
for key in d.ckeys:
    label_s.append(key)

# Plot them
import matplotlib.pyplot as plt

plt.figure(tight_layout=True)


for i in range(len(d)-1):
    y = d[i+1]
    t = d[0]
    ey = np.sqrt(y)
    plt.errorbar(t,y,yerr=ey,label=label_s[i+1])
#    plt.plot(t, y, label=label_s[i+1])

plt.legend()    
plt.xlabel(label_s[0])
plt.title(d.path, fontsize=9)
