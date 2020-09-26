# -*- coding: utf-8 -*-
"""
Created on Thu May 21 15:27:02 2020


Main GUI for doing confocal microscopy

@author: Childresslab, Michael
"""

# Import the relevant guis for confocal microscopy
from gui_confocal_counts import GUICounts
from gui_confocal_DIOsAOs_control import GUIDIOsAOsControl
from gui_confocal_map import GUIMap
from gui_confocal_optimizer import GUIOptimizer

from spinmob import egg
import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error



# Debug stuff.
_debug_enabled     = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))

        

class GUIMainConfocal(egg.gui.Window):
    """
    Main GUI for doing confocal microscopy. 
    The counts are taken from the FPGA in the class GUICounts
    
    """
    
    def __init__(self, fpga, name="Best confocal of the world", size=[1800,1000]): 
        """
        fpga:
            "FPGA_api" object from api_fpga.py. 
            This is the object shared amoung the GUIs for controlling the fpga. 
            The session of the fpga must already be open.    
            
        size:
            size of the window. 
        """    
        _debug('GUIMainConfocal:__init__')
        _debug('Everyone thinks of changing the world, but no one thinks of changing himself. – Leo Tolstoy')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)

        self.fpga = fpga
        
        # Some attributes
        self.was_taking_counts_before_optimizing = False # Weither or not the gui counts was running before the optimization 
        
        # Fill the GUI
        self.initialize_GUI()  
        
        # Connect (AKA overrid ) methods for synchronizing the sub_guis
        self.gui_outputs  .event_fpga_change = self.update_guis_but_gui_outputs
        self.gui_map      .event_fpga_change = self.update_guis_but_gui_map
        self.gui_optimizer.event_fpga_change = self.update_guis_but_gui_optimizer
#        # test
#        self.gui_optimizer.event_fpga_change = self.gui_outputs.update_GUI_with_fpga
        
        # The fpga change of the gui count is not connected, because the event_fpga_change is not really called in this gui. 
      
        self.gui_optimizer.event_optimize_starts = self.before_optimization
        self.gui_optimizer.event_optimize_ends   = self.after_optimization
        
        
        

    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIMainConfocal: initialize_GUI')
        


        # Prepare the GUI before to place them 
        self.gui_counts    = GUICounts(self.fpga)
        self.gui_outputs   = GUIDIOsAOsControl(self.fpga)
        self.gui_map       = GUIMap(self.fpga)
        self.gui_optimizer = GUIOptimizer(self.fpga)

        # Replace the optimer button outside, for easy access
        self.place_object(self.gui_optimizer.button_optimize,
                          row=1, column_span=2)
        
        # Place tabs !
        self.tabs1 = self.place_object(egg.gui.TabArea(), row=2, alignment=0)
        
        # Tab for showing the counts
        self.tab_counts_map = self.tabs1.add_tab('Counts and Map')
        # Place the Counter
        self.tab_counts_map.place_object(self.gui_counts, alignment=1)\
        # Place the mapper
        self.tab_counts_map.place_object(self.gui_map, column_span=1, 
                                         row_span=2, alignment=0)
        # Place the controller of the outputs
        self.tab_counts_map.new_autorow()
        self.tab_counts_map.place_object(self.gui_outputs, alignment=1)
        
        self.tab_counts_map.set_column_stretch(1, 10)
#        self.tab_counts_map.set_row_stretch(1, 10)
        
        # Tab for showing the optimization. 
        self.tab_optimize = self.tabs1.add_tab('Optimization details')
        self.tab_optimize.place_object(self.gui_optimizer )    
        
        # For fun, uncomment to make a uniform background
#        self.set_style('background-color: rgb(255, 200, 255);')

    def update_guis_but_gui_outputs(self):
        """
        Update all the guis with the fpga, but not the outputs gui. 
        """
        _debug('GUIMainConfocal: update_guis_but_gui_outputs')
        
        self.gui_map    .update_GUI_with_fpga()
        self.gui_counts .update_GUI_with_fpga()
        # The optimizer is not called, because there is nothing to do
        

    def update_guis_but_gui_map(self):
        """
        Update all the guis with the fpga, but not the map gui.
        """        
        _debug('GUIMainConfocal: update_guis_but_gui_map')
        
        self.gui_outputs.update_GUI_with_fpga()
        self.gui_counts .update_GUI_with_fpga()
        # The optimizer is not called, because there is nothing to do
        
    def update_guis_but_gui_optimizer(self):
        """
        Update all the guis with the fpga, but not the optimizer gui.
        """        
        _debug('GUIMainConfocal: update_guis_but_gui_optimizer')
        
        self.gui_outputs.update_GUI_with_fpga()
        self.gui_counts .update_GUI_with_fpga()  
        self.gui_map    .update_GUI_with_fpga()

    def before_optimization(self):
        """
        What to do before that the optimization starts
        """
        _debug('GUIMainConfocal: before_optimization')
        
        # Stop the counts if they are running.
        if self.gui_counts.is_taking_counts:
            # Note that count was running. This will allow to restart it is it was running. 
            # (This is impiortant for not running them during a pulse sequence)
            self.was_taking_counts_before_optimizing = True
            # Take note of the count time interval. 
            self.count_time_before_opt = self.gui_counts.count_time_ms
            # Click to stop the count
            self.gui_counts.button_take_counts.click()
        else:
            # Note that no count was running. Useful for not starting the counts after. 
            self.was_taking_counts_before_optimizing = False

    def after_optimization(self):
        """
        What to do after that the optimization is done.
        """
        _debug('GUIMainConfocal: after_optimization')
        
        # Restart to run the counts if they were running
        if self.was_taking_counts_before_optimizing:
            if not(self.gui_counts.is_taking_counts):
                # Re set the count time interval
                self.gui_counts.NumberBox_count_time.set_value(self.count_time_before_opt)
                # Click only if the count are not already runing
                self.gui_counts.button_take_counts.click()
            
                        
            
        


if __name__ == '__main__':
    
    import api_fpga as _fc
    import gui_confocal_counts as cc
    import gui_confocal_optimizer as co
    import gui_confocal_DIOsAOs_control as cdc
    import gui_confocal_map as cm
    
    cm._debug_enabled  = False
    cdc._debug_enabled = False
    co._debug_enabled  = True
    cc._debug_enabled  = False
    _debug_enabled     = True
    _fc._debug_enabled = True
    
    print('Hey on es-tu bin en coton-watte')
    
     # Create the fpga api
    bitfile_path = ("X:\DiamondCloud\Magnetometry\Acquisition\FPGA\Magnetometry Control\FPGA Bitfiles"
                    "\Pulsepattern(bet_FPGATarget_FPGAFULLV2_WZPA4vla3fk.lvbitx")
    resource_num = "RIO0"     
    fpga = _fc.FPGA_api(bitfile_path, resource_num) # Create the api   
    fpga.open_session()

    self = GUIMainConfocal(fpga)
    self.show()

#    fpga_fake = _fc.FPGA_fake_api(bitfile_path, resource_num) # Create the api   
#    fpga_fake.open_session()
#    self = GUIMainConfocal(fpga_fake)
#    self.show()

