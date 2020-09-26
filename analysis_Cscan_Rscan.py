#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  2 10:43:46 2017

Plots a confocal scan with the 

@author: adrian
"""

import numpy as np
import scipy as sp
import spinmob as sm
import matplotlib.pyplot as plt
import matplotlib as mpl

# First import the reflection data
Rdata = sm.data.load(text='Import the reflection scan')

# Next convert the N columns of data with 
# M entries per column into an MxN 2D np array
Refl = np.zeros((len(Rdata.ckeys), len(Rdata[0])) )
for i in range(len(Rdata.ckeys)):
    Refl[i,:] = Rdata[i]/1000 # Get in kcounts/sec
    


setMaxkCountPlot = True #If true, set the maximum kilocount in the plot. 
MaxKCountPlot = 180    #Maximum KiloCount to show in the plot




## Hardcoded scale parameters (obtained by scanning a resolution target)
#convx = 5.2 #um/V # For setup 2
#convy = 4.9 #um/V # For setup 2

# Hardcoded scale parameters (obtained by scanning a resolution target)
convx = 9.24 #um/V # For setup 1
convy = 6.30 #um/V # For setup 1


# Get reflection location parameters from header names
Rxmin = Rdata.headers['Vx_min']
Rxmax = Rdata.headers['Vx_max']
Rxpts = Rdata.headers['Nx']
Rymin = Rdata.headers['Vy_min']
Rymax = Rdata.headers['Vy_max']
Rypts = Rdata.headers['Ny']


Rxum = (Rxmax - Rxmin) * convx;
Ryum = (Rymax - Rymin) * convy;

Rx = np.linspace(Rxmin,Rxmax,Rxpts)
Ry = np.linspace(Rymin,Rymax,Rypts)

# Get locations
Rxloc = Rx * convx;
Ryloc = Ry * convy;

# Find optimal contour lines by getting difference between BG and Refl.max()
N, Counts = sp.histogram(Refl.flatten(),30)
ReflBG = Counts[N.argmax()]
ReflSig = Refl.max() - ReflBG

# Set contour lines as 40, 50, and 60% of the reflection signal above the BG
RContLvls = np.array([0.2])*ReflSig + ReflBG

# Then import the scan data
Cdata = sm.data.load(text='Import the confocal scan')

# Next convert the N columns of data with 
# M entries per column into an MxN 2D np array
PL = np.zeros((len(Cdata.ckeys), len(Cdata[0])))
for i in range(len(Cdata.ckeys)):
    PL[i,:] = Cdata[i]/1000 # Get in kcounts/sec


# Get confocal location parameters from header names
Cxmin = Cdata.headers['Vx_min']
Cxmax = Cdata.headers['Vx_max']
Cxpts = Cdata.headers['Nx']
Cymin = Cdata.headers['Vy_min']
Cymax = Cdata.headers['Vy_max']
Cypts = Cdata.headers['Ny']

Cxum = (Cxmax - Cxmin) * convx;
Cyum = (Cymax - Cymin) * convy;

Cx = np.linspace(Cxmin,Cxmax,Cxpts)
Cy = np.linspace(Cymin,Cymax,Cypts)

# Get locations
Cxloc = Cx * convx;
Cyloc = Cy * convy;

# Get optimal legend scale bar (closests length to 1/5 of x extent)
lengths = np.array([1, 2, 5, 10, 20])
optl = Cxum/5
chi = (optl - lengths)**2.0
barlen = lengths[chi==chi.min()]


###Show the Reflection map
plt.figure()
plt.pcolor(Cxloc, Cyloc,Refl,cmap='magma')
plt.title("Reflection Map")




# Format image nicely with colorbar and true aspect ratio
fig,ax = plt.subplots(figsize = (5,5), dpi=100)
if setMaxkCountPlot:
    pc = ax.pcolor(Cxloc,Cyloc,PL,cmap='magma',vmax=MaxKCountPlot)#vmax=150)
else:
    pc = ax.pcolor(Cxloc,Cyloc,PL,cmap='magma',)
#pc.set_clim(0,100)
cb = fig.colorbar(pc)
cb.ax.set_ylabel('PL (kcounts/sec)',fontsize=11)
ax.set_xticks([])
ax.set_yticks([])
ax.axis('image')

# Add contour lines for device
ax.contour(Rxloc,Ryloc, Refl, RContLvls, colors='w')

# Add optimal length scale bar
ax.add_patch(mpl.patches.Rectangle((Cxloc[0]+0.5*optl,Cyloc[0]+0.5*optl),
                                   barlen,barlen*.15,
                                   facecolor='white',edgecolor='white',
                                   linewidth=0))
ax.text((optl+barlen)*.5+Cxloc[0],0.5*optl+barlen*.2+Cyloc[0],
        str(int(barlen))+r'$\mathrm{\mu m}$',
        horizontalalignment='center',color='white')

# Add pathname as title
ax.set_title(Cdata.path[Cdata.path.rfind('/Data')+1:],fontsize=7)

# Uncomment to save
#plt.savefig(Cdata.path+'.png',dpi=200)
#plt.savefig(data.path+'.pdf',dpi=200)