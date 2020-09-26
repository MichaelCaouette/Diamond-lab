# -*- coding: utf-8 -*-
"""
Created on Thu May 21 15:27:02 2020


A gui for taking the counts live


@author: Childresslab, Michael
"""


from spinmob import egg
import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error


from converter import Converter # For converting the pattern for counting
import sound

import time

# Debug stuff.
_debug_enabled     = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))

class GUICounts(egg.gui.Window):
    """
    GUI for taking the counts, live. 
    
    It is this gui who is in charge of taking any counts for the main 
    confocal gui.
    
    """
    def __init__(self, fpga, name="Counter", size=[700,500]): 
        """
        Initialize 
        
        fpga:
            "FPGA_api" object from api_fpga.py. 
            This is the object shared amoung the GUIs for controlling the fpga. 
            The session of he fpga must already be open.        
        
        """    
        _debug('GUICounts:__init__')
        _debug('I have missed more than 9000 shots in my career.– Michael Jordan')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        self.fpga = fpga

        
        # Some attributes
        self.is_taking_counts = False # Weither or not we are taking counts. 
        self.is_playing_sounds = False #Weither or not the sound with count is on
        self.t0 = time.time() # Reference time
        self.dt = 0 # This will store how much time was elapsed between two rruns (for connecting the x axis at each run) 
        self.time_last_run = self.t0 # This is the time at the last run
        
        # Fill up the GUI 
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUICounts: initialize_GUI')
        
        # Place a qt SpinBox for the count time, in ms
        self.place_object(egg.gui.Label('Count time -->\ninterval (ms)'))
        self.NumberBox_count_time = egg.gui.NumberBox(value=5, step=1, 
                                                      bounds=(0, None))
        self.place_object(self.NumberBox_count_time, alignment=1)
        self.connect(self.NumberBox_count_time.signal_changed, self.numberBox_count_time_changed)
        self.numberBox_count_time_changed() # Initialize the value  
        
        # Place a qt SpinBox for the total point recorded in the plot
        self.new_autorow()
        self.place_object(egg.gui.Label('Number of point recorded -->\n(History)'))
        self.NumberBox_history = egg.gui.NumberBox(value=1000, step=1, 
                                                   int=True,
                                                      bounds=(0, None))
        self.place_object(self.NumberBox_history, alignment=1)
        self.connect(self.NumberBox_history.signal_changed, self.numberBox_history_changed)
        self.numberBox_history_changed() # Initialize the value  

        # Place the button for taking the counts
        self.new_autorow()
        self.button_take_counts = self.place_object(egg.gui.Button())
        self.button_take_counts.set_text('Take counts')
        self.button_take_counts.set_style('background-color: rgb(0, 200, 0);')
        self.connect(self.button_take_counts.signal_clicked, self.button_take_counts_clicked) 

        # Have a button for having sounds related to the count
        self.button_sound = self.place_object(egg.gui.Button())
        self.button_sound.set_text('Sound with counts :3')
        self.button_sound.set_style('background-color: rgb(255, 155, 255);')
        self.connect(self.button_sound.signal_clicked, self.button_sound_clicked) 
        
        # Place a label for the counts
        self.label_counts = self.place_object(egg.gui.Label('Counts/sec:: Nothing'),
                                              row = 0, column=2, alignment=0, 
                                              row_span=3)
        self.make_beautiful_style_counter()

        self.set_column_stretch(2,10)
        #Place the plot for the count VS time
        self.new_autorow()
        # Add a Data Box plotter for the count
        self.databoxplot_count = self.place_object(egg.gui.DataboxPlot(), column_span=3, alignment=0)  
        
    def make_beautiful_style_counter(self):
        """
        Make the reading of the counts to look bad-ass
        """
        self.label_counts.set_style('background-color: rgb(255, 255, 0);border-style: outset;border-width: 2px;border-radius: 10px;border-color: beige;font: bold 40px;min-width: 10em;padding: 6px;')
        
    def button_take_counts_clicked(self):
        """
        What to do when the take counts button is clicked
        """
        _debug('GUICounts: button_take_counts_clicked')
        
        if self.is_taking_counts == False:
            # Note that we are taking counts
            self.button_take_counts.set_text('Stop the counts')
            self.button_take_counts.set_style('background-color: rgb(255, 100, 100);')
            self.is_taking_counts = True          
            # Run the taking of counts
            self.run_take_counts()
        else:
            # Stop to take counts if we were taking counts
            self.is_taking_counts = False
            # Update the GUI
            self.button_take_counts.set_text('Take counts')
            self.button_take_counts.set_style('background-color: rgb(0, 200, 0);')     
            
    def button_sound_clicked(self):
        """
        """
        _debug('GUICounts: button_sound_clicked')
        
        if self.is_playing_sounds == False:
            # Note that we are playing sounds
            self.button_sound.set_text('Stop sounds')
            self.button_sound.set_style('background-color:rgb(255, 155, 0);')
            self.is_playing_sounds = True
            # Create the sound object
            self.sound = sound.sound()
            # Deternmine the bounds, which will be useful for mapping the counts to a frequency
            self.cmax = 1e6 # Maximum count to consider
            self.cmin = 0 # Minimum couts to consider
            self.crange = self.cmax - self.cmin # Range of count to consider
            self.fmax = 2000 # Maximum frequency for the maximum counts
            self.fmin = 150  # Minimum frequenmcy for the minimimum counts
            self.frange = self.fmax - self.fmin # Range of frequency to play
            # The attribute "self.is_playing_sounds" will determined in other 
            # loop if the sound is emite or not. 
            
            
        else:
            # Stop the sound if it was on
            self.is_playing_sounds = False
            # Update the GUI
            self.button_sound.set_text('Sound with counts :3')
            self.button_sound.set_style('background-color: rgb(255, 155, 255);')   
            
                    
        
            
    def numberBox_count_time_changed(self):
        """
        What to do when the count time changes. 
        """
        # This is the time interval for counting on each point. 
        # In milli-second
        self.count_time_ms = self.NumberBox_count_time.get_value()
        self.prepare_acquisition() # Prepare the fpga for that.
        _debug('GUICounts: numberBox_count_time_changed: value is ', self.count_time_ms)

    def numberBox_history_changed(self):
        """
        What do to when the history is changed.
        """
        # This is the number of point shown in the plot
        self.history = self.NumberBox_history.get_value()
        _debug('GUICounts: numberBox_history_changed: value is ', self.history)
        
        
    def run_take_counts(self):
        """
        Take counts for a certain amount of time ? 
        """
        _debug('GUICounts: run_take_counts')
        
        # Prepare the fpga
        self.prepare_acquisition()
        
        # Do the things
        # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
        self.process_events()    
        
        
        self.dt += time.time() - self.time_last_run # Time elapsed since last run
        self.elapsed_time = time.time() - self.t0 - self.dt
        
        # Take counts until the elapsed time is higher than the desired 
        # acquisition time OR until we click on stop and is_taking_count gets false.
        while self.is_taking_counts:
            
            # Get the counts (d'uh !)
            # Two step: runt he pulse pattern and get the counts. 
            self.fpga.run_pulse() 
            self.counts =  self.fpga.get_counts()[0]
            
            self.counts_per_sec = 1e3*self.counts/self.count_time_ms
        
            # Update the label
            self.label_counts.set_text('Counts/sec: %d'%self.counts_per_sec)
