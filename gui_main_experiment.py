# -*- coding: utf-8 -*-
"""
Created on Wed Jul  1 10:39:47 2020

Main GUI for running the experiment

@author: Childresslab
"""


from spinmob import egg
import gui_confocal_main
import gui_pulser
import gui_saturation
import gui_pipulse_optimization
import gui_magnet
from converter import Converter # For converting the pattern for counting

import sys # Useful for error handling
import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error

_debug_enabled     = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))
        
 

       
class GUIMainExperiment(egg.gui.Window):
    """
    Main GUI for running the experiment. 
    It contains:
        - The confocal
        - The pulser (for performing pulse sequences)
        - The frequency generator (for setting the frequency list, etc)
        
    TODO: Add the opportunity to save some combination of pulse sequence and 
          frequency generator parameters. Use tree dictionnary for that ?
    
    """
    
    def __init__(self, fpga, name="Best experiment of the world", size=[1800,1000]): 
        """
        fpga:
            "FPGA_api" object from api_fpga.py. 
            This is the object shared amoung the GUIs for controlling the fpga. 
            The session of the fpga must already be open.    
            
        size:
            size of the window. 
        """    
        _debug('GUIMainExperiment: __init__')
        _debug('Great things are done by a series of small things brought together – Vincent Van Gogh')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)

        # Take the sacro-saint fpga
        self.fpga = fpga
        # Fill the GUI
        self.initialize_GUI()  
        
        
        # Some attribute
#TODO remove this line if everything is cool.
#        self.pulse_was_running_before_optimizing = False
#        self.magnet_scan_line_was_running_before_optimizing = False
        

        
        #TODO Important Better handlge the optimization during either the pulse
        # Sequence or during the magnet scan. Very important, because we gonna 
        # have other protocols which will want to use the optimizer !
        # Maybe the information should be encoded in the specific GUIs themself !
        # Overrid some methods
#TODO remove this line if everything is cool.
#        self.gui_pulser.event_optimize = self.pulser_optimize        
#        self.gui_confocal.gui_optimizer.event_optimize_ends   = self.after_optimization
#        self.gui_magnet.gui_sweep_lines.event_one_line_is_swept = self.magnet_scan_line_optimize
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIMainExperiment: initialize_GUI')

        # Prepare the GUI before to place them 
        self.gui_confocal   = gui_confocal_main.GUIMainConfocal(self.fpga)
        self.gui_pulser     = gui_pulser.  GuiMainPulseSequence(self.fpga, 
                                                                self.gui_confocal.gui_optimizer)
        self.gui_saturation = gui_saturation.     GUISaturation(self.fpga)
        self.gui_magnet     = gui_magnet.GUIMagnet(self.fpga, 
                                                   self.gui_confocal.gui_optimizer)   
        
        
        # Replace the optimer button outside, for easy access
        self.place_object(self.gui_confocal.gui_optimizer.button_optimize,
                          row=1)   
        
        # Place a button for printing the bugs
        self.button_checkbug = egg.gui.Button('Check is everything is cool',
                                              tip='Print the last error')
        self.place_object(self.button_checkbug, row=1)
        self.connect(self.button_checkbug.signal_clicked, self.button_checkbug_clicked)
        # Plus the label for the print
        self.label_checkbug = egg.gui.Label('Welcome to the best experiment since 1992.')
        self.place_object(self.label_checkbug, row=1)
        
        # Place tabs
        self.tabs1 = self.place_object(egg.gui.TabArea(), 
                                       row=2, column=0,column_span=5, alignment=0)
        
        # Tab for the confocal
        self.tab_confocal = self.tabs1.add_tab('Confocal')
        self.tab_confocal.place_object(self.gui_confocal, alignment=0)
        
        # Tab for the pulser
        self.tab_pulser = self.tabs1.add_tab('Pulser')
        self.tab_pulser.place_object(self.gui_pulser, alignment=0)
        
        # Tab for the saturation analysis
        self.tab_saturation = self.tabs1.add_tab('Saturation curve')
        self.tab_saturation.place_object(self.gui_saturation, alignment=0)

        # Tab for the control of the magnet
        self.tab_magnet = self.tabs1.add_tab('Magnetooo')
        self.tab_magnet.place_object(self.gui_magnet, alignment=0)
        
        # Tab for miscaleneous experiment that are more complexe that simple 
        # pulse sequence
        # Each experiment will be placed into tabs2
        self.tabs2 = egg.gui.TabArea()   
        self.tab_high_level = self.tabs1.add_tab('Awesome experiment')
        self.tab_high_level.place_object(self.tabs2,
                                         row=2, column=0,column_span=5, alignment=0)
        
        # Place a tab for the pi-pulse
        self.gui_pipulse_opt = gui_pipulse_optimization.GUIPiPulseOptimization(self.gui_pulser)
        self.tab_pipulse = self.tabs2.add_tab('Pi-pulse')
        self.tab_pipulse.place_object(self.gui_pipulse_opt, alignment=0)

        # Place a tab for the adaptive Bayes
        self.tab_bayes = self.tabs2.add_tab('Adaptive Bayes')
        self.tab_bayes.place_object(egg.gui.Button('Wooho'))  
        

    def button_checkbug_clicked(self):
        """
        Print the last bug
        """     
        _debug('GUIMainExperiment: button_checkbug_clicked')  
        
        s = str(sys.last_value)
        self.label_checkbug.set_text('Last error: '+s)
 
     
if __name__ == '__main__':
    
    import api_fpga 
    
    _debug_enabled     = True
    gui_pulser._debug_enabled = True
    gui_confocal_main._debug_enabled = False
    gui_pipulse_optimization._debug_enabled = False
    gui_magnet._debug_enabled = False
    import gui_confocal_optimizer
    gui_confocal_optimizer._debug_enabled = True
    api_fpga.debug_enabled = False
    
    print('Hey on es-tu bin en coton-watte')
    
     # Create the fpga api
    bitfile_path = ("X:\DiamondCloud\Magnetometry\Acquisition\FPGA\Magnetometry Control\FPGA Bitfiles"
                    "\Pulsepattern(bet_FPGATarget_FPGAFULLV2_WZPA4vla3fk.lvbitx")
    resource_num = "RIO0"     
    fpga = api_fpga.FPGA_api(bitfile_path, resource_num) # Create the api   
    fpga.open_session()
    
    self = GUIMainExperiment(fpga)
    self.show()
    
    
#    fpga_fake = _fc.FPGA_fake_api(bitfile_path, resource_num) # Create the api   
#    fpga_fake.open_session()
#    
#    self = GUIMainExperiment(fpga_fake) 
#    self.show()    
    
    
    
    
    
    
    
    
    
    
    
    
    
    