# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 20:44:08 2019

@author: Adrian and slighly modified by Michael. 
"""

import spinmob as sm
import matplotlib.pyplot as plt
import numpy as np

### Import databox (w/ or w/o BG)

ds = sm.data.load_multiple(text="Open Saturation curve (and / or Backgrounds)")

# Determine if dataset are PL(s) paired with BG(s)
PL = False
BG = False
paired = False
for d in ds:
    if 'BG' in d.path:
        BG = True
    else: PL = True
if PL and BG: paired = True

if paired: idcs = np.arange(len(ds))[1::2]
else: idcs = np.arange(len(ds))

## Set up fit 
if paired:
    fitNV = sm.data.fitter().set_functions('PL0*x/(I0 + x)','PL0=1e6, I0=1')
    fitBG = sm.data.fitter().set_functions('C*x', 'C=1e3')
else:
    fitPL = sm.data.fitter().set_functions('C*x + PL0*x/(I0 + x)',
                                            'PL0=1e6, I0=0.5, C=5e4')

# Loop over data(sets)
col = 0
for i in idcs:
    if paired:
        if 'BG' in ds[i].path: BG, PL = ds[i], ds[i-1]
        else: BG, PL = ds[i-1], ds[i]
        
        # Check the keys if they changed
        print('BG keys: ', BG.ckeys)
        print('PL keys: ', PL.ckeys)
        
        photodiode_BG = BG['AI_reading']
        dt_BG = BG.h('Count_time') # Should be in ms
        counts_BG = BG['Counts']/dt_BG  # This will be Kcount/sec    
        photodiode_PL = PL['AI_reading']
        dt_PL    = PL.h('Count_time') # Should be in ms
        counts_PL = PL['Counts']/dt_PL # This will be Kcount/sec  
        
        fitBG.set_data(photodiode_BG, counts_BG).fit()
#        C = fitBG.results[0][0] # This is the old way
        C = fitBG.get_fit_results()['C']
        NV = counts_PL - C*photodiode_PL
        fitNV.set_data(photodiode_PL, NV).fit().autoscale_eydata().fit()
#        PL0, I0 = fitNV.results[0]
        PL0 = fitNV.get_fit_results()['PL0']
        I0 = fitNV.get_fit_results()['I0']
        PL0e = fitNV.get_fit_standard_errors()[0]
        I0e = fitNV.get_fit_standard_errors()[1]
        
        #Also show the max and the ratio
        #Plot Nice stuffs
        AOM = PL['AO_voltage']
        PDiode = photodiode_PL
        Pcounts = counts_PL
        index = np.argmax(PDiode)
        xmax = AOM[index]
        ymax = PDiode[index]
        PcountsMax = Pcounts[index]-C*PDiode[index]
        
        plt.figure()
        plt.plot(PDiode, Pcounts, label='NV')
        #Show BackGround
        plt.plot(photodiode_BG, counts_BG,'+',color='C'+str(col), label = 'BackGround')
        plt.plot(photodiode_BG, C*photodiode_BG,'-.',color='k', lw=2)
        #Show Data minus BackGround
        labelForFit = 'Fit gives:\nI0 = %.3f +- %.3f V \nPL0 = %.0f +- %.0f counts'%(I0,I0e, PL0,PL0e)
        plt.plot(ymax,PcountsMax, 'ro',markersize=10, label='Imax = %.2f V\nImax/I0 = %.2f'%(ymax,ymax/I0))
        plt.plot(photodiode_PL,counts_PL-C*photodiode_PL,'.',color='C', label='NV-fitBackGround')
        plt.plot(photodiode_PL,PL0*photodiode_PL/(I0+photodiode_PL),'-',color='k', label=labelForFit)
        
        plt.legend(loc='best')
        plt.xlabel('Photodiode Voltage')
        plt.ylabel('KiloCounts/sec')
        plt.title(d.path+'\nFit: PL0*x/(I0 + x) with the C*x fit on BackGround removed', fontsize=9)


    else:
        PL = ds[i]
        
        photodiode_PL = PL['AI_reading']
        dt_PL    = PL.h('Count_time') # Should be in ms
        counts_PL = PL['Counts']/dt_PL # This will be Kcount/sec            
        
        fitPL.set_data(photodiode_PL, counts_PL).fit()
            
#        # The following lines will need to be adjusted to the new fitter 
#        # See how it is done in the other if condition above 
#        PL0, I0, C = fitPL.results[0]
#        PL0e, I0e, Ce = np.sqrt(fitPL.results[1].diagonal())
        
        # This should work with the new fitter 
        PL0 = fitPL.get_fit_results()['PL0']
        I0 = fitPL.get_fit_results()['I0']
        C = fitPL.get_fit_results()['C']
        PL0e = fitPL.get_fit_standard_errors()[0]
        I0e = fitPL.get_fit_standard_errors()[1]    
        Ce = fitPL.get_fit_standard_errors()[2]   
        

        #Plot Nice stuffs
        AOM = PL['AO_voltage']
        PDiode = photodiode_PL
        Pcounts = counts_PL
        index = np.argmax(PDiode)
        xmax = AOM[index]
        ymax = PDiode[index]
        PcountsMax = Pcounts[index]
        
        #Plot the saturation curve to compare the maximum intensity with the theoretical maximum one. 
        plt.figure()
        plt.plot(PDiode, Pcounts)
        labelForFit = 'Fit gives:\nI0 = %.3f +- %.3f V \nPL0 = %.0f +- %.0f counts'%(I0,I0e, PL0,PL0e)
        plt.plot(PDiode,C*PDiode+PL0*PDiode/(I0+PDiode),'--',color='k', label=labelForFit)
        plt.plot(ymax,PcountsMax, 'ro',markersize=10, label='Imax = %.2f V\nImax/I0 = %.2f'%(ymax,ymax/I0))
        plt.legend(loc='best')
        plt.xlabel('Photodiode Voltage')
        plt.ylabel('KiloCounts/sec')
        plt.title(d.path+'\nFit:C*x + PL0*x/(I0 + x)', fontsize=7)
        



        
    # Increment plotting colour
    col += 1
    col = col % 10
    
#Plot Nice stuffs
AOM = PL['AO_voltage']
PDiode =  PL['AI_reading']
Pcounts = PL['Counts']/dt_PL # This will be Kcount/sec    
index = np.argmax(PDiode)
xmax = AOM[index]
ymax = PDiode[index]
PcountsMax = Pcounts[index]

#Plot the AOM voltage versus PhotoDiode Voltage, in order to see what valu gives the max. 
plt.figure()
plt.plot(AOM,PDiode)
plt.plot(xmax,ymax, 'ro',markersize=10, label='xmax = %.2f V\nymax = %.2f V'%(xmax,ymax))
plt.legend(loc='best')
plt.xlabel('AOM Voltage')
plt.ylabel('Photodiode Voltage')
plt.title(d.path, fontsize=7)









