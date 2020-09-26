# -*- coding: utf-8 -*-
"""
Created on Wed Jul  8 09:23:02 2020

Example of how to load a scan and extract information.

@author: Childresslab
"""

import spinmob as sm
import numpy as np
import matplotlib.pyplot as plt 

d = sm.data.load(text='Select Scan')


# Each column of d is a columns of the scan




# Hardcoded scale parameters (obtained by scanning a resolution target)
convx = 9.24 #um/V
convy = 6.30 #um/V

xmin = d.headers['Vx_min']
xmax = d.headers['Vx_max']
Nx = d.headers['Nx']
ymin = d.headers['Vy_min']
ymax = d.headers['Vy_max']
Ny = d.headers['Ny']

xs = np.linspace(xmin, xmax, Nx)*convx
ys = np.linspace(ymin, ymax, Ny)*convy

# We can look at the image by doing this:
fig = plt.figure()
ax = fig.add_subplot(111)
ax.pcolor(xs, ys,d)
ax.set_xlabel('x (um)')
ax.set_ylabel('y (um)')
ax.set_aspect('equal')
plt.title(d.path, fontsize=9)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    