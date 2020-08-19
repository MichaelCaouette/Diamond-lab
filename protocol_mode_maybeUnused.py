# -*- coding: utf-8 -*-
"""
Created on Sat Jun 13 11:46:18 2020

Goal: Define the different type of initialization and readout of the PL

@author: Michael
"""

import numpy as np


class PLModel():
    """
    Define the model for the Photoluminescences for each of the 9 types of 
    measurement.  
    """
    def __init__(self, constants):
        """
        
        constants = [PL0, contrast]
        PL0:
            Mean photocounts from the ms=0 state. 
        contrast:
            Contrast in photoluminescence from the ms=+-1 state. This is 
            defined such that the photoluminescence coming from ms=+-1 is 
            PL0*(1-contrast)
        """
        self.PL0 = constants[0]       
        self.contrast   = constants[1]
        
        # Define some dimensionless number appearing over and over in the model. 
        self.A = self.PL0-self.contrast*self.PL0*2/3 
        self.B = self.contrast*self.PL0/6 
        
    def PL00(self, t, Gp, Gm):
        """
        Photoluminescence of initializing in ms=0, reading ms=0
        t:
            Time to probe
        Gp:
            Rate gamma+
        Gm: 
            Rate gamma-
        Units must be such that t*Gp or t*Gm is unitless. 
        """
        G0 = np.sqrt(Gp*Gp + Gm*Gm - Gp*Gm)
        betap = Gm + Gp + G0
        betam = Gm + Gp - G0
        
        coefp = (2*G0 + Gm + Gp)/G0
        coefm = (2*G0 - Gm - Gp)/G0
        
        return self.A + self.B*(  coefm*np.exp(-t*betam) 
                                + coefp*np.exp(-t*betap) )

    def PLp0(self, t, Gp, Gm):
        """
        Photoluminescence of initializing in ms=p, reading ms=0
        t:
            Time to probe
        Gp:
            Rate gamma+
        Gm: 
            Rate gamma-
        Units must be such that t*Gp or t*Gm is unitless. 
        """
        G0 = np.sqrt(Gp*Gp + Gm*Gm - Gp*Gm)
        betap = Gm + Gp + G0
        betam = Gm + Gp - G0
        
        coefp = -(G0 - Gm + 2*Gp)/G0
        coefm = -(G0 + Gm - 2*Gp)/G0
        
        return self.A + self.B*(  coefm*np.exp(-t*betam) 
                                + coefp*np.exp(-t*betap) )

    def PLm0(self, t, Gp, Gm):
        """
        Photoluminescence of initializing in ms=m, reading ms=0
        t:
            Time to probe
        Gp:
            Rate gamma+
        Gm: 
            Rate gamma-
        Units must be such that t*Gp or t*Gm is unitless. 
        """
        G0 = np.sqrt(Gp*Gp + Gm*Gm - Gp*Gm)
        betap = Gm + Gp + G0
        betam = Gm + Gp - G0
        
        coefp = -(G0 + 2*Gm - Gp)/G0
        coefm = -(G0 - 2*Gm + Gp)/G0
        
        return self.A + self.B*(  coefm*np.exp(-t*betam) 
                                + coefp*np.exp(-t*betap) )

    def PL0p(self, t, Gp, Gm):
        """
        Photoluminescence of initializing in ms=0, reading ms=+
        t:
            Time to probe
        Gp:
            Rate gamma+
        Gm: 
            Rate gamma-
        Units must be such that t*Gp or t*Gm is unitless. 
        """
        G0 = np.sqrt(Gp*Gp + Gm*Gm - Gp*Gm)
        betap = Gm + Gp + G0
        betam = Gm + Gp - G0
        
        coefp = -(G0 - Gm + 2*Gp)/G0
        coefm = -(G0 + Gm - 2*Gp)/G0
        
        return self.A + self.B*(  coefm*np.exp(-t*betam) 
                                + coefp*np.exp(-t*betap) )

    def PLpp(self, t, Gp, Gm):
        """
        Photoluminescence of initializing in ms=+, reading ms=+
        t:
            Time to probe
        Gp:
            Rate gamma+
        Gm: 
            Rate gamma-
        Units must be such that t*Gp or t*Gm is unitless. 
        """
        G0 = np.sqrt(Gp*Gp + Gm*Gm - Gp*Gm)
        betap = Gm + Gp + G0
        betam = Gm + Gp - G0
        
        coefp = (2*G0 - 2*Gm + Gp)/G0
        coefm = (2*G0 + 2*Gm - Gp)/G0
        
        return self.A + self.B*(  coefm*np.exp(-t*betam) 
                                + coefp*np.exp(-t*betap) )

    def PLmp(self, t, Gp, Gm):
        """
        Photoluminescence of initializing in ms=-, reading ms=+
        t:
            Time to probe
        Gp:
            Rate gamma+
        Gm: 
            Rate gamma-
        Units must be such that t*Gp or t*Gm is unitless. 
        """
        G0 = np.sqrt(Gp*Gp + Gm*Gm - Gp*Gm)
        betap = Gm + Gp + G0
        betam = Gm + Gp - G0
        
        coefp = +(-G0 + Gm + Gp)/G0
        coefm = -(+G0 + Gm + Gp)/G0
        
        return self.A + self.B*(  coefm*np.exp(-t*betam) 
                                + coefp*np.exp(-t*betap) )

    def PL0m(self, t, Gp, Gm):
        """
        Photoluminescence of initializing in ms=0, reading ms=-
        t:
            Time to probe
        Gp:
            Rate gamma+
        Gm: 
            Rate gamma-
        Units must be such that t*Gp or t*Gm is unitless. 
        """
        G0 = np.sqrt(Gp*Gp + Gm*Gm - Gp*Gm)
        betap = Gm + Gp + G0
        betam = Gm + Gp - G0
        
        coefp = -(G0 + 2*Gm - Gp)/G0
        coefm = -(G0 - 2*Gm + Gp)/G0
        
        return self.A + self.B*(  coefm*np.exp(-t*betam) 
                                + coefp*np.exp(-t*betap) )

    def PLpm(self, t, Gp, Gm):
        """
        Photoluminescence of initializing in ms=+, reading ms=-
        t:
            Time to probe
        Gp:
            Rate gamma+
        Gm: 
            Rate gamma-
        Units must be such that t*Gp or t*Gm is unitless. 
        """
        G0 = np.sqrt(Gp*Gp + Gm*Gm - Gp*Gm)
        betap = Gm + Gp + G0
        betam = Gm + Gp - G0
        
        coefp = +(-G0 + Gm + Gp)/G0
        coefm = -(+G0 + Gm + Gp)/G0
        
        return self.A + self.B*(  coefm*np.exp(-t*betam) 
                                + coefp*np.exp(-t*betap) )

    def PLmm(self, t, Gp, Gm):
        """
        Photoluminescence of initializing in ms=-, reading ms=-
        t:
            Time to probe
        Gp:
            Rate gamma+
        Gm: 
            Rate gamma-
        Units must be such that t*Gp or t*Gm is unitless. 
        """
        G0 = np.sqrt(Gp*Gp + Gm*Gm - Gp*Gm)
        betap = Gm + Gp + G0
        betam = Gm + Gp - G0
        
        coefp = (2*G0 + Gm - 2*Gp)/G0
        coefm = (2*G0 - Gm + 2*Gp)/G0
        
        return self.A + self.B*(  coefm*np.exp(-t*betam) 
                                + coefp*np.exp(-t*betap) )



