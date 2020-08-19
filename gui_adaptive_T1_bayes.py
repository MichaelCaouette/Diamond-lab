# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 16:34:14 2020

@author: Childresslab
"""

import numpy as np
from spinmob import egg
import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error


_debug_enabled     = False
def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))
        

class GUIAdaptiveT1Bayes(egg.gui.Window):
    """
    GUI for managing the adaptive protocole for T1 measurement. Using 
    Bayesian inference to adapt the best time to probe. 
    """   
    
    def __init__(self, gui_pulser, name="Super adaptive Bayes Bad Ass", size=[1000,500]): 
        """
        Initialize
        
        gui_pulser:
            Object GuiMainPulseSequence in gui_pulser. 
            This will allow to control the pulse sequence. 
        """    
        _debug('GUIAdaptiveT1Bayes: __init__')
        _debug('Oh yes, the past can hurt. But the way I see it, you can either run from it or learn from it. – The Lion King')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Steal the pulser, mouhahaha
        self.gui_pulser = gui_pulser
        
        # Initialise the GUI
        self.initialize_GUI()
               
    def initialize_GUI(self):
        """
        Fill up the GUI
        """      
        _debug('GUIAdaptiveT1Bayes: initialize_GUI')

        # A button for preparing stuff
        self.button_run = egg.gui.Button('Start', tip='Launch the experiment')
        self.button_run.set_style('background-color: rgb(0, 200, 0);')
        self.place_object(self.button_run, row=0, column=0)
        self.connect(self.button_run.signal_clicked, self.button_run_clicked)

        # Place a buttong for saving the data
        self.button_save = self.place_object(egg.gui.Button(), row=0, column=1,
                                             alignment=1)
        self.button_save.set_text('Save :D :D :D')
        self.connect(self.button_save.signal_clicked, self.button_save_clicked)  
        
        # tree dictionnarry for the settings
        self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_adaptiveT1Bayes')
        self.place_object(self.treeDic_settings, row=1, column=0)
        self.treeDic_settings.add_parameter('Rate_+_min', 0.01, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' Hz',
                                            tip='Guess for the minimum value of the rate gamma+') 
        self.treeDic_settings.add_parameter('Rate_+_max', 150*1e3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' Hz',
                                            tip='Guess for the maximum value of the rate gamma+') 
        self.treeDic_settings.add_parameter('Size_rate_+_axis', 150, 
                                            type='int', step=10, 
                                            bounds=[0,None],
                                            tip='Number of points along the gamma+ axis for the pdf') 
        self.treeDic_settings.add_parameter('Rate_-_min', 0.01, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' Hz',
                                            tip='Guess for the minimum value of the rate gamma-')         
        self.treeDic_settings.add_parameter('Rate_-_max', 150*1e3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' Hz',
                                            tip='Guess for the maximum value of the rate gamma-')
        self.treeDic_settings.add_parameter('Size_rate_-_axis', 150, 
                                            type='int', step=10, 
                                            bounds=[0,None],
                                            tip='Number of points along the gamma- axis for the pdf') 
        self.list_prior_types = ['Flat', 'Gaussian']
        self.treeDic_settings.add_parameter('Prior_type', self.list_prior_types, 
                                            tip='Which prior to use. Based on the bounds given for the rates.')  


        self.treeDic_settings.add_parameter('PL0', 0.04, 
                                            type='float', step=0.04, 
                                            bounds=[0,None], 
                                            tip='Mean photocounts from ms=0 for a SINGLE readout') 
        self.treeDic_settings.add_parameter('Contrast', 0.1, 
                                            type='float', step=0.01, 
                                            bounds=[0,None], 
                                            tip='Contrast between the state ms=0 and ms=+-1 at time=0.\nThis is defined as (PL0-PL+-)/PL0, where PL+- is the mean photocount of ms=+-1.') 
 
        # Add the Image View for the posterior. 
        self.plot_item = egg.pyqtgraph.PlotItem()
        # Put an image in the plot item. 
        self.plot_image = egg.pyqtgraph.ImageView(view=self.plot_item)
        self.place_object(self.plot_image, row=1, column = 1, 
                          row_span=2, column_span=3, alignment=0)  
        self.set_column_stretch(1,10)
        self.set_row_stretch(1,10)
        
        # Add a dummy map 
        x = np.linspace(1, 20, 100)
        y = np.linspace(1, 20, 100)
        X,Y = np.meshgrid(x,y)


    def initiate_attributes(self):
        """
        Initiate the attribute from the parameter choosen. 
        Prepare the prior based on the parameters choosen. 
        """
        _debug('GUIAdaptiveT1Bayes: initiate_attributes') 
        
        # Set the prior
        # Extract the bounds
        self.Gp_min       = self.treeDic_settings['Rate_+_min']   #Minimum guess for gamma plus (Hz) 
        self.Gp_max       = self.treeDic_settings['Rate_+_max']  #Maximun guess for gamma plus (Hz)    
        self.size_axis_Gp = self.treeDic_settings['Size_rate_+_axis'] # Size of the axis gamam plus
        self.Gm_min       = self.treeDic_settings['Rate_-_min']   #Minimum guess for gamma minus (Hz) 
        self.Gm_max       = self.treeDic_settings['Rate_-_max']  #Maximun guess for gamma minus (Hz)  
        self.size_axis_Gm = self.treeDic_settings['Size_rate_-_axis'] # Size of the axis gamam minus
        #Define the axis for the prior pdf      
        self.gp_axis = np.linspace(self.Gp_min, self.Gp_max, self.size_axis_Gp) 
        self.gm_axis = np.linspace(self.Gm_min,self. Gm_max, self.size_axis_Gm) 
        
        # Set the prior according to the type of prior
        if self.treeDic_settings['Prior_type'] == 'Flat':
            #Define the prior 
            self.prior = 1+np.zeros([len(self.gm_axis), len(self.gp_axis)])      
            # No need to normalize it for now. 
        if self.treeDic_settings['Prior_type'] == 'Gaussian':
            # The priore will be gaussian, with the widt set by the bounds
            X,Y = np.meshgrid(self.gp_axis,self.gm_axis)
            x0 = np.mean(self.gp_axis)
            y0 = np.mean(self.gm_axis)
            dx = 0.5*(self.Gp_max-self.Gp_min) # Width in the gamma+ direction
            dy = 0.5*(self.Gm_max-self.Gm_min) # Width in the gamma- direction
            self.prior = np.exp(-( (X-x0)*(X-x0)/dx**2 + (Y-y0)*(Y-y0)/dy**2 )) # A non-skewed gaussian

        # Initiate the class for processing the protocol
        # Define the constants
        self.PL0      = self.treeDic_settings['PL0']
        self.contrast = self.treeDic_settings['Contrast']
        constants = [self.PL0, self.contrast]
        # Define the model functions that describe our experiment. 
        f0 = PLModel(constants).PL00
        fp = PLModel(constants).PLp0
        fm = PLModel(constants).PLm0
        self.model_functions = [f0, fp, fm]
            
        # Initiate the class for Bayes inference.
        self.bayes = Bayes3Measure(self.model_functions, self.prior, 
                                   self.gp_axis, self.gm_axis)

    def button_run_clicked(self):
        """
        Run the protocole !
        """
        _debug('GUIAdaptiveT1Bayes: button_run_clicked')
        
        # Make the attribute to match with the settings
        self.initiate_attributes()
        
        #TODO It is here that we gonna implement the measurement and update of
        #TODO  the best time to probe. 
        
        # Update the plot
        self.update_image()        

        
    def button_save_clicked(self):
        """
        Save everything !
        """
        _debug('GUIAdaptiveT1Bayes: button_save_clicked')
        print('Implement me !!')
        
        # Fake a measurement
        Gp_true, Gm_true = 15000, 32000
        t = self.gui_pulser.gui_T1_probeOneTime.t_probe
        nb_readout = self.gui_pulser.rep
        self.measured_f0 = np.random.poisson(nb_readout*self.model_functions[0](t, Gp_true, Gm_true))
        self.measured_fp = np.random.poisson(nb_readout*self.model_functions[1](t, Gp_true, Gm_true))
        self.measured_fm = np.random.poisson(nb_readout*self.model_functions[2](t, Gp_true, Gm_true))
        diffp = self.measured_f0 - self.measured_fp
        diffm = self.measured_f0 - self.measured_fm
        #Add the fake measure as a data
        self.bayes.add_measurement(t, nb_readout, diffp, diffm)
        # Update the plot
        self.update_image()
                
        
        
    def update_image(self):
        """
        Update the plot of the posterior. The title should be clear lol. 
        """    
        _debug('GUIAdaptiveT1Bayes: update_image')
        
 
        # Set the axis 
        # Get the scale (AKA the spacing between two neighboor points on the image)
        self.scale_x = (self.gp_axis.max()-self.gp_axis.min())/len(self.gp_axis)*1e-3
        self.scale_y = (self.gm_axis.max()-self.gm_axis.min())/len(self.gm_axis)*1e-3
        
        self.plot_item.setLabel('bottom', text='Gamma + (kHz)')
        self.plot_item.setLabel('left'  , text='Gamma - (kHz)')      
        
        # Set the image
        self.plot_image.setImage(self.bayes.get_post().T,
                                 pos=(self.gp_axis.min(), self.gm_axis.min()),
                                 scale =(self.scale_x, self.scale_y) )
        # magic method for the image to fill all the space
        self.plot_image.view.setAspectLocked(False) # Input True for having the scaling right.              
    

def integral2D(x,y, Z):
    """
    Integrate in 2 dimension Z. 
    Z is the 2D array to integrate. 
    x and y are both 1D array used to define the axis of Z
    """
    _debug('integral2D')#,
#               'x:', x,
#               'y:', y,
#               'Z:', Z)
    firstInt = np.trapz(Z, x=x, axis=1) #First integrate along the first axis
    return     np.trapz(firstInt, x=y) #Integrate over the remaining axis

class Bayes3Measure():
    """
    Bayes inference for 3 measure
    
    Take the data and update the posterior.
    
    This is how it should be used:
        
        - Initiate it with the prior and the model functions. 
        - Add measurement for updating the likelihood. This can be done many
          time. 
        - Get the posterior distribution.  
     
    """

    def __init__(self, model_functions, prior, gp_axis, gm_axis):
        """
        For this Bayes, we 
        
        model_functions = [f0, fp, fm]
        
        f0,fp,fm:
            Function with signature (t,Gp,Gm) which gonna define the PL for the 
            three type of measurement. 
            The likelihood will be computed by using the difference f0-fp and
            f0-fm.
            
        prior:
            (2 dimensionnal array) Initial probability distribution that we have 
            on the 2 rates rates gamam+ and gamma-. No need to be normalized, 
            because the normalizing constant will be set when computing the 
            posterior. The relative axis (the two rates) should match the 
            meshgrid bellow for Gp_Axis and Gm_Axis. 
            
        gp_axis: 
            1D array of the axis for gamma+
        gm_axis: 
            1D array of the axis for gamma-
            
        """
        _debug('Bayes3Measure: __init__')
        _debug('Your limitation-it’s only your imagination.')
       
        self.model_functions = model_functions        
        self.f0 = model_functions[0]
        self.fp = model_functions[1]
        self.fm = model_functions[2]

        #Define the axis over which we estimate the rates and the probability distribution
        self.gp_axis = gp_axis #1D axis for gamma+
        self.gm_axis = gm_axis #1D axis for gamma-
        self.NGp    = len(self.gp_axis)       #Number of discrete point along the gamma+ axis for the probability distributions.
        self.NGm    = len(self.gm_axis)       #Number of discrete point along the gamma- axis for the probability distributions. 
        #Meshgrid
        self.Gp_Axis, self.Gm_Axis = np.meshgrid(self.gp_axis, self.gm_axis)  
        
        #Get the prior 
        self.prior = prior #Prior distribution
        
        # Initial the log of like-lihood. With no measurement for now.
        self.L = np.zeros(np.shape(self.Gp_Axis)) #This will be related to the logatirhtm of the like-lihood. It simplify a lot the calculation and reduce the number of calculation 
             
        
    def get_post(self):
        """
        Update the posterior and return it
        Compute it from the like-lihood and the prior, than normalize it
        """
        _debug('Bayes3Measure: get_post' )
        
        return self.Ppost

    def likelihood(self, exp0, expp, expm, diffp, diffm):   
        """
        Compute the likehihood of the measured data. 
        The measured data are diffp and dippm. 
        
        In the following, R is the total number of readout performed.
        
        exp0:
            (array) Expectation for R*f0, for each element of the domain. 
        expp:
            (array) Expectation for R*fp, for each element of the domain. 
        expm:
            (array) Expectation for R*fm, for each element of the domain.   
            
        diffp: 
            (float) Measured value of the difference R*(f0-fp). That's it, the 
            measured total difference. (not averaged: the difference is taken 
            with the total numbers of counts)
        diffm: 
            (float) Measured value of the difference R*(f0-fm )  That's it, the 
            measured total difference (not averaged: the difference is taken 
            with the total numbers of counts)
        
        """
        _debug('Bayes3Measure: likelihood')
        
        # Precompute arrays for simplification
        ZZZ = expp*expm +exp0*(expp+expm)
        
        A = (exp0 + expp + expm +2*(diffp+diffm) 
            + diffp*diffp/expp + diffm*diffm/expm )
        
        B = (expp*diffm + expm*(3*expp+diffp))**2       
        C = exp0/(expp*expm*ZZZ)
        # THE like-lihood
        L = 0.5*(np.log(ZZZ) + A - B*C )
        
        return L     
    
    def add_measurement(self, t_probe, nb_readout, diff_p, diff_m):
        """
        Add a measurement for updating the likelihood.
        
        t_probe:
            (float) Time at which the measurment is done. 
        nb_readout:
            (float) Number of readout performed on each state. This will be used
            for computing the expectation. 
        diff_p:
            Measured TOTAL difference between the counts of the f0 and fp 
            measurements. Without noise, it would be expected to be equal to
            nb_readout*(f0-fp). 
        diff_m:
            Measured TOTAL difference between the counts of the f0 and fm 
            measurements. Without noise, it would be expected to be equal to
            nb_readout*(f0-fm). 
            
        """
        
        # Get the like-lihood of this measurement
        exp_0 = self.f0(t_probe, self.Gp_Axis, self.Gm_Axis)*nb_readout
        exp_p = self.fp(t_probe, self.Gp_Axis, self.Gm_Axis)*nb_readout
        exp_m = self.fm(t_probe, self.Gp_Axis, self.Gm_Axis)*nb_readout
        L_now = self.likelihood(exp_0, exp_p, exp_m, diff_p, diff_m)
        
        # Update the total likelihood. 
        self.L += L_now

        # Update the posterior from the like-lihood and the prior
        self.Ppost  = np.exp(-self.L)*self.prior
        self.Ppost /= integral2D(self.gp_axis, self.gm_axis, self.Ppost) #Normalize 
        if _debug_enabled:
            #Put this debug into an extra of, because the extra calculation of the volume might be expensive 
            _debug('Volume of posterior (its not fun)  = ', integral2D(self.gp_axis, self.gm_axis, self.Ppost ) ) 
            
        
# Let's put this class here for now        
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


    
if __name__=="__main__":
    _debug_enabled = True
    
     # Create the fpga api
    bitfile_path = ("X:\DiamondCloud\Magnetometry\Acquisition\FPGA\Magnetometry Control\FPGA Bitfiles"
                    "\Pulsepattern(bet_FPGATarget_FPGAFULLV2_WZPA4vla3fk.lvbitx")
    resource_num = "RIO0"     
    
    import fpga_control as _fc
    fpga_fake = _fc.FPGA_fake_api(bitfile_path, resource_num) # Create the api   
    fpga_fake.open_session()
    
    import gui_pulser
    gui = gui_pulser.GuiMainPulseSequence(fpga_fake)
    gui.show()
    
    self = GUIAdaptiveT1Bayes(gui)
    self.show()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    