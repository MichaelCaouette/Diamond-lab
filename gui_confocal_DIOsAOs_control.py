# -*- coding: utf-8 -*-
"""
Created on Thu May 21 15:27:02 2020


A GUI for controling the DIOs and AOs voltages


@author: Childresslab, Michael
"""

import numpy as np

from scipy.optimize import curve_fit

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


class GUIDIOsAOsControl(egg.gui.Window):
    """
    GUI for controlling the steady state of the DIOs and AOs.
    
    The goal is thatt eh DIOs and AOs are automatically changed as we change there 
    statut. Unlike in Labview where we need to click on write output. 
    
    """
    def __init__(self, fpga, name="DIOs and AOs", size=[700,500]): 
        """
        Initialize 
        
        fpga:
            "FPGA_api" object from api_fpga.py. 
            This is the object shared amoung the GUIs for controlling the fpga. 
            The session of he fpga must already be open.
        """    
        _debug('GUIDIOsAOsControl:__init__')
        _debug('Success is going from failure to failure without losing your enthusiasm – Winston Churchill')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)

        self.fpga = fpga
        
        
        # Fill up the GUI 
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIDIOsAOsControl: initialize_GUI')
        
        # Prepare the list of the DIOs
        self.list_DIOs = []
        # Place the Radio Button for the DIOs with some labels
        self.place_object(egg.gui.Label(text='Label for the DIOs'), 
                          row=0, column=0, alignment=1)
        self.place_object(egg.gui.Label(text='State of the DIOs'), 
                          row=0, column=1, alignment=1)        
        self.radioButton_DIOs = []
        for i in range(2,16):
            self.list_DIOs.append(i)
            # Placee the checkboxe 
            self.radioButton_DIOs.append(egg.pyqtgraph.Qt.QtWidgets.QRadioButton('DIO %d'%i))
            self.radioButton_DIOs[-1].setAutoExclusive(False)
            self.new_autorow()
            self.place_object(egg.gui.TextBox(autosettings_path='TextBox_DIO%d'%i),
                              row=i-1, column=0, alignment=1)
            self.place_object(self.radioButton_DIOs[-1], 
                              row=i-1, column=1, alignment=1)
            self.connect(self.radioButton_DIOs[-1].clicked, self.update_fpga)
#        
        # Prepare the list of AOs
        self.list_AOs = []
        #Place the AOs with tree dictionary
        self.treeDict_AOs  = egg.gui.TreeDictionary(autosettings_path='setting_DIOsAOsControl')
        self.place_object(self.treeDict_AOs, 
                          row=0, column=2, alignment=1, row_span=20)   
        for i in range(8):
            self.list_AOs.append(i)
            key = 'AO_%d/Voltage'%i
            self.treeDict_AOs.add_parameter(key, 0, 
                                               type='float', step=1, 
                                               bounds=[-10, 10], suffix=' V',
                                               tip='Voltage of the AO')
            # Connect the value change to a signal
            self.treeDict_AOs.connect_signal_changed(key, self.update_fpga)
            # Also add a label
            self.treeDict_AOs.add_parameter('AO_%d/Label'%i, '', 
                                               type='str',
                                               tip='Label of the AO')            
        # Strecht the widgets to make them together\
        self.set_column_stretch(3, 10)
        self.set_row_stretch(16, 10)
        
    def update_fpga(self):
        """
        Update the value of the voltage on the AOs. 
        Also Automatically write it on the FPGA, with no wait time. 
        
        It doesn't clean the existing pulse sequence. It just readjusting the 
        DIOs and the AOs on the settings
        """
        _debug('GUIDIOsAOsControl: update_fpga')

        # Get the list of the state of each DIOs
        self.list_DIO_states = []
        for radioButton in self.radioButton_DIOs:
            self.list_DIO_states.append(int(radioButton.isChecked()))  
        
        # Get the voltage of the AOs from the tree dictionary
        self.list_AO_voltages = []
        for i in range(8):
            key = 'AO_%d/Voltage'%i
            self.list_AO_voltages.append(self.treeDict_AOs[key])
            
        # Get the new data array
        # For each data in the fpga data array, adjust the DIOs
        self.conver = Converter() # Load the converter object.
        self.old_datas = self.fpga.get_data_array()
        self.new_datas = [] # New data array 
        for self.old_data in self.old_datas:
            # First note the previous tivks and DIO state
            out = self.conver.int32_to_ticks_and_DIOs(int(self.old_data))
            self.ticks, self.old_DIO_states = out
            # Add or modifye the actual DIOs state
            self.new_DIO_states = self.old_DIO_states
            self.new_DIO_states[self.list_DIOs] = self.list_DIO_states
            
            self.new_data = self.conver.single_pulse_to_fpga(self.ticks, self.new_DIO_states)
            self.new_datas.append(self.new_data)
                        

        # Prepare the fpga with the values    
        self.fpga.prepare_AOs(self.list_AOs, self.list_AO_voltages)
        self.fpga.prepare_pulse(self.new_datas, 
                                is_zero_ending=False,
                                list_DIO_state = self.new_DIO_states)            
        self.fpga.prepare_wait_time(self.fpga.get_wait_time_us()) 
        
        # Run the FPGA with all these settings
        self.fpga.lets_go_FPGA()  
        
        # Call the event to say "hey, stuff changed on the fpga"
        self.event_fpga_change()
            
    def event_fpga_change(self):
        """
        Dummy function to be overrid. 
        
        It is called after that the value on the fpga changed.
        """
        return
        
    def update_GUI_with_fpga(self):
        """
        Update the gui such that the widgets match with the fpga. 
        That is useful for the implementation with other GUI that also 
        modifies the fpga. 
        """
        _debug('GUIDIOsAOsControl: update_GUI_with_fpga')
        
        # Update the DIOs
        # Get the states of the fpga
        dio_states = self.fpga.get_DIO_states()
        
        for i in range(2, 2+len(self.radioButton_DIOs)):
            state = dio_states[i]
            self.radioButton_DIOs[i-2].setChecked(state)
            
        # Update the AOs
        for AO in range(8):
            V = self.fpga.get_AO_voltage(AO)
            key = 'AO_%d/Voltage'%AO
            self.treeDict_AOs[key] = V
#            print(key, V) # For troubleshooting
        
        


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
    
    
    self = GUIDIOsAOsControl(fpga)
    self.show()
    





