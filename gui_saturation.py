# -*- coding: utf-8 -*-
"""
Created on Thu May 21 15:27:02 2020


A gui for taking saturation curve. 


@author: Childresslab, Michael
"""


import numpy as np

from spinmob import egg
import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error


from converter import Converter # For converting the pattern for counting

import time

# Debug stuff.
_debug_enabled     = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))

class GUISaturation(egg.gui.Window):
    """
    GUI for taking saturaton curve. 
    It scans the AOM (which varies the intensity of the laser) and monitor the 
    counts AND the intensity (trough a photo-diode on AI1)
    
    """
    def __init__(self, fpga, name="Saturater", size=[1000,700]): 
        """
        Initialize 
        
        fpga:
            "FPGA_api" object from api_fpga.py. 
            This is the object shared amoung the GUIs for controlling the fpga. 
            The session of he fpga must already be open.        
        
        """    
        _debug('GUISaturation:__init__')
        _debug('PLEASE FIND A QUOTE')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        self.fpga = fpga
        
        # Some attributes
        self.is_running = False # Weither or not saturation curve is going on tonight. 
        
        # Fill up the GUI
        self.initialize_GUI()
        
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUISaturation: initialize_GUI')

        # Place a buttong for the scan
        self.button_start = self.place_object(egg.gui.Button())
        self.button_start.set_text('Saturation, GO !')
        self.button_start.set_style('background-color: rgb(0, 200, 0);')
        self.connect(self.button_start.signal_clicked, self.button_start_clicked) 

        # Place a label for some indication
        text = 'The intensity is monitored through AI1.\nThe FPGA can only read AI1.'
        self.label_indication = egg.gui.Label(text=text)   
        self.place_object(self.label_indication)
        
        self.new_autorow()
        # Place the dictionay three for all the parameters
        self.treeDic_settings  = egg.gui.TreeDictionary(autosettings_path='setting_saturation')
        self.place_object(self.treeDic_settings, column=0, column_span=2)   
        self.treeDic_settings.add_parameter('Wait_after_AOs', 1, 
                                           type='int', step=1, 
                                           bounds=[0,None], suffix='us',
                                           tip='Time to wait after the AOs set.')
        self.treeDic_settings.add_parameter('Count_time', 1, 
                                           type='float', step=1, 
                                           bounds=[0,None], suffix='ms',
                                           tip='Count time during the scan')
        self.treeDic_settings.add_parameter('AO_to_scan', 3, 
                                           type='int', step=1, 
                                           bounds=[0,7],
                                           tip='Channel to scan')
        self.treeDic_settings.add_parameter('AO_min', 1, 
                                           type='float', step=0.5, 
                                           bounds=[0, 10], suffix=' V',
                                           tip='Minimum value to scan')  
        self.treeDic_settings.add_parameter('AO_max', 5, 
                                           type='float', step=0.5, 
                                           bounds=[0, 10], suffix=' V',
                                           tip='Maximum value to scan')      
        self.treeDic_settings.add_parameter('Nb_points', 50, 
                                           type='int', step=5, 
                                           bounds=[0, None],
                                           tip='Number of point to scan') 

        # Add a Data Box plotter for the curves
        self.databoxplot = self.place_object(egg.gui.DataboxPlot(),
                                             column=2)  
        

    def button_start_clicked(self):
        """
        Manage to start or stop the saturation curve.
        """   
        _debug('GUISaturation: button_start_clicked')
        
        if self.is_running == False:
            # Note that we are scanning
            self.button_start.set_text('Stop :O')
            self.button_start.set_style('background-color: rgb(255, 100, 100);')
            self.is_running = True
            
            # Run the scan
            self.run_saturation()
        else:
            # Stop to take counts if we were taking counts
            self.is_running = False # We stopped to scan
            self.button_start.set_text('Scan :D')
            self.button_start.set_style('background-color: rgb(0, 200, 0);')  

    def prepare_acquisition_pulse(self):
        """
        Prepare the acquisition of counts. 
        
        It prepares the pulse pattern and set the wait time. 
        
        """
        _debug('GUISaturation: prepare_acquisition')
        # Create the data array from counting
        # Prepare DIO1 in state 1
        self.fpga.prepare_DIOs([1], [1]) 
        # Get the actual DIOs, because there might be other DIOs open.
        self.dio_states = self.fpga.get_DIO_states() 
        # Convert the instruction into the data array
        conver = Converter() # Load the converter object.
        self.count_time_ms = self.treeDic_settings['Count_time']
        nb_ticks = self.count_time_ms*1e3/(conver.tickDuration)
        self.data_array = conver.convert_into_int32([(nb_ticks, self.dio_states)])
        
        # Upate the waiting time
        self.wait_after_AOs_us = self.treeDic_settings['Wait_after_AOs']
        self.fpga.prepare_wait_time(self.wait_after_AOs_us)
        
         # Send the data_array to the FPGA
        self.fpga.prepare_pulse(self.data_array)
            
    def run_saturation(self):
        """
        Run saturation curve. Yeah. 
        """
        _debug('GUISaturation: run_saturation')
        
        # Prepare the pulse pattern for reading the counts
        self.prepare_acquisition_pulse()
        
        # Get the relevant settings
        self.AO_min = self.treeDic_settings['AO_min']
        self.AO_max = self.treeDic_settings['AO_max']
        self.Nb_pts = self.treeDic_settings['Nb_points']
        self.AO     = self.treeDic_settings['AO_to_scan']
        
        # Determine the voltages to scan
        self.voltage_to_scan = np.linspace(self.AO_min, self.AO_max, self.Nb_pts)
        
        # Prepare the arrays to plot and save
        self.AO_voltages = [] # Will contain the scanned voltages 
        self.counts      = [] # For the counts
        self.AI_readings = [] # The intensity of the photo-diode 
        
        # Scan each voltage
        for i in range(self.Nb_pts):
            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events() 
            if self.is_running == False:
                # It gonna stop if we don't want to continue.
                break
            
            # Set the AO value
            V_AO = self.voltage_to_scan[i]
            self.AO_voltages.append(  V_AO )
            self.fpga.prepare_AOs([self.AO], [V_AO])
            
            # Get the count
            # Two step: runt he pulse pattern and get the counts. 
            self.fpga.run_pulse() # This will also write the AOs
            self.counts.append(  self.fpga.get_counts()[0] )
            
            # Get the reading of AI1
            self.AI_readings.append( self.fpga.get_A1_voltage() )
            
            
            # Get the counts and intensity
            #TODO Remove the following line when the implementation will be completed. 
            # The purpose is just to test the gui with fake counts