if __name__ == '__main__':
    import matplotlib.pyplot as plt


    Gp = 10e3
    Gm = 23e3
    t = np.linspace(0, 5/Gp, 200)
    m = PLModel(PL0=0.04, contrast=0.3)
    
    plt.figure(tight_layout=True)
    plt.plot(t, m.PL00(t, Gp, Gm), label='PL00')
    plt.plot(t, m.PL0p(t, Gp, Gm), label='PL0p')
    plt.plot(t, m.PL0m(t, Gp, Gm), label='PL0m')
    plt.legend()
    
    plt.figure(tight_layout=True)
    plt.plot(t, m.PLp0(t, Gp, Gm), label='PLp0')
    plt.plot(t, m.PLpp(t, Gp, Gm), label='PLpp')
    plt.plot(t, m.PLpm(t, Gp, Gm), label='PLpm')
    plt.legend()
    
    plt.figure(tight_layout=True)
    plt.plot(t, m.PLm0(t, Gp, Gm), label='PLm0')
    plt.plot(t, m.PLmp(t, Gp, Gm), label='PLmp')
    plt.plot(t, m.PLmm(t, Gp, Gm), label='PLmm')
    plt.legend()
    
    
    plt.figure(tight_layout=True)
    plt.plot(t, m.PL00(t, Gp, Gm), label='PL00')
    plt.plot(t, m.PL0p(t, Gp, Gm), label='PL0p')
    plt.plot(t, m.PL0m(t, Gp, Gm), label='PL0m')
    plt.plot(t, m.PLpp(t, Gp, Gm), label='PLpp')
    plt.plot(t, m.PLpm(t, Gp, Gm), label='PLpm')
    plt.plot(t, m.PLmm(t, Gp, Gm), label='PLmm')
    plt.legend()
    plt.title(   '$\Gamma_+$ = %.3f kHz'%(Gp*1e-3)
              +'\n$\Gamma_-$ = %.3f kHz'%(Gm*1e-3))




        
        