#            self.make_beautiful_style_counter()
            #Update the plot 
            self.databoxplot_count.append_row([self.elapsed_time, self.counts_per_sec],
                                                 ['Time_(s)', 'Counts_per_sec'],
                                                 history=self.history).plot()
            # Check how much time as elapsed, shifted by the last run.
            self.elapsed_time = time.time() - self.t0 - self.dt
            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events() 
            
            # Play the sound
            if self.is_playing_sounds:
                self.alpha = (self.counts_per_sec - self.cmin)/self.crange
                self.Hz = self.alpha*self.frange + self.fmin
                self.sound.play_wobble(self.Hz, 0.5, duration=self.count_time_ms/1000)
            
            
            
        # Note what time it is for substracting the x-axis in the next run
        self.time_last_run = time.time()
            
        # Finalize
        
        # Update the GUI        
        if self.is_taking_counts:
            # This will stop the count only if self-is_taking_counts is True
            self.button_take_counts_clicked()   
 

    def prepare_acquisition(self):
        """
        Prepare the acquisition of counts. 
        """
        _debug('GUICounts: prepare_acquisition')

        # Set the fpga NOT in each tick mode
        self.fpga.set_counting_mode(False)
        
        # Create the data array from counting
        # Prepare DIO1 in state 1
        self.fpga.prepare_DIOs([1], [1]) 
        # Get the actual DIOs, because there might be other DIOs open.
        self.dio_states = self.fpga.get_DIO_states() 
        # Convert the instruction into the data array
        conver = Converter() # Load the converter object.
        nb_ticks = self.count_time_ms*1e3/(conver.tickDuration)
        self.data_array = conver.convert_into_int32([(nb_ticks, self.dio_states)])
        
         # Send the data_array to the FPGA
        self.fpga.prepare_pulse(self.data_array)

    def event_fpga_change(self):
        """
        Dummy function to be overrid. 
        
        It is called after that the value on the fpga changed.
        Not call during the continuous count, because it would be too much.  
        """
        
    def update_GUI_with_fpga(self):
        """
        Update the gui such that the widgets match with the fpga. 
        That is useful for the implementation with other GUI that also 
        modifies the fpga. 
        """
        _debug('GUICounts: update_GUI_with_fpga')
        # There is nothing to update with the fpga. 
        # The count time interval is note recored in the fpga, because it is 
        # hidden in the data array
  

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
    


    self = GUICounts(fpga)
    self.show()
    