#            time.sleep(0.3)
#            print(time.ctime(time.time()))
#            # Fake data
#            x = self.AO_voltages[-1]
#            print(x)
#            y1 = np.random.poisson(100000/(1 + np.exp(-(x-10))) )
#            self.counts.append(y1)
#            y2 = np.random.poisson(5000/(1 + np.exp(-0.5*(x-10))) )
#            self.AI_readings.append(y2)
            
            
            # Update the plot
            self.databoxplot['AO_voltage'] = self.AO_voltages
            self.databoxplot['Counts'] = self.counts
            self.databoxplot['AI_reading'] = self.AI_readings
            self.databoxplot.plot()
            
        # Stop the button if it was not stopped during the loop
        if self.is_running:
            self.button_start_clicked()     
            
        # Add all the element of the three dictionnary in the databox
        for key in self.treeDic_settings.get_keys():
            # Add each element of the dictionnary three
            self.databoxplot.insert_header(key , self.treeDic_settings[key])        
            
            
            


if __name__ == '__main__':
    
    import api_fpga as _fc
    
    _debug_enabled     = True
    _fc._debug_enabled = False
    
    print('Hey on es-tu bin en coton-watte')
    
     # Create the fpga api
    bitfile_path = ("X:\DiamondCloud\Magnetometry\Acquisition\FPGA\Magnetometry Control\FPGA Bitfiles"
                    "\Pulsepattern(bet_FPGATarget_FPGAFULLV2_WZPA4vla3fk.lvbitx")
    resource_num = "RIO0"     
    fpga = _fc.FPGA_api(bitfile_path, resource_num) # Create the api   
    fpga.open_session()
    


    self = GUISaturation(fpga)
    self.show()
    




