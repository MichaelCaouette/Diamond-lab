# -*- coding: utf-8 -*-
"""
Created on Thu May 21 15:27:02 2020

A GUI for playing with the FPGA

@author: Childresslab, Michael
"""

import numpy as np
from spinmob import egg
import spinmob as sm
import time

from gui_map_2D import map2D

import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error


# Debug stuff.
_debug_enabled     = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))
        

 
class GUIPiPulseOptimization(egg.gui.Window):
    """
    GUI for optimizing the pi pulse. 
    """
    
    def __init__(self, gui_pulser, name="Optimer of pipulse", size=[1000,500]): 
        """
        Initialize
        
        gui_pulser:
            Object GuiMainPulseSequence in gui_pulser. 
            This will allow to control the pulse sequence. 
        """    
        _debug('GUIPiPulseOptimization:__init__')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Initialise the GUI
        self.initialize_GUI()
        
        # Get the attribute
        self.gui_pulser = gui_pulser # Steal the pulser for controlling it :)
        self.is_running = False # This will keep track of if the protocole is running or not. 
        
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIPiPulseOptimization: initialize_GUI')
        _debug('Forget your excuses. You either want it bad or don’t want it at all. – Unknown')
        
        # A button for preparing stuff
        self.button_run = egg.gui.Button('Start', tip='Launch the experiment')
        self.button_run.set_style('background-color: rgb(0, 200, 0);')
        self.place_object(self.button_run, row=0, column=0)
        self.connect(self.button_run.signal_clicked, 
                     self.button_run_clicked)

        # Place a buttong for saving the data
        self.button_save = self.place_object(egg.gui.Button(), row=0, column=1,
                                             alignment=1)
        self.button_save.set_text('Save :D :D :D')
        self.connect(self.button_save.signal_clicked, self.button_save_clicked)  
            
        # tree dictionnarry for the settings
        self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_pipulse_optimizer')
        self.place_object(self.treeDic_settings, row=1, column=0, column_span=2)

        # Note that all the other parameter are set in the pulse sequence ;)
        self.treeDic_settings.add_parameter('f_min', 2.5, 
                                            type='float', step=0.1, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Minimum frequency to sweep')
        self.treeDic_settings.add_parameter('f_max', 3.1, 
                                            type='float', step=0.1, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Maximum frequency to sweep')        
        self.treeDic_settings.add_parameter('N_f', 200, 
                                            type='int', step=10, 
                                            bounds=[0,None],
                                            tip='Number of frequency to sweep')               
        # A map for the incoming data
        self.map =  map2D()
        self.place_object(self.map, column=3, column_span=6,
                          row=1,row_span=5,alignment=0)      

    def button_run_clicked(self):
        """
        Start or stop the experiment
        """
        _debug('GUIPiPulseOptimization: button_run_clicked')
        print('Heyhey !')
        
        if self.is_running == False:
            self.is_running = True
            self.button_run.set_text('Pause')
            self.button_run.set_colors(background='blue')
            self.run()
        else:
            # Stop to run if it is running
            self.is_running = False
            if self.is_reseted:
                self.button_run.set_text('Start')
                self.button_run.set_colors(background='green')       
            else:
                self.button_run.set_text('Continue')
                self.button_run.set_colors(background='green') 

    def button_save_clicked(self):
        """
        Save the data
        """                       
        _debug('GUIPiPulseOptimization: button_save_clicked')
        
        # Note the information on the data
        N_col = len(self.Z) # Number of columns\
        # Get the pipulse time
        self.dt_us = self.gui_pulser.gui_Rabi_power.treeDic_settings['dt_pulse']
        
        self.databox = sm.data.databox()
        self.str_date = time.ctime(time.time())
        
        self.databox.insert_header('date', self.str_date)
        self.databox.insert_header('f_min', self.fmin)
        self.databox.insert_header('f_max', self.fmax)
        self.databox.insert_header('N_f', self.Nf)
        self.databox.insert_header('P_min', self.Pmin)
        self.databox.insert_header('P_maz', self.Pmax)
        self.databox.insert_header('N_p', self.Np)   
        self.databox.insert_header('dt_pulse_us', self.dt_us) 
        self.databox.insert_header('N_col', N_col)
        
        # Add each column 
        for i in range(N_col):
            col = self.Z[i]
            self.databox['Col%d'%i] = col    
            
        # This will open a dialog window for saving the databox
        self.databox.save_file()
        
    def run(self):
        """
        run the measurement
        """
        _debug('GUIPiPulseOptimization: run')
        
        # Prepare the axis
        self.fmin = self.treeDic_settings['f_min'] 
        self.fmax = self.treeDic_settings['f_max'] 
        self.Nf   = self.treeDic_settings['N_f'  ] 
        self.fs = np.linspace(self.fmin, self.fmax, self.Nf)
        
        self.Pmin = self.gui_pulser.gui_Rabi_power.treeDic_settings['P_min']
        self.Pmax = self.gui_pulser.gui_Rabi_power.treeDic_settings['P_max']
        self.Np   = self.gui_pulser.gui_Rabi_power.treeDic_settings['N']
        self.Ps = np.linspace(self.Pmin, self.Pmax, self.Np)
        
        # Initiate the map
        self.Z = np.zeros((self.Nf, self.Np))
        self.map.set_data(self.Z, 
                          x_info=(self.Pmin,self.Pmax, self.Np),
                          y_info=(self.fmin, self.fmax, self.Nf),
                          label_x = 'Power (dBm)', 
                          label_y = 'Frequency (Ghz)')

        for i, f in enumerate(self.fs):
            _debug('GUIPiPulseOptimization: run: f=', f)
            # The first step is to prepare the pulse sequence. 
            # Modify the setting of the sub_gui
            self.gui_pulser.gui_Rabi_power.treeDic_settings['Frequency'] = f
            # Prepare the specific sequence. This should prepare everything in the pulser gui
            self.gui_pulser.gui_Rabi_power.button_prepare_experiment.click()
            
            # The data in the FPGA should not change, so we don't need to click 
            # On convert
            # But we need to reset, otherwise the iteration increments by one unity
            # After it reached the maximum
            self.gui_pulser.button_reset.click()
            
            _debug('GUIPiPulseOptimization: run: f=', f, ' Run')
            # Run the sequence
            self.gui_pulser.button_start.click()
            
            # When it stops to run, collect the data
            self.data = self.gui_pulser.gui_Rabi_power.databoxplot
            
            _debug('GUIPiPulseOptimization: run: f=', f, ' Collect data')
            
            self.Z[i] = self.data[1]
            
            # Update the image
            self.map.set_data(self.Z)

            
            _debug('GUIPiPulseOptimization: run: f=', f, 'Okay')


        

 
    
if __name__ == '__main__':
    _debug_enabled     = True


     # Create the fpga api
    bitfile_path = ("X:\DiamondCloud\Magnetometry\Acquisition\FPGA\Magnetometry Control\FPGA Bitfiles"
                    "\Pulsepattern(bet_FPGATarget_FPGAFULLV2_WZPA4vla3fk.lvbitx")
    resource_num = "RIO0"     
    
#    fpga = _fc.FPGA_api(bitfile_path, resource_num) # Create the api   
#    fpga.open_session()
#    self = GuiMainPulseSequence(fpga) 
#    self.show()

    
    import api_fpga as _fc
    fpga_fake = _fc.FPGA_fake_api(bitfile_path, resource_num) # Create the api   
    fpga_fake.open_session()
    
    import gui_pulser
    gui = gui_pulser.GuiMainPulseSequence(fpga_fake)
    
    
    self = GUIPiPulseOptimization(gui)
    self.show()
    






















