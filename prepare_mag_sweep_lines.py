# -*- coding: utf-8 -*-
"""
Created on Thu Aug 27 13:13:42 2020

Goal:
    Define some functions for making and viewing the lines to sweep with the
    magnet. 

@author: Childresslab
"""

import numpy as np
import spinmob as _s

from mpl_toolkits.mplot3d import Axes3D # This import registers the 3D projection, but is otherwise unused.
import matplotlib.pyplot as plt

import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error

# Debug stuff.
_debug_enabled                = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))

#TODO create a general function for a plane perpendicular to a given normal direction

def tilted_plane():
    """
    Make a plabe tilted with respect to the axis. 
    It's gonna be a zigzag in the plane
    """
    xs = []
    ys = []
    zs = []

    # Define a plane tilted
    x1 = 10
    x2 = 17
    z1 = 15
    z2 = 22
    y_lines = np.linspace(14, 19, 10)
    
    for i in range(int(len(y_lines)/2)):
        
        y1 = y_lines[2*i]
        y2 = y_lines[2*i+1]
        
        xs.append(x1)
        xs.append(x2)
        ys.append(y1)
        ys.append(y2)
        zs.append(z1)
        zs.append(z2)    
        
    return xs, ys, zs


def parallel_plane():
    """
    Make a plane parallel to an axis.
    It's gonna be a zigzag in the plane.
    """
    xs = []
    ys = []
    zs = []

    # Define a plane tilted
    y1 = 14
    y2 = 16.7
    z1 = 23
    z2 = z1
    x_lines = np.linspace(14, 19, 4)
    
    for i in range(int(len(x_lines)/2)):
        x1 = x_lines[2*i]
        x2 = x_lines[2*i+1]
        
        xs.append(x1)
        xs.append(x2)
        ys.append(y1)
        ys.append(y2)
        zs.append(z1)
        zs.append(z2)    
        
    return xs, ys, zs

def rectangle_parallel_zfixed(c1, c3, Nzigzag=10, z=15):
    """
    Construct a zigzag path inside a rectangle with two opposite corner c1 and c2.
    z is fixed for this path. 
    
    
    c1:
        List of two number [x,y] for a corner of the rectangle. 
    c3:
        List of two number [x,y] for the opposite corner of the rectangle. 
        (opposite to c3)    
    Nzigzag:
        Number of zizag (back and forth) to make in the rectangle.
    z:
        (float) Value of the z position
    """
    xs = []
    ys = []
    zs = []

    xmin = c1[0]
    xmax = c3[0]
    ymin = c1[1]
    ymax = c3[1]
    
    # Make sure that the number of zigzag is even
    if Nzigzag %2 == 1:
        print('Warning: in rectangle_parallel_zfixed, Nzigzag is incremented to make it even')
        Nzigzag +=1
    
    
    # If the zigzags are going toward x
    y1 = ymin
    y2 = ymax
    
    x_lines = np.linspace(xmin, xmax, Nzigzag)
    
    for i in range(int(len(x_lines)/2)):
        x1 = x_lines[2*i]
        x2 = x_lines[2*i+1]
        
        xs.append(x1)
        xs.append(x2)
        ys.append(y1)
        ys.append(y2)
        zs.append(z)
        zs.append(z)    
        
    return xs, ys, zs

def parallelogram(c1, c2, c3):
    """
    Construct a path inside a parallelogram with three corner c1, c2 and c3. 
    The fourth corner c4 is determined by being opposite to c1. 
    
    
    c1, c2, c3:
        Each ci is a list of two number [x,y] for defining a corner.
        
    """
    _debug('parallelogram')
    
    # Please implement this awesome function
    

def plot_magSweepLinesSettings(databox, title='Patate Chaude'):
    """
    Plot the lines that we aim to sweep. 
    """
    
    xs = databox['xs']
    ys = databox['ys']
    zs = databox['zs']   

    # Initialize the figure and axis
    fig = plt.figure(tight_layout=True)
    ax  = fig.add_subplot(111, projection='3d') 

    ax.plot(xs, ys, zs, label='Goal') 
    ax.scatter(xs[1:-1], ys[1:-1], zs[1:-1]) 
    ax.scatter(xs[0], ys[0], zs[0]   , color='red',label='Start')
    ax.scatter(xs[-1], ys[-1], zs[-1], color='y'  ,label='End')
    plt.legend()
    ax.set_xlabel('x (mm)')
    ax.set_ylabel('y (mm)')
    ax.set_zlabel('z (mm)')
    # Set equal aspect
    # For this we need the extermum of all the pts
    allpts = np.concatenate((xs, ys, zs))
    maximum = np.max(allpts)
    minimum = np.min(allpts)
    ax.set_xlim3d(minimum, maximum)
    ax.set_ylim3d(minimum, maximum)
    ax.set_zlim3d(minimum, maximum)
    # Slice the title if it's too long (for example, by including the whol path)
    if len(title)>20:
        t1 = title[:int(len(title)/2)]
        t2 = title[int(len(title)/2):]
        title = t1+'\n'+t2
        
    ax.set_title(title, fontsize=10) 



#By default set the object
if __name__ == '__main__':
    _debug_enabled = True    

    # Uncomment the type of sweep that you want to create
#    xs, ys, zs = tilted_plane()
#    xs, ys, zs = parallel_plane()
    xs, ys, zs = rectangle_parallel_zfixed(c1 = [20, 13],
                                           c3 = [25, 18],
                                           Nzigzag=23, z=8)
    
    # Save the data into a databox
    databox = _s.data.databox()
    # Put some header
    databox.insert_header('name', 'Hakuna matata')
    # Add each column
    databox['xs'] = xs
    databox['ys'] = ys
    databox['zs'] = zs  
    # Save it
    databox.save_file()

    plot_magSweepLinesSettings(databox, 'My path')
















