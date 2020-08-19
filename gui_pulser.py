# -*- coding: utf-8 -*-
"""
Created on Thu May 21 15:27:02 2020

A GUI for playing with the FPGA

@author: Childresslab, Michael
"""

import numpy as np
from spinmob import egg
import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error

import fpga_control as _fc
from converter import Converter # This convert the sequence object into fpga data
from pulses import GUIPulsePattern
from pulses import ChannelPulses, PulsePatternBlock, Sequence
import pulses
from converter import GUIFPGAInstruction
from predefined_sequence import PredefinedSequence

import gui_signal_generator

import time


# Debug stuff.
_debug_enabled     = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))
        

class GuiMainPulseSequence(egg.gui.Window):
    """
    Main GUI for running the FPGA with pulse sequence. 
    """
    def __init__(self, fpga, name="Best pulser of the world", size=[1400,700]): 
        """
        fpga:
            "FPGA_api" object from fpga_control.py. 
            This is the object shared amoung the GUIs for controlling the fpga. 
            The session of the fpga must already be open.    
        """    
        _debug('GuiMainPulseSequence:__init__')
        _debug('Don’t watch the clock; do what it does. Keep going. – Sam Levenson')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        
        self.fpga = fpga           
       
        # Some attribute
        self.is_running = False # Weither or not the pulse sequence is running    

        # Initialize variable
        self.data_array = []
        self.length_data_block_s = []
        self.selected_experiment = 'Predefined' # This tells which experiment is selected

        # Fill the GUI
        self.initialize_GUI() 
        
        # Reset the data. This also initialise some attributes
        self.reset_data()

    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GuiMainPulseSequence: initialize_GUI')

        # Place the run button and connect it
        self.button_start = egg.gui.Button('Start',
                                           tip='Start/Pause the fpga sequence.')
        self.place_object(self.button_start)
        self.connect(self.button_start.signal_clicked, self.button_start_clicked)
        self.button_start.disable() # Disable is until data are available

        # Place the button reset and connect it. 
        self.button_reset= egg.gui.Button("Reset :O")
        self.place_object(self.button_reset)
        self.connect(self.button_reset.signal_clicked, self.button_reset_clicked)
        
        # Place the conversion button and connect it
        self.button_convert_sequence = self.place_object(egg.gui.Button("Convert"))
        self.connect(self.button_convert_sequence.signal_clicked, self.button_convert_sequence_clicked)        
 
        # Place the show_fpga_data button and connect it
        self.show_fpga_data_button = self.place_object(egg.gui.Button("Show FPGA data"))
        self.connect(self.show_fpga_data_button.signal_clicked, self.show_fpga_data)   
        
        # Place a label for the FPGA length 
        self.label_data_length = self.place_object(egg.gui.Label('FPGA data length: XX'))
        
        
        # Place a label for the selected experiment
        text = 'Experiment = ' + self.selected_experiment
        self.label_selected_experiment = egg.gui.Label(text)
        self.place_object(self.label_selected_experiment)

        # Place a qt SpinBox for the number of FPGA loop
        self.new_autorow()
        self.place_object(egg.gui.Label('Maximum Nb of \nFPGA loop'))
        self.NumberBox_N_loopFPGA = egg.gui.NumberBox(value=100000, step=1, 
                                                      bounds=(1, None), int=True)
        self.place_object(self.NumberBox_N_loopFPGA, alignment=1)
        self.connect(self.NumberBox_N_loopFPGA.signal_changed, self.NumberBox_N_loopFPGA_changed)     
        self.NumberBox_N_loopFPGA_changed() # Initialize the value 
        
        # Place a label for the number of iteration performed
        self.iteration_label = self.place_object(egg.gui.Label('Iteration of FPGA:XX'))      

        # A spinbox for the number of iteration before optimization
        self.place_object(egg.gui.Label('Number of FPGA loop\nbefore optimization\n0=never optimize'))
        self.NumberBox_Nloop_before_optimize = egg.gui.NumberBox(value=100, step=1, 
                                                      bounds=(0, None), int=True)
        self.place_object(self.NumberBox_Nloop_before_optimize, alignment=1)
        self.connect(self.NumberBox_Nloop_before_optimize.signal_changed, 
                     self.NumberBox_Nloop_before_optimize_changed)     
        self.NumberBox_Nloop_before_optimize_changed() # Initialize the value 
        
        
        #######################
        # Place tabs
        ########################
        # Declare the object that we gonna use
        self.gui_pulse_builder = GUIPulseBuilder()
        self.sig_gen = gui_signal_generator.GUISignalGenerator('Anana',show=False)
        self.gui_sig_gen    = self.sig_gen.window       
        self.gui_predefined = GUIPredefined(self.fpga)
        self.gui_ESR        = GUIESR()
        self.gui_Rabi       = GUIRabi()
        self.gui_Rabi_power = GUIRabiPower()
        self.gui_pulse_calibration = GUICalibration()
        self.gui_spincontrast = GUISpinContrast()
        self.gui_T1_trace2         = GUIT1TimeTrace2()
        self.gui_T1_trace3         = GUIT1TimeTrace3()
        self.gui_T1_probeOneTime   = GUIT1probeOneTime()
        
        self.new_autorow()
        self.tabs1 = self.place_object(egg.gui.TabArea(autosettings_path='tabs1'),
                                       column_span=6, alignment=0)
        # Tab for the pulse sequence
        self.tab_sequence = self.tabs1.add_tab('Pulse Sequence\nViewer/Builder')
        self.tab_sequence.place_object(self.gui_pulse_builder, alignment=0)
        
        # Tab for the signal generator
        self.tab_sig_gen = self.tabs1.add_tab('Signal Generator')
        self.tab_sig_gen.place_object(self.gui_sig_gen)

        # Tab for the predefined experiment
        self.tab_predef = self.tabs1.add_tab('predefined\nexperiments')
        self.tab_predef._widget.setToolTip('This shows the result of predefined sequence')
        self.tab_predef.place_object(self.gui_predefined) 
        # Connecting the gui by overidding
        self.gui_predefined .event_prepare_experiment = self.prepare_predefined
        
        # Tab for the ESR measurement
        self.tab_ESR = self.tabs1.add_tab('ESR')
        self.tab_ESR.place_object(self.gui_ESR)
        # Connecting the gui by overidding
        self.gui_ESR        .event_prepare_experiment = self.prepare_ESR
        
        # Tab for the Rabi measurement
        self.tab_Rabi = self.tabs1.add_tab('Rabi')
        self.tab_Rabi.place_object(self.gui_Rabi)
        # Connecting the gui by overidding        
        self.gui_Rabi       .event_prepare_experiment = self.prepare_Rabi 

        # Tab for the Rabi measurement
        self.tab_Rabi_power = self.tabs1.add_tab('Rabi Power !')
        self.tab_Rabi_power.place_object(self.gui_Rabi_power)   
        # Connecting the gui by overidding
        self.gui_Rabi_power .event_prepare_experiment = self.prepare_Rabi_power
     
        # Tab for the pulse calibration
        self.tab_pulse_cal = self.tabs1.add_tab('Pulse Calibration')
        self.tab_pulse_cal.place_object(self.gui_pulse_calibration) 
        # Connecting the gui by overidding
        self.gui_pulse_calibration  .event_prepare_experiment = self.prepare_calibration   
        
        # Tab for the spin contrast
        self.tab_spincontrast = self.tabs1.add_tab('Spin Contrast')
        self.tab_spincontrast .place_object(self.gui_spincontrast )  
        # Connecting the gui by overidding
        self.gui_spincontrast.event_prepare_experiment = self.prepare_spincontrast
       
        # Tab for T1 :) Finnally
        self.tab_T1_trace2  = self.tabs1.add_tab('T1 two states :D')
        self.tab_T1_trace2 .place_object(self.gui_T1_trace2)   
        # Connecting the gui by overidding
        self.gui_T1_trace2         .event_prepare_experiment = self.prepare_T1_trace2

        # Tab for T1 :) Finnally
        self.tab_T1_trace3  = self.tabs1.add_tab('T1 three states :o')
        self.tab_T1_trace3 .place_object(self.gui_T1_trace3)   
        # Connecting the gui by overidding
        self.gui_T1_trace3         .event_prepare_experiment = self.prepare_T1_trace3                

        # Tab for the ultimate 
        self.tab_T1_probeOneTime  = self.tabs1.add_tab('Probe one time')
        self.tab_T1_probeOneTime .place_object(self.gui_T1_probeOneTime, alignment=0)   
        # Connecting the gui by overidding
        self.gui_T1_probeOneTime         .event_prepare_experiment = self.prepare_T1_probeOneTime

    def NumberBox_N_loopFPGA_changed(self):
        """
        What do to when the number of FPGA loop changes.
        """
        self.N_loopFPGA = self.NumberBox_N_loopFPGA.get_value()
        _debug('GuiMainPulseSequence: NumberBox_N_loopFPGA_changed: ', self.N_loopFPGA)        

    def NumberBox_Nloop_before_optimize_changed(self):
        """
        Ajdust the number of loop to perform before optimizing.
        """
        _debug('GuiMainPulseSequence: NumberBox_Nloop_before_optimize_changed')
        self.Nloop_before_optimize = self.NumberBox_Nloop_before_optimize.get_value()


    def button_convert_sequence_clicked(self):
        """
        What to do is the button convert is clicked
        """
        _debug('GuiMainPulseSequence: button_convert_sequence_clicked')

        if self.is_running == False:
            # Convert the sequence (Obviously)
            self.convert_sequence()            
            # Unablle the run button, because there are now data to be sent
            self.button_start.enable()
            self.button_start.set_text('Run')
            self.button_start.set_colors(background='green')
            
    def button_start_clicked(self):
        """
        What to do when the run instruction button is clicked
        """
        _debug('GuiMainPulseSequence: button_start_clicked')
        
        if self.is_running == False:
            self.is_running = True
            self.button_start.set_text('Pause')
            self.button_start.set_colors(background='blue')
            self.run_loops()
            
        else:
            # Stop to run if it is running
            self.is_running = False
            if self.is_reseted:
                self.button_start.set_text('Start')
                self.button_start.set_colors(background='green')       
            else:
                self.button_start.set_text('Continue')
                self.button_start.set_colors(background='green')  

    def button_reset_clicked(self):
        """
        Reset the data
        """
        _debug('GuiMainPulseSequence:  button_reset_clicked')
        
        # Stop to run 
        if self.is_running:
            self.button_start_clicked()
        # Reset
        self.reset_data()
        
        # Reupdate the button, because the if was not met the first time. 
        self.button_start.set_text('Start')
        self.button_start.set_colors(background='green')         
        
    def prepare_predefined(self):
        """
        Prepare the sub GUI and attributes for the predefined pulse sequences
        """
        _debug('GuiMainPulseSequence: prepare_predefined')
        
        # Note which experiment is selected
        self.selected_experiment = 'Predefined'
        # Update the label
        text = 'Experiment = ' + self.selected_experiment
        self.label_selected_experiment.set_text(text)   
        
        # Send the sequence to the pulse builder
        self.gui_pulse_builder.set_sequence(self.gui_predefined.sequence)

        # Set the fpga NOT in each tick mode
        self.CET_mode = False # It's gonna be set in the fpga in run_loops()
        
        # Overird the method to be called after each loop
        self.after_one_loop = self.gui_predefined.after_one_loop

#        # Extra cool thing to do
#        # Convert the sequence
#        self.convert_sequence()
#        # Send the data_array to the FPGA and initialize it
#        self.fpga.prepare_pulse(self.data_array)      
        
    def prepare_ESR(self):
        """
        Prepare the sub GUIs and attributes for the ESR measurement. 
        """
        _debug('GuiMainPulseSequence: prepare_ESR')
        
        # Note which experiment is selected
        self.selected_experiment = 'ESR'
        # Update the label
        text = 'Experiment = ' + self.selected_experiment
        self.label_selected_experiment.set_text(text)

        # Set the fpga NOT in each tick mode
        self.CET_mode = False # It's gonna be set in the fpga in run_loops()
        
        # Send the sequence to the pulse builder
        if self.gui_pulse_builder.sequence_has_delay:
            # Remove the delay if there was previously
            self.gui_pulse_builder.button_set_delays.click()
        # Set the sequence
        self.gui_pulse_builder.set_sequence( self.gui_ESR.sequence )
        # Set the delay
        self.gui_pulse_builder.button_set_delays.click()
        
        
        # Prepare the setting for the signal generator
        self.fmin = self.gui_ESR.treeDic_settings['f_min']
        self.fmax = self.gui_ESR.treeDic_settings['f_max']
        self.Nf   = self.gui_ESR.treeDic_settings['N']
        self.P    = self.gui_ESR.treeDic_settings['Power']
        self.sig_gen.settings['Generate-List/f1']    = self.fmin*1e9 #Convert into Hz
        self.sig_gen.settings['Generate-List/f2']    = self.fmax*1e9 #Convert into Hz
        self.sig_gen.settings['Generate-List/P1']    = self.P
        self.sig_gen.settings['Generate-List/P2']    = self.P
        self.sig_gen.settings['Generate-List/Steps'] = self.Nf
        
        # Prepare the signal generator for an ESR sequence
#        print('PLEASE UNCOMMENT 478')
        self.sig_gen.combo_mode.set_value(index=1) # Set in List mode
        self.sig_gen.button_generate_list.click()
        self.sig_gen.button_send_list.click()
        # Make the instrumenbt ready for the pulse sequence
        # The method should set the trigger to be external, pulse modulatiion, etc. 
        self.sig_gen.api.prepare_for_ESR()
        
        # Overird the method to be called after each loop
        self.after_one_loop = self.gui_ESR.after_one_loop    


    def prepare_Rabi(self):
        """
        Prepare the sub GUIs and attributes for the Rabi measurement. 
        """
        _debug('GuiMainPulseSequence: prepare_Rabi')
        
        # Note which experiment is selected
        self.selected_experiment = 'Rabi vs time'
        # Update the label
        text = 'Experiment = ' + self.selected_experiment
        self.label_selected_experiment.set_text(text)

        # Set the fpga NOT in each tick mode
        self.CET_mode = False # It's gonna be set in the fpga in run_loops()
        
        # Send the sequence to the pulse builder
        if self.gui_pulse_builder.sequence_has_delay:
            # Remove the delay if there was previously
            self.gui_pulse_builder.button_set_delays.click()
        # Set the sequence
        self.gui_pulse_builder.set_sequence( self.gui_Rabi.sequence )
        # Set the delay
        self.gui_pulse_builder.button_set_delays.click()
        

        
        # Prepare the setting for the signal generator
        self.tmin = self.gui_Rabi.treeDic_settings['t_in']
        self.tmax = self.gui_Rabi.treeDic_settings['t_end']
        self.Nt   = self.gui_Rabi.treeDic_settings['N']
        self.P    = self.gui_Rabi.treeDic_settings['Power']
        self.f    = self.gui_Rabi.treeDic_settings['Frequency']
        
        # Prepare the signal generator for the specific sequence
        self.sig_gen.combo_mode.set_value(index=0) # Set in Fixed mode
        self.sig_gen.number_dbm      .set_value(self.P)
        self.sig_gen.number_frequency.set_value(self.f*1e9 )#Convert into Hz
        self.sig_gen.api.prepare_for_Rabi()
        
        # Overird the method to be called after each loop
        self.after_one_loop = self.gui_Rabi.after_one_loop            

    def prepare_Rabi_power(self):
        """
        Prepare the sub GUIs and attributes for the Rabi power measurement
        """
        _debug('GuiMainPulseSequence: prepare_Rabi_power')
        
        # Note which experiment is selected
        self.selected_experiment = 'Rabi Power'
        # Update the label
        text = 'Experiment = ' + self.selected_experiment
        self.label_selected_experiment.set_text(text)

        # Set the fpga NOT in each tick mode
        self.CET_mode = False # It's gonna be set in the fpga in run_loops()
        
        
        # Send the sequence to the pulse builder
        if self.gui_pulse_builder.sequence_has_delay:
            # Remove the delay if there was previously
            self.gui_pulse_builder.button_set_delays.click()
        # Set the sequence
        self.gui_pulse_builder.set_sequence( self.gui_Rabi_power.sequence )
        # Set the delay
        self.gui_pulse_builder.button_set_delays.click()
        
        # Prepare the setting for the signal generator
        self.f = self.gui_Rabi_power.treeDic_settings['Frequency']
        self.Pmin = self.gui_Rabi_power.treeDic_settings['P_min']
        self.Pmax = self.gui_Rabi_power.treeDic_settings['P_max']
        self.Np   = self.gui_Rabi_power.treeDic_settings['N']
        self.sig_gen.settings['Generate-List/f1']    = self.f*1e9 #Convert into Hz
        self.sig_gen.settings['Generate-List/f2']    = self.f*1e9 #Convert into Hz
        self.sig_gen.settings['Generate-List/P1']    = self.Pmin
        self.sig_gen.settings['Generate-List/P2']    = self.Pmax
        self.sig_gen.settings['Generate-List/Steps'] = self.Np
        self.sig_gen.settings['Generate-List/Mode']  = 'Log'
        
        # Prepare the signal generator for an List sweep
        self.sig_gen.combo_mode.set_value(index=1) # Set in List mode
        self.sig_gen.button_generate_list.click()
        self.sig_gen.button_send_list.click()
        # Make the instrumenbt ready for the pulse sequence
        # The method should set the trigger to be external, pulse modulatiion, etc. 
        self.sig_gen.api.prepare_for_ESR() # It is the same instruction that for the ESR (For sweeping the list)
        
        # Overird the method to be called after each loop
        self.after_one_loop = self.gui_Rabi_power.after_one_loop   


    def prepare_T1_trace2(self):
        """
        Prepare the sub GUIs and attributes for the T1measurement. 
        """
        _debug('GuiMainPulseSequence: prepare_T1_trace2')
        
        # Note which experiment is selected
        self.selected_experiment = 'T1 time trace 2 states'
        # Update the label
        text = 'Experiment = ' + self.selected_experiment
        self.label_selected_experiment.set_text(text)

        # Set the fpga NOT in each tick mode
        self.CET_mode = False # It's gonna be set in the fpga in run_loops()

        # Send the sequence to the pulse builder
        if self.gui_pulse_builder.sequence_has_delay:
            # Remove the delay if there was previously
            self.gui_pulse_builder.button_set_delays.click()
        # Set the sequence
        self.gui_pulse_builder.set_sequence( self.gui_T1_trace2.sequence )
        # Set the delay
        self.gui_pulse_builder.button_set_delays.click()
        
        
        # Prepare the setting for the signal generator
        self.tmin = self.gui_T1_trace2.treeDic_settings['t_in']
        self.tmax = self.gui_T1_trace2.treeDic_settings['t_end']
        self.Nt   = self.gui_T1_trace2.treeDic_settings['N']
        self.P    = self.gui_T1_trace2.treeDic_settings['Power']
        self.f    = self.gui_T1_trace2.treeDic_settings['Frequency']
        
        # Prepare the signal generator for the specific sequence
        self.sig_gen.combo_mode.set_value(index=0) # Set in Fixed mode
        self.sig_gen.number_dbm      .set_value(self.P)
        self.sig_gen.number_frequency.set_value(self.f*1e9 )#Convert into Hz
        self.sig_gen.api.prepare_for_Rabi() # It is the same set up as Rabi
        
        # Put a very low number of repetition, just in case we forget to do so. 
        # ecause the sequence is, in general, slow. 
        self.gui_pulse_builder.NumberBox_repetition.set_value(1)
        
        # Overird the method to be called after each loop
        self.after_one_loop = self.gui_T1_trace2.after_one_loop     

    def prepare_T1_trace3(self):
        """
        Prepare the sub GUIs and attributes for the T1 measurement,
        when we take a time trace for the three ms states. 
        """
        _debug('GuiMainPulseSequence: prepare_T1_trace3')
        
        # Note which experiment is selected
        self.selected_experiment = 'T1 time trace 3 states'
        # Update the label
        text = 'Experiment = ' + self.selected_experiment
        self.label_selected_experiment.set_text(text)

        # Set the fpga NOT in each tick mode
        self.CET_mode = False # It's gonna be set in the fpga in run_loops()

        # Send the sequence to the pulse builder
        if self.gui_pulse_builder.sequence_has_delay:
            # Remove the delay if there was previously
            self.gui_pulse_builder.button_set_delays.click()
        # Set the sequence
        self.gui_pulse_builder.set_sequence( self.gui_T1_trace3.sequence )
        # Set the delay
        self.gui_pulse_builder.button_set_delays.click()
        
        
#        # Prepare the setting for the signal generator
#        self.f_msm1 = self.gui_T1_trace3.treeDic_settings['Frequency_ms_-1']
#        self.f_msp1 = self.gui_T1_trace3.treeDic_settings['Frequency_ms_+1']
#        self.Nf   = 2 # We have two frequencies to probe
#        self.P_msm1    = self.gui_T1_trace3.treeDic_settings['Power_ms_-1']
#        self.P_msp1    = self.gui_T1_trace3.treeDic_settings['Power_ms_+1']
#        # The first power/frequency will be the second in the pulse sequence,
#        # This is because we trigger for switching at the beggining for saving time. 
#        self.sig_gen.settings['Generate-List/f1']    = self.f_msp1*1e9 #Convert into Hz
#        self.sig_gen.settings['Generate-List/f2']    = self.f_msm1*1e9 #Convert into Hz
#        self.sig_gen.settings['Generate-List/P1']    = self.P_msp1
#        self.sig_gen.settings['Generate-List/P2']    = self.P_msm1
#        self.sig_gen.settings['Generate-List/Steps'] = self.Nf
#        
#        # Prepare the signal generator for the list sweep 
#        self.sig_gen.combo_mode.set_value(index=1) # Set in List mode
#        self.sig_gen.button_generate_list.click()
#        self.sig_gen.button_send_list.click()
#        # Make the instrumenbt ready for the pulse sequence
#        # The method should set the trigger to be external, pulse modulatiion, etc. 
#        self.sig_gen.api.prepare_for_ESR()
        
        
        self.tmin = self.gui_T1_trace3.treeDic_settings['t_in']
        self.tmax = self.gui_T1_trace3.treeDic_settings['t_end']
        self.Nt   = self.gui_T1_trace3.treeDic_settings['N']
        self.P    = self.gui_T1_trace3.treeDic_settings['Power']
        self.f    = self.gui_T1_trace3.treeDic_settings['Frequency']
        
        # Prepare the signal generator for the specific sequence
        self.sig_gen.combo_mode.set_value(index=0) # Set in Fixed mode
        self.sig_gen.number_dbm      .set_value(self.P)
        self.sig_gen.number_frequency.set_value(self.f*1e9 )#Convert into Hz
        self.sig_gen.api.prepare_for_Rabi() # It is the same set up as Rabi
        
        # Put a very low number of repetition, just in case we forget to do so. 
        # ecause the sequence is, in general, slow. 
        self.gui_pulse_builder.NumberBox_repetition.set_value(1)       
        
        
        
        # Put a very low number of repetition, just in case we forget to do so. 
        # ecause the sequence is, in general, slow. 
        self.gui_pulse_builder.NumberBox_repetition.set_value(1)
        
        # Overird the method to be called after each loop
        self.after_one_loop = self.gui_T1_trace3.after_one_loop     
        
    def prepare_calibration(self):
        """
        Prepare the sub GUIs and attributes for the Calibration measurement. 
        """
        _debug('GuiMainPulseSequence: prepare_calibration')
        
        # Note which experiment is selected
        self.selected_experiment = 'Calibration'
        # Update the label
        text = 'Experiment = ' + self.selected_experiment
        self.label_selected_experiment.set_text(text)
        
        # Set the fpga in each tick mode
        self.CET_mode = True# It's gonna be set in the fpga in run_loops()
        
        # Send the sequence to the pulse builder
        if self.gui_pulse_builder.sequence_has_delay:
            # Remove the delay if there was previously
            self.gui_pulse_builder.button_set_delays.click()
        # Set the sequence
        self.gui_pulse_builder.set_sequence( self.gui_pulse_calibration.sequence )
        # Set the delay
        self.gui_pulse_builder.button_set_delays.click()
        
        
        # Prepare the signal generator only if we want.
        if self.gui_pulse_calibration.treeDic_settings['DIO_pulse_modulation_1']>=0:
            self.P    = self.gui_pulse_calibration.treeDic_settings['Power']
            self.f    = self.gui_pulse_calibration.treeDic_settings['Frequency']
            
            # Prepare the signal generator for the specific sequence
            self.sig_gen.combo_mode.set_value(index=0) # Set in Fixed mode
            self.sig_gen.number_dbm      .set_value(self.P)
            self.sig_gen.number_frequency.set_value(self.f*1e9 )#Convert into Hz
            self.sig_gen.api.prepare_for_Rabi() # It fiex mode plus RF modulated, like Rabi
        
        # Overird the method to be called after each loop
        self.after_one_loop = self.gui_pulse_calibration.after_one_loop   

    def prepare_spincontrast(self):
        """
        Prepare the sub GUIs and attributes for the Spin Contrast measurement. 
        """
        _debug('GuiMainPulseSequence: prepare_spincontrast')
        
        # Note which experiment is selected
        self.selected_experiment = 'Spin Contrast '
        # Update the label
        text = 'Experiment = ' + self.selected_experiment
        self.label_selected_experiment.set_text(text)
        
        # Set the fpga in each tick mode
        self.CET_mode = True# It's gonna be set in the fpga in run_loops()
        
        # Send the sequence to the pulse builder
        if self.gui_pulse_builder.sequence_has_delay:
            # Remove the delay if there was previously
            self.gui_pulse_builder.button_set_delays.click()
        # Set the sequence
        self.gui_pulse_builder.set_sequence( self.gui_spincontrast.sequence )
        # Set the delay
        self.gui_pulse_builder.button_set_delays.click()
        
        
        # Prepare the signal generator 
        self.P    = self.gui_spincontrast.treeDic_settings['Power']
        self.f    = self.gui_spincontrast.treeDic_settings['Frequency']
            
        # Prepare the signal generator for the specific sequence
        self.sig_gen.combo_mode.set_value(index=0) # Set in Fixed mode
        self.sig_gen.number_dbm      .set_value(self.P)
        self.sig_gen.number_frequency.set_value(self.f*1e9 )#Convert into Hz
        self.sig_gen.api.prepare_for_Rabi() # Its fixe mode plus RF modulated, like Rabi
        
        # Overird the method to be called after each loop
        self.after_one_loop = self.gui_spincontrast.after_one_loop   

    def prepare_T1_probeOneTime(self):
        """
        Prepare the sub GUIs and attributes for the measurement of probing at
        a single time.
        """
        _debug('GuiMainPulseSequence: prepare_T1_probeOneTime')
        
        # Note which experiment is selected
        self.selected_experiment = 'T1 probing one time'
        # Update the label
        text = 'Experiment = ' + self.selected_experiment
        self.label_selected_experiment.set_text(text)
        
        # Set the fpga NOT in each tick mode
        self.CET_mode = False # It's gonna be set in the fpga in run_loops()

        # Send the sequence to the pulse builder
        if self.gui_pulse_builder.sequence_has_delay:
            # Remove the delay if there was previously
            self.gui_pulse_builder.button_set_delays.click()
        # Set the sequence
        self.gui_pulse_builder.set_sequence( self.gui_T1_probeOneTime.sequence )
        # Set the delay
        self.gui_pulse_builder.button_set_delays.click()
        
        # Prepare the setting for the signal generator
        #TODO do it !
        
        # Overird the method to be called after each loop
        self.after_one_loop = self.gui_T1_probeOneTime.after_one_loop   

        
        

        
    def convert_sequence(self):
        """
        Convert the sequence into data array
        """
        _debug('GuiMainPulseSequence: convert_sequence')
        # Reset the number of iteration
        self.button_reset_clicked()
        
        time_start = time.time()
        # Extract important information from the pulse sequence
        # Take the sequence from the pulse sequence GUI
        self.sequence = self.gui_pulse_builder.get_sequence()
        self.rep      = self.gui_pulse_builder.get_repetition()
        self.nb_block = self.gui_pulse_builder.get_nb_block()
        
        # Create the converter and convert
        cc = Converter()
        self.data_array = cc.sequence_to_FPGA(self.sequence, repetition=self.rep)
        time_elapsed = time.time() - time_start
        
        # Note the data lenght
        length = len(self.data_array)
        text = ('FPGA data length: %d'%length+
                '\nTime for conversion: %f sec'%time_elapsed)
        self.label_data_length.set_text(text )
        # Note also the lentght of each block
        self.length_data_block_s = cc.get_length_data_block_s()

    
    def reset_data(self):
        """
        Initialize the data before the run
        """
        _debug('GuiMainPulseSequence: reset_data')
        
        # Flush the counts (One moment of silence for all the data who disapeared.)
        self.counts_total = 0        
        
        # Reset the number of iterations
        self.iter = -1         
        
        # Update the label for the number of iteration
        self.iteration_label.set_text('Iteration reseted')          
        
        # Note that it is resetted
        self.is_reseted = True
        

    def run_loops(self):
        """
        Perform the loops of the fpga has long as the conditions are met. 
        """
        _debug('GuiMainPulseSequence: run_loops')
        # Rewrite the data in the FPGA, in case they were changed by an other 
        # gui (example: the optimizer between loops)
        # Send the data_array to the FPGA and prepare it
        self.fpga.prepare_pulse(self.data_array) 
        
        # Specify the counting mode again
        self.fpga.set_counting_mode(self.CET_mode)

        condition_loop = True
        while condition_loop:
            self.iter += 1
            # Update the label for the number of iteration
            self.iteration_label.set_text('Iteration %d'%self.iter)
            _debug('GuiMainPulseSequence: run_loops %d/%d'%(self.iter, self.N_loopFPGA))
            self.fpga.run_pulse() 

            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events()    
            
            # Get the counts and proceed
            self.counts = self.fpga.get_counts()
            self.after_one_loop(self.counts, self.iter, self.rep) # This is a dummy function that should be overidden somewhere else. 

            # Note that the data are no longer reseted
            self.is_reseted = False
            
            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events()    
            # Update the condition for the while loop
            condition_loop = (self.iter<self.N_loopFPGA) and self.is_running    
            
            # Call the function for optimizing if the condition is met
            # Note that the condition is not meet if N=0. Clever. 
            if self.Nloop_before_optimize>0:
                if self.iter%self.Nloop_before_optimize == self.Nloop_before_optimize-1:
                    print('Cotton Wouate')
                    self.event_optimize()
        
        # Loop ended.         
        # Update the buttons
        if self.is_running:
            # Click on stop if it is still running
            self.button_start_clicked()            
        

    def after_one_loop(self, counts, iteration, rep):
        """
        DUmmy function to be overrid

        This is called after each loop (single run) of the fpga. 
        
        counts:
            Array of counts that the fpga get. 
        iteration:
            int corresponding to which iteration are we at
            
        rep:
            Number of repetition of the sequence into the fpga instruction
            """
        _debug('GuiMainPulseSequence: after_one_loop')
        

#        
        
    def show_fpga_data(self):
        """
        Pop up a window showing the pulses from the fpga data
        """
        _debug('GuiMainPulseSequence: show_sequence')
        
        # Show the GUI
        GUIFPGAInstruction(self.data_array, self.rep, self.length_data_block_s)
        
    def event_optimize(self):
        """
        Dummy function that is meant to be overrid. 
        It gets call whenenver we want to re-optimize the x-y-z positions. 
        """
        return
        


class GUIPulseBuilder(egg.gui.Window):
    """
    GUI for building and viewing the pulse sequence
    
    """
    def __init__(self, name="Pulse Sequence", size=[1200,700]): 
        """
        Initialize 
        """    
        _debug('GUIPulseBuilder:__init__')
        _debug('Be a fruitloop in a world of Cheerios.')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Initialise the GUI
        self.initialize_GUI()
        
        # Initiate a simple pulse sequence
        self.set_sequence( PredefinedSequence().get_sequence('pulse_simple') )
        
        # Initiate the table 
        self.block_index_changed()           
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIPulseBuilder: initialize_GUI')
            
        # Place the show_sequence button and connect it
        self.button_show_sequence = self.place_object(egg.gui.Button("Show sequence"))
        self.connect(self.button_show_sequence.signal_clicked, self.button_show_sequence_clicked)          
        
        # Place a qt SpinBox for the repetition
        self.new_autorow()
        self.place_object(egg.gui.Label('Repetion of \nsequence')) #Set the label at position (0,0)
        self.NumberBox_repetition = egg.gui.NumberBox(value=1000, step=1, 
                                                      bounds=(0, None), int=True)
        self.place_object(self.NumberBox_repetition, alignment=1)
        self.connect(self.NumberBox_repetition.signal_changed, self.NumberBox_repetition_changed)
        self.NumberBox_repetition_changed() # Initialize the value
        
        # Place a qt SpinBox for setting which block to see
        self.place_object(egg.gui.Label('Block index'), 2,0) #Set the label at position (0,0)
        self.block_index_NumberBox = egg.gui.NumberBox(value=0, step=1, 
                                                      bounds=(0, None), int=True)
        self.place_object(self.block_index_NumberBox, 3,0, alignment=1)
        self.connect(self.block_index_NumberBox.signal_changed, self.block_index_changed)
        
        # A button for setting the delays
        self.sequence_has_delay = False # This will be true if the sequence contain delays, false otherwise
        self.button_set_delays = egg.gui.Button('Set the delays', tip='Set/remove the delays into the sequence.\nRemove and set again for updating new values.')
        self.button_set_delays.set_style('background-color: rgb(255, 155, 255);')         
        self.place_object(self.button_set_delays, row=3, column=0)
        self.connect(self.button_set_delays.signal_clicked, self.button_set_delays_clicked)             

        # Prepare the list of delays for pulse
        #Place the AOs with tree dictionary
        self.treeDict_delays  = egg.gui.TreeDictionary(autosettings_path='setting_DIOs_delays')
        self.place_object(self.treeDict_delays, 
                          row=4, column=0, column_span=2)   
        for i in range(8):
            # NOTE: I limited up to DIO7, just to have a smaller dictionary tree, but it can go up to DIO15
            key = 'Delay_raise_DIO%d'%i
            self.treeDict_delays.add_parameter(key, 0, 
                                               type='float', step=0.01, 
                                               bounds=[None,None], suffix=' us',
                                               tip='Time delay for the raise time of DIO%d'%i)        
        for i in range(8):
            # NOTE: I limited up to DIO7, just to have a smaller dictionary tree, but it can go up to DIO15
            key = 'Delay_fall_DIO%d'%i
            self.treeDict_delays.add_parameter(key, 0, 
                                               type='float', step=0.01, 
                                               bounds=[None,None], suffix=' us',
                                               tip='Time delay for the fall time of DIO%d'%i)          
        
        # Place a Table for showing the sequence
        self.block_table = egg.gui.Table()
        self.place_object(self.block_table, 2,1, row_span=4, column_span=10, alignment=0)    
        self.set_column_stretch(2, 10)

    def button_show_sequence_clicked(self):
        """
        Pop up a window for showing the pulse sequence
        """
        _debug('GUIPulseBuilder: button_show_sequence_clicked') 
        
        # Show the block
        GUIPulsePattern(self.sequence)    

    def button_set_delays_clicked(self):
        """
        Add the delays in the sequence
        """
        _debug('GUIPulseBuilder: button_set_delays_clicked') 
        
        # Put the delays only if the sequence do not contain them
        if not(self.sequence_has_delay):
            
            # Keepin memory the sequence with no delay
            self.sequence_no_delay = self.sequence
            
            # Extract the raise delays
            delays_raise = []
            DIOs = []
            for i in range(8):
                DIOs.append(i)
                delays_raise.append( self.treeDict_delays['Delay_raise_DIO%d'%i])
            # Set the raise delay
            new_sequence = pulses.add_raise_delays(self.sequence, DIOs, delays_raise)
    
            # Extract the fall delays
            delays_fall = []
            DIOs = []
            for i in range(8):
                DIOs.append(i)
                delays_fall.append( self.treeDict_delays['Delay_fall_DIO%d'%i])
            # Set the fall delay
            new_sequence = pulses.add_fall_delays(new_sequence, DIOs, delays_fall)   
            
            # Set the sequence to be this one
            self.set_sequence(new_sequence)
            # Note that the sequence has delay
            self.sequence_has_delay = True
            
            #Adjust the button 
            self.button_set_delays.set_text('Remove the delays')
            self.button_set_delays.set_style('background-color: rgb(255, 155, 0);')  
            
        else:
            # Set the sequence with no delay
            self.set_sequence(self.sequence_no_delay)
            # Note that the sequence has NO delay
            self.sequence_has_delay = False
            #Adjust the button 
            self.button_set_delays.set_text('Set the delays')
            self.button_set_delays.set_style('background-color: rgb(255, 155, 255);')              
        
        
        
    def block_index_changed(self):
        """
        What to do when the index for the lbock shown changes.
        """
        # Set the blox index, plus change the block information
        self.block_ind = self.block_index_NumberBox.get_value()
        
        
        
        self.block = self.sequence.get_block_s()[self.block_ind]
        self.nb_channel_event = self.block.get_nb_channel_events()
        self.pulse_pattern = self.block.get_pulse_pattern()  
        _debug('GUIPulseBuilder: block_index_changed: ', self.block_ind)
        
        #Fill the table
        self.fill_block_table()
        
        
    
    def fill_block_table(self):
        """
        Fill up the table with the block information. 
        
        """
        _debug('GUIPulseBuilder: fill_block_table ')
        
        #First destroy the previous table
        while (self.block_table.get_column_count() > 0):
            self.block_table._widget.removeColumn(0)   
        #TODO also loop over the remaining rows to delete them

        #Then input the new one. 
        self.block_table.set_value(column=0, row=0, value='Name')
        self.block_table.set_value(column=1, row=0, value='Channel')
        self.block_table.set_value(column=2, row=0, value='Times')
        for i in range(self.nb_channel_event ):
            self.channel_event = self.pulse_pattern[i]
            #Extract the name
            name = self.channel_event.get_name()
            self.block_table.set_value(column=0, row=i+1, value=name)
            #Extract the channel
            channel = self.channel_event.get_channel()
            self.block_table.set_value(column=1, row=i+1, value=channel)
            #Extract the raise and fall time
            times = self.channel_event.get_pulses_times()
            for j,t in enumerate(times):
                self.block_table.set_value(column=j+2, row=i+1, value=t)   
                

    def NumberBox_repetition_changed(self):
        """
        What to do when the repetition number changes.
        """                
        self.repetition = self.NumberBox_repetition.get_value()
        _debug('GUIPulseBuilder: NumberBox_repetition_changed: ', self.repetition)
        
    def set_sequence(self, sequence):
        """
        Set the sequence to sequence. 
        
        sequence:
            Sequence object. 
        """
        _debug('GUIPulseBuilder: set_sequence')
        
        # Take the input sequence has the official sequence
        self.sequence = sequence
        
        
        self.nb_block = self.sequence.get_nb_block()
        
        # Update attributes and sub guis
        self.nb_block = self.sequence.get_nb_block() 
        # Set the maximum number for the number box widget
        self.block_index_NumberBox._widget.setMaximum(self.nb_block-1) 
        # Update the table
        self.block_index_changed()  

        _debug('GUIPulseBuilder: set_sequence: name = '+self.sequence.get_name())            
               
    
    def get_sequence(self):
        """
        Return the single sequence
        """
        return self.sequence
    
    def get_repetition(self):
        """
        Return the number of repetition of the single pulse sequence
        """
        return self.repetition  
    
    def get_nb_block(self):
        """
        Return the the number of block inside a single pulse sequence
        """
        return self.nb_block     
      

class GUIPredefined(egg.gui.Window):
    """
    GUI for managing predefined sequence for test
    """
    
    def __init__(self, fpga,  name="Counts", size=[700,500]): 
        """
        fpga:
            "FPGA_api" object from fpga_control.py. 
            This is the object shared amoung the GUIs for controlling the fpga. 
            The session of the fpga must already be open.

        """    
        _debug('GUIPredefined:__init__')
        _debug('The best way to predict your future is to create it. – Abraham Lincoln')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Take possession of the GUIs. Mouahahaha...
        self.fpga = fpga
        
        # Initialise the GUI
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIPredefined: initialize_GUI')

        # A button for preparing stuff
        self.button_prepare_experiment = egg.gui.Button('Prepare',
                                                        tip='Prepare the measurement before running')
        self.place_object(self.button_prepare_experiment)
        self.connect(self.button_prepare_experiment.signal_clicked, 
                     self.button_prepare_experiment_clicked)
        
        self.new_autorow()            
        # Place a combobox with predefined sequence
        self.place_object(egg.gui.Label('Predefined\nSequence ')) #Set the label at position (0,0)
        self.pred_seq = PredefinedSequence() # This object gives access to all predefined sequence
        self.seq_list = self.pred_seq.get_sequence_list()
        self.seq_list_comboxBox = self.place_object( egg.gui.ComboBox(self.seq_list),alignment=1)
        
        
        # Add a Data Box plotter for the incoming data
        self.databoxplot = egg.gui.DataboxPlot(autosettings_path='plot_predefined')
        self.place_object(self.databoxplot, row=2, column = 2, row_span=2) 
        self.databoxplot.button_multi.set_value(False) # Make all on the same plot
        
    def button_prepare_experiment_clicked(self):
        """
        Prepare the experiment:
        """
        _debug('GUIPredefined: button_prepare_experiment_clicked')   
        
        # Prepare
        self.prepare_pulse_sequence()
        # Extract some info for the plots
        self.nb_block  = self.sequence.get_nb_block()
        self.x_axis = np.linspace(1, self.nb_block, self.nb_block)
        
        # Trigger a dummy function for signaling to prepare stuffs
        self.event_prepare_experiment()

    def prepare_pulse_sequence(self):
        """
        Prepare the pulse sequence for the ESR. 
        It generates the objet to be converted into a data array. 
        """
        _debug('GUIPredefined: set_predefined_seq')
        
        # Get the sequence
        # Get the index of the combox Box
        ind = self.seq_list_comboxBox.get_index()
        model = self.seq_list[ind]
        self.sequence = self.pred_seq.get_sequence(model) 
        
        # Call the preparation of the experiment
        self.event_prepare_experiment()
        
    def plot_empty_counts(self, *a):
        """
        Plot something cool
        """
        _debug('GUIPredefined: plot_empty_counts')
        # Clear the plot
        self.databoxplot_count.clear()      

        # Show a rose for now, for fun ! :D 
        # Make rose
        tt = np.linspace(0, 100, 100)
        x = tt*np.cos(tt) 
        y = tt*np.sin(tt) 
        
        self.databoxplot_count.append_data_point([x, y],
                                             ['Fake x axis', 'Fake y axis']).plot()    
        tt = np.linspace(0, 50, 200)
        x = tt*np.cos(tt*2) 
        y = tt*np.sin(tt*2) 
        self.databoxplot_count.append_data_point([x, y],
                                             ['Fake x axis', 'Fake y axis']).plot()          
    
    def databoxplot_update(self):
        """
        Update the plot
        """
        _debug('GUIPredefined: databoxplot_update')

        # Plot counts only if the sequence generates count
        if len(self.counts_total)>0:          
            # Clear the plot
            self.databoxplot.clear() 
            
            self.databoxplot['Block_index'] = self.x_axis
            # Loop over each readout 
            for i, count_per_readout in enumerate(self.counts_total):
                # Add a curve
                self.databoxplot['Total_counts_%d'%i] = count_per_readout
                # Show it
                self.databoxplot.plot() 
            
        else:
            self.plot_empty_counts()
        
    
        
    def after_one_loop(self, counts, iteration, rep):
        """
        What to do after one loop of the fpga. 

        This is called after each loop (single run) of the fpga. 
        
        counts:
            Array of counts that the fpga get. 
        iteration:
            int corresponding to which iteration are we at
            
        rep:
            Number of repetition of the sequence into the fpga instruction
            """
        _debug('GUIPredefined: after_one_loop')
        
        self.count_processor = _fc.ProcessFPGACounts(counts)
        self.block_ind, self.counts = self.count_processor.get_count_per_readout_vs_block(rep, self.nb_block)
#        self.fpga.get_count_per_readout_vs_block(self.rep, self.nb_block)  

#        print(self.counts)
        # If its the first iteration
        if iteration == 0:
            # Get the count and the correct shape for the array
            self.counts_total = np.array(self.counts)  
        else:
            # Increment the counts
            self.counts_total += np.array(self.counts)
            
        # Update the plot
        self.databoxplot_update()
              
        
    def event_prepare_experiment(self): 
        """
        Dummy function to be overrid
        This is was should be done after that the pulse sequence is defined. 
        """        
        return 
        
 
class GUIESR(egg.gui.Window):
    """
    GUI for preparing the pulse sequence for an ESR measurement.    
    TODO: implement an alternative method where the frequency are sweep normally 
    and the counts are monitored. 
    """
    
    def __init__(self, name="ESR", size=[1000,500]): 
        """
        Initialize
        """    
        _debug('GuiESRs:__init__')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Initialise the GUI
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIESR: initialize_GUI')
        _debug('If you fall – I’ll be there. – Floor')
        
        # A button for preparing stuff
        self.button_prepare_experiment = egg.gui.Button('Prepare',
                                                        tip='Prepare the measurement before running')
        self.place_object(self.button_prepare_experiment, row=1, column=0)
        self.connect(self.button_prepare_experiment.signal_clicked, 
                     self.button_prepare_experiment_clicked)
            
        # tree dictionnarry for the settings
        self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_ESR_pulse')
        self.place_object(self.treeDic_settings, row=2, column=0)

        self.treeDic_settings.add_parameter('Power', -20, 
                                            type='float', step=0.01, 
                                            bounds=[-50,30], suffix=' dBm',
                                            tip='Constant power of the RF')
        self.treeDic_settings.add_parameter('f_min', 1, 
                                            type='float', step=0.1, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Minimum frequency to sweep')
        self.treeDic_settings.add_parameter('f_max', 1, 
                                            type='float', step=0.1, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Maximum frequency to sweep')        
        self.treeDic_settings.add_parameter('N', 200, 
                                            type='int', step=10, 
                                            bounds=[0,None],
                                            tip='Number of points to sweep')         
        
        self.treeDic_settings.add_parameter('dt_off', 5000, 
                                            type='float', step=100, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of the initial off state') 
        self.treeDic_settings.add_parameter('dt_on', 5000, 
                                            type='float', step=100, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of the on state: read, shine the laser, send RF, modulate') 
        self.treeDic_settings.add_parameter('dt_delay_laser', 500, 
                                            type='float', step=10, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Delay to start the laser before the ON state')         
        
        self.treeDic_settings.add_parameter('DIO_laser', 2, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for the laser')         
        self.treeDic_settings.add_parameter('DIO_change_frequency', 7, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for triggering the change in frequency')  
        self.treeDic_settings.add_parameter('DIO_pulse_modulation', 3, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for modulating the pulse')  
        self.treeDic_settings.add_parameter('DIO_sync_scope', 5, 
                                            type='int', step=1, 
                                            bounds=[-1,16],
                                            tip='DIO for synchronizing the oscilloscope. Put -1 for nothing')
        
        # Add a Data Box plotter for the incoming data
        self.databoxplot = egg.gui.DataboxPlot(autosettings_path='plot_ESR')
        self.place_object(self.databoxplot, row=2, column = 1, row_span=2) 
        self.databoxplot.button_multi.set_value(False) # Make all on the same plot
        

    def button_prepare_experiment_clicked(self):
        """
        Prepare the experiment:
            Prepare the pulse sequence in the fpga
            Prepare the signal generator
            Prepare the plot
        """
        _debug('GUIESR: button_prepare_experiment_clicked')   
        
        # Prepare
        self.prepare_pulse_sequence()
        
        # Get useful parameters for the plot
        self.fmin = self.treeDic_settings['f_min']
        self.fmax = self.treeDic_settings['f_max']       
        self.x_axis = np.linspace(self.fmin,self.fmax, self.nb_block)
        
        
        # Trigger a dummy function for signaling to prepare stuffs
        self.event_prepare_experiment()
        
        
    def prepare_pulse_sequence(self):
        """
        Prepare the pulse sequence. 
        It generates the objet to be converted into a data array. 
        """
        _debug('GUIESR: prepare_pulse_sequence')
        
        # Initiate the sequence on which we gonna construct the sequence
        sequence = Sequence(name='Awesome ESR')
        
        DIO_trigger = self.treeDic_settings['DIO_change_frequency']
        DIO_laser   = self.treeDic_settings['DIO_laser']
        DIO_PM      = self.treeDic_settings['DIO_pulse_modulation']
        DIO_sync    = self.treeDic_settings['DIO_sync_scope']
        
        dt_off = self.treeDic_settings['dt_off']
        dt_on  = self.treeDic_settings['dt_on']
        dt_in_laser = self.treeDic_settings['dt_delay_laser']
        
        self.nb_block = self.treeDic_settings['N']
        
        dt_trigger = 100 # Elapsed time for the trigger
        
        
        t0_read = dt_off  # Start time to read (us)
        t1_read = dt_off + dt_on # Stop time to read (us)
        
        # Create a channel for the trigger
        channel_trigger_RF = ChannelPulses(channel=DIO_trigger, 
                                           name='Change Frequency')
        channel_trigger_RF.add_pulses([t1_read+1, t1_read+dt_trigger])

        # Create the ChannePulse for when to read
        channel_read = ChannelPulses(channel=1, name='Read')      
        channel_read.add_pulses([t0_read, t1_read])

        # A Channel for the modulation of the pulse
        channel_PM = ChannelPulses(channel=DIO_PM, name='Pulse modulation')      
        channel_PM.add_pulses([t0_read, t1_read])
        
        # Create the ChannePulse for the laser output
        channel_laser = ChannelPulses(channel=DIO_laser, name='Laser')      
        channel_laser.add_pulses([t0_read-dt_in_laser , t1_read])   
        
        # Create a channel for the end state (use full for the scope)
        channel_sync = ChannelPulses(channel=DIO_sync, name='Synchronize scope')
        channel_sync.add_pulses([t1_read+1, t1_read+dt_trigger]) # Same duration as trigger
        
        # Create many block of the same thing. 
        for i in range(self.nb_block):
            # Build the block
            block = PulsePatternBlock(name='Block %d'%i)
            block.add_channelEvents([channel_read, 
                                     channel_trigger_RF, 
                                     channel_laser,
                                     channel_PM,
                                     channel_sync])
            # Add the block to the sequence
            sequence.add_block(block)
        
        self.sequence = sequence       

    def databoxplot_update(self):
        """
        Update the plot
        """
        _debug('GUIESR: databoxplot_update')
        # CLear the plot
        self.databoxplot.clear() 
                
        self.databoxplot['Frequency_(GHz)'] = self.x_axis
        # Loop over each readout 
        for i, count_per_readout in enumerate(self.counts_total):
            # Add a curve
            self.databoxplot['Total_counts_%d'%i] = count_per_readout

            
        # Show it
        self.databoxplot.plot()      
        
    def after_one_loop(self, counts, iteration, rep):
        """
        What to do after one loop of the fpga. 

        This is called after each loop (single run) of the fpga. 
        
        counts:
            Array of counts that the fpga get. 
        iteration:
            int corresponding to which iteration are we at
            
        rep:
            Number of repetition of the sequence into the fpga instruction
            """
        _debug('GUIESR: after_one_loop')
        
        # Get the counts per readout per block
        self.count_processor = _fc.ProcessFPGACounts(counts)
        self.block_ind, self.counts = self.count_processor.get_count_per_readout_vs_block(rep, self.nb_block)
#        self.fpga.get_count_per_readout_vs_block(self.rep, self.nb_block)  

#        print(self.counts)
        # If its the first iteration
        if iteration == 0:
            # Get the count and the correct shape for the array
            self.counts_total = np.array(self.counts)  
        else:
            # Increment the counts
            self.counts_total += np.array(self.counts)  
            
        # Update the plot
        self.databoxplot_update()
        
    def event_prepare_experiment(self): 
        """
        Dummy function to be overrid
        This is was should be done after that the pulse sequence is defined. 
        """        
        return 
        

class GUIRabi(egg.gui.Window):
    """
    GUI for preparing the pulse sequence for a Rabi measurement. 
    
    """
    
    def __init__(self, name="Rabi", size=[1000,500]): 
        """
        Initialize
        """    
        _debug('GGUIRabi:__init__')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Initialise the GUI
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIRabi: initialize_GUI')
        _debug('If you think you’re too small to make a difference, try sleeping with a mosquito. – Dalai Lama')
        
        # A button for preparing stuff
        self.button_prepare_experiment = egg.gui.Button('Prepare',
                                                        tip='Prepare the measurement before running')
        self.place_object(self.button_prepare_experiment, row=1, column=0)
        self.connect(self.button_prepare_experiment.signal_clicked, 
                     self.button_prepare_experiment_clicked)
            
        # A button for preparing stuff
        self.button_reset = egg.gui.Button('Reset counts',
                                                        tip='Reset the array of counts')
        self.place_object(self.button_reset, row=1, column=1)
        self.connect(self.button_reset.signal_clicked, 
                     self.button_reset_clicked)
        
        # tree dictionnarry for the settings
        self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_Rabi_pulse')
        self.place_object(self.treeDic_settings, row=2, column=0, column_span=2)

        self.treeDic_settings.add_parameter('Power', -20, 
                                            type='float', step=0.01, 
                                            bounds=[-50,30], suffix=' dBm',
                                            tip='Constant power of the RF')
        self.treeDic_settings.add_parameter('Frequency', 1, 
                                            type='float', step=0.0001, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Frequency of the RF')        
        self.treeDic_settings.add_parameter('N', 50, 
                                            type='int', step=10, 
                                            bounds=[0,None],
                                            tip='Number of points to sweep')         
        
        self.treeDic_settings.add_parameter('dt_readout', 0.4, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of the readout') 
        self.treeDic_settings.add_parameter('t_in', 0, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Initialie time to probe') 
        self.treeDic_settings.add_parameter('t_end', 1, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Last time to probe')         
        self.treeDic_settings.add_parameter('dt_read_after_RF', 1, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='How much time to wait before reading after the RF') 
        self.treeDic_settings.add_parameter('delay_read_before_laser', 0.05, 
                                            type='float', step=0.01, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Delay that we read before shining the laser')  
    
        
        self.treeDic_settings.add_parameter('DIO_laser', 2, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for the laser')          
        self.treeDic_settings.add_parameter('DIO_pulse_modulation', 3, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for modulating the pulse')  
        self.treeDic_settings.add_parameter('DIO_sync_scope', 5, 
                                            type='int', step=1, 
                                            bounds=[-1,16],
                                            tip='DIO for synchronizing the oscilloscope. Put -1 for nothing')             
        
        

        
        # Add a Data Box plotter for the incoming data
        self.databoxplot = egg.gui.DataboxPlot(autosettings_path='plot_Rabi')
        self.place_object(self.databoxplot, row=2, column = 2, row_span=2) 
        self.databoxplot.button_multi.set_value(False) # Make all on the same plot
        

    def button_prepare_experiment_clicked(self):
        """
        Prepare the experiment:
            Prepare the pulse sequence in the fpga
            Prepare the signal generator
            Prepare the plot
        """
        _debug('GUIRabi: button_prepare_experiment_clicked')   
        
        # Prepare
        self.prepare_pulse_sequence()
        
        # Trigger a dummy function for signaling to prepare stuffs
        self.event_prepare_experiment()

    def button_reset_clicked(self):
        """
        Reset the total counts. 
        """
        self.counts_total = np.zeros(np.shape(self.counts_total))
        
    def prepare_pulse_sequence(self):
        """
        Prepare the pulse sequence. 
        It generates the objet to be converted into a data array. 
        """
        _debug('GUIRabi: prepare_pulse_sequence')
        
        # Initiate the sequence on which we gonna construct the  sequence
        sequence = Sequence(name='Wonderful Rabi')
        
        DIO_laser   = self.treeDic_settings['DIO_laser']
        DIO_PM      = self.treeDic_settings['DIO_pulse_modulation']
        DIO_sync    = self.treeDic_settings['DIO_sync_scope']
        
        
        T_min_us    = self.treeDic_settings['t_in'] # Minimum time  to probe
        T_max_us    = self.treeDic_settings['t_end'] # Maximum time  to probe
        self.nb_block    = self.treeDic_settings['N'] # Number of point to take
        dt_readout  = self.treeDic_settings['dt_readout'] # Readout time (us)
        delay_read = self.treeDic_settings['delay_read_before_laser'] # Delay (us) that we read before shining the laser
        dt_read_after_RF = self.treeDic_settings['dt_read_after_RF'] # How long to wait before reading after the RF (us)
        
        # Define the time durations of the RF
        self.dt_s = np.linspace(T_min_us, T_max_us, self.nb_block)
      
        t_ini_laser_init = 1  # Raise time for the initialization laser (us)
        dt_laser_init = 1 # Time duration of the initializaiton laser (us)
        t0_RF = t_ini_laser_init + dt_laser_init + 1 # Initial raise time for the RF (us)   
        
        
#        t0_ref = 0.1 #Initial time for the reference
#        t0_RF = t0_ref + 2*dt_readout # Initial raise time for the RF
        
        # Initiate the sequence on which we gonna construct the Rabi sequence
        sequence = Sequence(name='Rabi sequence')        
        
        # Initiate the channels
        
        # Create a channel for synching the scope
        channel_sync = ChannelPulses(channel=DIO_sync, name='Sync with scope')
        channel_sync.add_pulses([0, 0.5]) # At the beggining
        
        
        # Define a block for each duration to probe
        for i, dt in enumerate(self.dt_s):
            
            # Initialize the state into ms=0 with the green laser
            # Channel for the laser output, which follows the readout
            channel_laser = ChannelPulses(channel=DIO_laser, name='Laser') 

            #Add a pulse for the initialization into ms=0
            channel_laser.add_pulses([t_ini_laser_init, t_ini_laser_init+dt_laser_init])            

            # Channel for the modulatiion of the RF
            channel_RF_mod = ChannelPulses(channel=DIO_PM, name='RF modulation')
            # The RF span from time zero to the duration
            channel_RF_mod.add_pulses([t0_RF, t0_RF+dt])
            
            # Channel for the readout
            channel_read = ChannelPulses(channel=1, name='Read') 
            
            # Add a pulse for the readout after the RF
            t0_read = t0_RF+dt+dt_read_after_RF
            # Add a delay at the beggining, before that the laser is shone, just to be cool. 
            channel_read.add_pulses([t0_read-delay_read, t0_read+ dt_readout])
            
            # Add a pulse for shining the NV for both readind ans initialting into ms=0
            t0_shine = t0_read
            channel_laser.add_pulses([t0_shine, t0_shine + dt_laser_init ])              

            # Add a pulse for reading the reference
            t0_read = t0_shine + dt_laser_init-dt_readout
            channel_read.add_pulses([t0_read, t0_read+dt_readout]) 
          
            # Build the block
            block = PulsePatternBlock(name='Block Rabi RF = %.2f us'%dt)
            block.add_channelEvents([channel_sync,
                                     channel_RF_mod,
                                     channel_read ,
                                     channel_laser])
            # Add the block to the sequence
            sequence.add_block(block)

        
# This is the previous pulse sequence
# TODO Allow the user to choose
#        # Define a block for each duration to probe
#        for i, dt in enumerate(dt_s):
#
#            # Channel for the modulatiion of the RF
#            channel_RF_mod = ChannelPulses(channel=DIO_PM, name='RF modulation')
#            # The RF span from time zero to the duration
#            channel_RF_mod.add_pulses([t0_RF, t0_RF+dt])
#            
#            # Channel for the readout
#            channel_read = ChannelPulses(channel=1, name='Read') 
#            # Add a pulse for the reference
#            channel_read.add_pulses([t0_ref,t0_ref+ dt_readout, ])
#            # Add a pulse for the readout after the RF
#            t_read = t0_RF+dt
#            channel_read.add_pulses([t_read, t_read+ dt_readout, ])
#            
#            # Channel for the laser output, which follows the readout
#            channel_laser = ChannelPulses(channel=DIO_laser, name='Laser') 
#            # Add a pulse for the reference
#            channel_laser.add_pulses([t0_ref-delay_laser,t0_ref+ dt_readout, ])
#            # Add a pulse for the readout after the RF
#            t_read = t0_RF+dt
#            channel_laser.add_pulses([t_read-delay_laser, t_read+ dt_readout, ])            
#
#            # Build the block
#            block = PulsePatternBlock(name='Block Rabi RF = %.2f us'%dt)
#            block.add_channelEvents([channel_sync,
#                                     channel_RF_mod,
#                                     channel_read ,
#                                     channel_laser])
#            # Add the block to the sequence
#            sequence.add_block(block)
        
        self.sequence = sequence          

    def databoxplot_update(self):
        """
        Update the plot
        """
        _debug('GUIRabi: databoxplot_update')
        # CLear the plot
        self.databoxplot.clear() 
                
        self.databoxplot['Time_(us)'] = self.dt_s
        # Loop over each readout 
        for i, count_per_readout in enumerate(self.counts_total):
            # Add a curve
            self.databoxplot['Total_counts_%d'%i] = count_per_readout
            
        # Show it
        self.databoxplot.plot()   
        
    def after_one_loop(self, counts, iteration, rep):
        """
        What to do after one loop of the fpga. 

        This is called after each loop (single run) of the fpga. 
        
        counts:
            Array of counts that the fpga get. 
        iteration:
            int corresponding to which iteration are we at
            
        rep:
            Number of repetition of the sequence into the fpga instruction
            """
        _debug('GUIRabi: after_one_loop')
        
        # Get the counts per readout per block
        self.count_processor = _fc.ProcessFPGACounts(counts)
        self.block_ind, self.counts = self.count_processor.get_count_per_readout_vs_block(rep, self.nb_block)
        # If its the first iteration
        if iteration == 0:
            # Get the count and the correct shape for the array
            self.counts_total = np.array(self.counts)  
        else:
            # Increment the counts
            self.counts_total += np.array(self.counts)  
            
        # Update the plot
        self.databoxplot_update()
        
    def event_prepare_experiment(self): 
        """
        Dummy function to be overrid
        This is was should be done after that the pulse sequence is defined. 
        """        
        return         


      


class GUIRabiPower(egg.gui.Window):
    """
    GUI for the pulse sequence of Rabi of Count VS power 
    """
    
    def __init__(self, name="Rabi power !", size=[1000,500]): 
        """
        Initialize
        """    
        _debug('GUIRabiPower:__init__')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Initialise the GUI
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIRabiPower: initialize_GUI')
        _debug('And, when you want something, all the universe conspires in helping you to achieve it. ― Paulo Coelho, The Alchemist')

        # A button for preparing stuff
        self.button_prepare_experiment = egg.gui.Button('Prepare',
                                                        tip='Prepare the measurement before running')
        self.place_object(self.button_prepare_experiment, row=1, column=0)
        self.connect(self.button_prepare_experiment.signal_clicked, 
                     self.button_prepare_experiment_clicked)
        
        # tree dictionnarry for the settings
        self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_Rabi_pulse')
        self.place_object(self.treeDic_settings, row=2, column=0)

        self.treeDic_settings.add_parameter('dt_pulse', 3/120, 
                                            type='float', step=1/120, 
                                            bounds=[0, None], suffix=' us',
                                            tip='Duration of the pi-pulse')
        self.treeDic_settings.add_parameter('Frequency', 1, 
                                            type='float', step=0.0001, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Frequency of the RF')        
        self.treeDic_settings.add_parameter('N', 50, 
                                            type='int', step=10, 
                                            bounds=[0,None],
                                            tip='Number of points to sweep')         

        self.treeDic_settings.add_parameter('P_min', -20, 
                                            type='float', step=0.1, 
                                            bounds=[-50,30], suffix=' dBm',
                                            tip='Minimum power') 
        self.treeDic_settings.add_parameter('P_max', -10, 
                                            type='float', step=0.1, 
                                            bounds=[-50,30], suffix=' dBm',
                                            tip='Maximum power')  
        
        self.treeDic_settings.add_parameter('dt_readout', 0.4, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of the readout') 
       
        self.treeDic_settings.add_parameter('dt_read_after_RF', 1, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='How much time to wait before reading after the RF') 
        self.treeDic_settings.add_parameter('delay_read_before_laser', 0.05, 
                                            type='float', step=0.01, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Delay that we read before shining the laser')  

        self.treeDic_settings.add_parameter('delay_switch_list', 100, 
                                            type='float', step=0.01, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Delay that it takes for the signal generator to swicth list element.')          
        
        self.treeDic_settings.add_parameter('DIO_laser', 2, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for the laser')          
        self.treeDic_settings.add_parameter('DIO_pulse_modulation', 3, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for modulating the pulse')  
        self.treeDic_settings.add_parameter('DIO_change_power', 7, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for triggering the change in power')  
        self.treeDic_settings.add_parameter('DIO_sync_scope', 5, 
                                            type='int', step=1, 
                                            bounds=[-1,16],
                                            tip='DIO for synchronizing the oscilloscope. Put -1 for nothing')  
        
        # Add a Data Box plotter for the incoming data
        self.databoxplot = egg.gui.DataboxPlot(autosettings_path='plot_Rabi_power')
        self.place_object(self.databoxplot, row=2, column = 1, row_span=2) 
        self.databoxplot.button_multi.set_value(False) # Make all on the same plot
        

    def button_prepare_experiment_clicked(self):
        """
        Prepare the experiment:
            Prepare the pulse sequence in the fpga
            Prepare the signal generator
            Prepare the plot
        """
        _debug('GUIRabiPower: button_prepare_experiment_clicked')   
        
        # Prepare
#        self.prepare_pulse_sequence_v1()
        self.prepare_pulse_sequence_v2()
        
        
        self.pmin = self.treeDic_settings['P_min']
        self.pmax = self.treeDic_settings['P_max']
        self.x_axis = np.linspace(self.pmin, self.pmax, self.nb_block)
        
        # Trigger a dummy function for signaling to prepare stuffs
        self.event_prepare_experiment()
           
    def prepare_pulse_sequence_v1(self):
        """
        Prepare the pulse sequence. 
        It generates the objet to be converted into a data array. 
        """
        _debug('GUIRabiPower: prepare_pulse_sequence')
        
        DIO_trigger = self.treeDic_settings['DIO_change_power']
        DIO_laser   = self.treeDic_settings['DIO_laser']
        DIO_PM      = self.treeDic_settings['DIO_pulse_modulation']
        DIO_sync    = self.treeDic_settings['DIO_sync_scope']
        
        
        self.nb_block    = self.treeDic_settings['N'] # Number of point to take
        
        dt_readout  = self.treeDic_settings['dt_readout'] # Readout time (us)
        delay_read = self.treeDic_settings['delay_read_before_laser'] # Delay (us) that we read before shining the laser
        dt_read_after_RF = self.treeDic_settings['dt_read_after_RF'] # How long to wait before reading after the RF (us)
        
        # Define the time durations of the RF
        dt_RF = self.treeDic_settings['dt_pulse']
      
        t_ini_laser_init = 1  # Raise time for the initialization laser (us)
        dt_laser_init = 1 # Time duration of the initializaiton laser (us)
        t0_RF = t_ini_laser_init + dt_laser_init + 1 # Initial raise time for the RF (us)   
        
        dt_trigger = 1 # Elapsed time for the trigger
        
        
        
        # Initiate the sequence that we gonna construct
        sequence = Sequence(name='Rabi VS power')        
        
        # Initiate the channels
        # Create a channel for synching the scope
        channel_sync = ChannelPulses(channel=DIO_sync, name='Sync with scope')
        channel_sync.add_pulses([0, 0.5]) # At the beggining
        
        
        # Define a block for each duration to probe
        for i in range(self.nb_block):
            
            # Initialize the state into ms=0 with the green laser
            # Channel for the laser output, which follows the readout
            channel_laser = ChannelPulses(channel=DIO_laser, name='Laser') 

            #Add a pulse for the initialization into ms=0
            channel_laser.add_pulses([t_ini_laser_init, t_ini_laser_init+dt_laser_init])            

            # Channel for the modulatiion of the RF
            channel_RF_mod = ChannelPulses(channel=DIO_PM, name='RF modulation')
            # The RF span from time zero to the duration
            channel_RF_mod.add_pulses([t0_RF, t0_RF+dt_RF])
            
            # Channel for the readout
            channel_read = ChannelPulses(channel=1, name='Read') 
            
            # Add a pulse for the readout after the RF
            t0_read = t0_RF+dt_RF+dt_read_after_RF
            # Add a delay at the beggining, before that the laser is shone, just to be cool. 
            channel_read.add_pulses([t0_read-delay_read, t0_read+ dt_readout, ])
            
            # Add a pulse for shining the NV
            t0_shine = t0_read + delay_read
            channel_laser.add_pulses([t0_shine, t0_shine + dt_laser_init, ])              

            # Add a pulse for reading the reference
            t0_read = t0_shine + dt_laser_init-dt_readout
            channel_read.add_pulses([t0_read, t0_read+dt_readout-delay_read]) 
            
            # Add a pulse for switching the index in the signal generator
            channel_trig_sig = ChannelPulses(channel=DIO_trigger, name='Switch power')
            t0 = channel_read.get_pulses_times()[-1]
            channel_trig_sig.add_pulses([t0, t0+dt_trigger])
          
            # Build the block
            block = PulsePatternBlock(name='Block Rabi power #%d'%i)
            block.add_channelEvents([channel_sync,
                                     channel_RF_mod,
                                     channel_read ,
                                     channel_laser,
                                     channel_trig_sig])
            # Add the block to the sequence
            sequence.add_block(block)
            
        self.sequence = sequence 

     
    def prepare_pulse_sequence_v2(self):
        """
        Prepare the pulse sequence. 
        It generates the objet to be converted into a data array. 
        """
        _debug('GUIRabiPower: prepare_pulse_sequence_v2')
        
        DIO_trigger = self.treeDic_settings['DIO_change_power']
        DIO_laser   = self.treeDic_settings['DIO_laser']
        DIO_PM      = self.treeDic_settings['DIO_pulse_modulation']
        DIO_sync    = self.treeDic_settings['DIO_sync_scope']
           
        
        self.nb_block    = self.treeDic_settings['N'] # Number of point to take
        
        dt_readout        = self.treeDic_settings['dt_readout'] # Readout time (us)
        delay_read        = self.treeDic_settings['delay_read_before_laser'] # Delay (us) that we read before shining the laser
        dt_read_after_RF  = self.treeDic_settings['dt_read_after_RF'] # How long to wait before reading after the RF (us)
        dt_RF             = self.treeDic_settings['dt_pulse'] # Define the time durations of the RF
        delay_switch_list = self.treeDic_settings['delay_switch_list' ]
       
        
        
      
        t_ini_laser_init = 1  # Raise time for the initialization laser (us)
        dt_laser_init = 1 # Time duration of the initializaiton laser (us) 
        dt_trigger = 1 # Elapsed time for the trigger
        delay_before_RF = 0.5 # dead-time after the initialization in ms=0 and the pi pulse. 
    
        
        # Initiate the sequence that we gonna construct
        sequence = Sequence(name='Rabi VS power')        
               
        # Here we create the block that gonna be repeated for each power to scan

        # Initiate the channels
        # Channel for synching the scope
        # Channel for the laser output, which follows the readout
        # Channel for the modulatiion of the RF
        # Channel for the readout
        # Channel for switching power
        channel_sync     = ChannelPulses(channel=DIO_sync   , name='Sync with scope')
        channel_laser    = ChannelPulses(channel=DIO_laser  , name='Laser')         
        channel_RF_mod   = ChannelPulses(channel=DIO_PM     , name='RF modulation')
        channel_read     = ChannelPulses(channel=1          , name='Read') 
        channel_trig_sig = ChannelPulses(channel=DIO_trigger, name='Switch power')
        
        #Synch the oscilloscope at the beginning
        channel_sync.add_pulses([0, 0.5]) # At the beggining
                
        # First initiate the state into ms=0 with the green laser
        channel_laser.add_pulses([t_ini_laser_init, t_ini_laser_init+dt_laser_init])            

        # Now the state is ms=0

        # Repeat the same measurement until enough time elapsed for the 
        # signal generator to switch the element in the list. 
        tref =  channel_laser.get_pulses_times()[-1] # Get the reference time
        self.N_repeat_within_block = 0 # We will keep track of how many repetition there is.
        while tref <delay_switch_list:
            self.N_repeat_within_block += 1
            # Now the state is ms=0
            
            # Flip the state with a pi-pulse
            # The RF span from time zero to the duration
            tref = tref + delay_before_RF
            channel_RF_mod.add_pulses([tref, tref+dt_RF])
          
            # Add a pulse for the readout after the RF
            t0_read = channel_RF_mod.get_pulses_times()[-1] + dt_read_after_RF
            # Add a delay at the beggining, before that the laser is shone, just to be cool. 
            channel_read.add_pulses([t0_read-delay_read, t0_read+ dt_readout ])
            
            # Add a pulse for shining the NV and to initiate it
            t0_shine = t0_read
            channel_laser.add_pulses([t0_shine, t0_shine + dt_laser_init ])              
    
            # Add a pulse for reading the reference
            t0_read = channel_laser.get_pulses_times()[-1] - dt_readout
            channel_read.add_pulses([t0_read, t0_read+dt_readout]) 
            
            tref =  channel_laser.get_pulses_times()[-1]
       
        # At this time, enought time should have elasped to allow the switch of power
        # Add a pulse for switching the index in the signal generator
        t0 = channel_read.get_pulses_times()[-1]
        channel_trig_sig.add_pulses([t0, t0+dt_trigger])
           
        # Copy the block for each power to probe
        for i in range(self.nb_block):
            # Build the block
            block = PulsePatternBlock(name='Block Rabi power #%d'%i)
            block.add_channelEvents([channel_sync,
                                     channel_RF_mod,
                                     channel_read ,
                                     channel_laser,
                                     channel_trig_sig])
            # Add the block to the sequence
            sequence.add_block(block)
            
        self.sequence = sequence 
        
    def databoxplot_update(self):
        """
        Update the plot
        """
        _debug('GUIRabiPower: databoxplot_update')
        # CLear the plot
        self.databoxplot.clear() 
              
        _debug('GUIRabiPower: databoxplot_update cleared')
        
        self.databoxplot['Power_(dBm)'] = self.x_axis
        
        _debug('GUIRabiPower: databoxplot_update xaxis')
        
        # Loop over each readout 
        for i, count_per_readout in enumerate(self.counts_total):
            
            _debug('GUIRabiPower: databoxplot_update add1')
            
            # Add a curve
            self.databoxplot['Total_counts_%d'%i] = count_per_readout
            
            _debug('GUIRabiPower: databoxplot_update add2')
            
        # Show it
        self.databoxplot.plot()      
        
    def after_one_loop(self, counts, iteration, rep):
        """
        What to do after one loop of the fpga. 

        This is called after each loop (single run) of the fpga. 
        
        counts:
            Array of counts that the fpga get. 
        iteration:
            int corresponding to which iteration are we at
            
        rep:
            Number of repetition of the sequence into the fpga instruction
            """
        _debug('GUIRabiPower: after_one_loop')
        
        # Get the counts per readout per block
        # This is for V1
#        self.count_processor = _fc.ProcessFPGACounts(counts)
#        self.block_ind, self.counts = self.count_processor.get_count_per_readout_vs_block(rep, self.nb_block)

        # This is for V2
        self.count_processor = _fc.ProcessFPGACounts(counts)
        self.counts_per_block_s = self.count_processor.get_sum_count_per_block(rep, self.nb_block)
        
        self.count_0_s = []
        self.count_1_s = []
        for count_per_block in self.counts_per_block_s:
            # For each block, we have a repetion of reading the counts and reading the reference
            # So we want to sum the counts for each type of reading
            # The following magix lines split each 2 element of the array
            self.count_0 = np.sum( count_per_block[0:][::2] )
            self.count_1 = np.sum( count_per_block[1:][::2] )
            self.count_0_s.append(self.count_0)
            self.count_1_s.append(self.count_1)
    
        self.counts = [self.count_0_s, self.count_1_s]
        

#        print(self.counts)
        # If its the first iteration
        if iteration == 0:
            # Get the count and the correct shape for the array
            self.counts_total = np.array(self.counts)  
        else:
            # Increment the counts
            self.counts_total += np.array(self.counts)  
            
        # Update the plot
        self.databoxplot_update()
        
    def event_prepare_experiment(self): 
        """
        Dummy function to be overrid
        This is was should be done after that the pulse sequence is defined. 
        """        
        return 


class GUICalibration(egg.gui.Window):
    """
    GUI for setting the count in each tick mode. This would be useful for 
    calibrating the time delay in the wires. 
    """
    
    def __init__(self, name="Calibration", size=[1000,500]): 
        """
        Initialize
        """    
        _debug('GUICalibration:__init__')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Initialise the GUI
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUICalibration: initialize_GUI')
        _debug('If you can’t make a mistake you can’t make anything. – Marva Collin')
        
        # A button for preparing stuff
        self.button_prepare_experiment = egg.gui.Button('Prepare',
                                                        tip='Prepare the measurement before running')
        self.place_object(self.button_prepare_experiment, row=1, column=0)
        self.connect(self.button_prepare_experiment.signal_clicked, 
                     self.button_prepare_experiment_clicked)
            
        # tree dictionnarry for the settings
        self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_pulse_calibration')
        self.place_object(self.treeDic_settings, row=2, column=0)    
        

        self.treeDic_settings.add_parameter('t_read_start', 0, 
                                            type='float', step=0.1, 
                                            bounds=[0, None], suffix=' us',
                                            tip='Time at which we start to read') 
        
        self.treeDic_settings.add_parameter('t_laser_raise', 1, 
                                            type='float', step=0.1, 
                                            bounds=[0, None], suffix=' us',
                                            tip='Time at which the laser raises')      

        self.treeDic_settings.add_parameter('t_RF1_raise', 2, 
                                            type='float', step=0.1, 
                                            bounds=[0, None], suffix=' us',
                                            tip='Time at which the RF modulation 1 raises')      
        self.treeDic_settings.add_parameter('t_RF1_fall', 3, 
                                            type='float', step=0.1, 
                                            bounds=[0, None], suffix=' us',
                                            tip='Time at which the RF modulation 1 falls') 
        self.treeDic_settings.add_parameter('t_RF2_raise', 4, 
                                            type='float', step=0.1, 
                                            bounds=[0, None], suffix=' us',
                                            tip='Time at which the RF modulation 2 raises')      
        self.treeDic_settings.add_parameter('t_RF2_fall', 5, 
                                            type='float', step=0.1, 
                                            bounds=[0, None], suffix=' us',
                                            tip='Time at which the RF modulation 2 falls') 
        
        self.treeDic_settings.add_parameter('t_laser_fall', 6, 
                                            type='float', step=0.1, 
                                            bounds=[0, None], suffix=' us',
                                            tip='Time at which the laser fall') 
        self.treeDic_settings.add_parameter('t_read_end', 7, 
                                            type='float', step=0.1, 
                                            bounds=[0, None], suffix=' us',
                                            tip='Time at which we stop to read') 
 
        self.treeDic_settings.add_parameter('Power', 10, 
                                            type='float', step=1, 
                                            bounds=[-50,30], suffix=' dBm',
                                            tip='Constant power of the first RF')
        self.treeDic_settings.add_parameter('Frequency', 3.01, 
                                            type='float', step=0.1, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Frequency of the first RF')   
        
        
        self.treeDic_settings.add_parameter('DIO_pulse_modulation_1', 3, 
                                            type='int', step=1, 
                                            bounds=[-1,16],
                                            tip='DIO for modulating the first RF signal. Put -1 for nothing.')          
        self.treeDic_settings.add_parameter('DIO_pulse_modulation_2', 4, 
                                            type='int', step=1, 
                                            bounds=[-1,16],
                                            tip='DIO for modulating the second RF signal. Put -1 for nothing.')       
        self.treeDic_settings.add_parameter('DIO_laser', 2, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for the laser')   
        self.treeDic_settings.add_parameter('DIO_sync_scope', 5, 
                                            type='int', step=1, 
                                            bounds=[-1,16],
                                            tip='DIO for synchronizing the oscilloscope. Put -1 for nothing')
        
        # Add a Data Box plotter for the incoming data
        self.databoxplot = egg.gui.DataboxPlot(autosettings_path='plot_calibration')
        self.place_object(self.databoxplot, row=2, column = 1, row_span=2) 
        self.databoxplot.button_multi.set_value(False) # Make all on the same plot
        

    def button_prepare_experiment_clicked(self):
        """
        Prepare the experiment:
            Prepare the pulse sequence in the fpga
            Prepare the signal generator
            Prepare the plot
        """
        _debug('GUICalibration: button_prepare_experiment_clicked')   
        
        # Prepare
        self.prepare_pulse_sequence()
        
        # Trigger a dummy function for signaling to prepare stuffs
        self.event_prepare_experiment()
        
        
    def prepare_pulse_sequence(self):
        """
        Prepare the pulse sequence.  
        It generates the objet to be converted into a data array. 
        """
        _debug('GUICalibration: prepare_pulse_sequence')
        
        DIO_laser   = self.treeDic_settings['DIO_laser']
        DIO_sync    = self.treeDic_settings['DIO_sync_scope']
        DIO_PM1      = self.treeDic_settings['DIO_pulse_modulation_1']
        DIO_PM2      = self.treeDic_settings['DIO_pulse_modulation_2']
        
        t_on_laser  = self.treeDic_settings['t_laser_raise']
        t_off_laser = self.treeDic_settings['t_laser_fall']
        
        self.t_on_read        = self.treeDic_settings['t_read_start']
        t_off_read_aimed = self.treeDic_settings['t_read_end']
        t_read_duration = t_off_read_aimed - self.t_on_read
        
        # FORCE THE TOTAL NUMBER OF TICKS TO BE MULTIPLE OF 32
        # THIS IS BECAUSE THE FPGA BUNDLE EACH 32 COUNTS INTO A SINGLE INT32
        # IF THE NUMBER OF TICKS IS NOT A MULTIPLE OF 32, IT WILL BUNDLE THE 
        # TICKS OF TWO SUCCESSIVE REPEATED SEQUENCE. THAT WOULD COMPLICATE 
        # THE UNBUNDLING PROCESS. THEREFORE, TO KEEP IT SIMPLE, WE GONNA FORCE
        # THE NUMBER OF TICKS TO BE MULTIPLE OF 32.
        self.aimed_duration = t_read_duration
        self.nb_aimed_ticks = self.aimed_duration*120 # That's the aimed number of ticks. 
        self.nb_excess_ticks = self.nb_aimed_ticks%32 # That's how much too much ticks there are
        # Compute a corrected number of ticks which will be a mutliple of 32
        self.nb_corrected_ticks = self.nb_aimed_ticks - self.nb_excess_ticks + 32 # Add 32 extra tick to have more counts than asked :)
        # Get the correction duration for reading
        self.t_read_duration  = self.nb_corrected_ticks/120
        
        
        t_off_read_corrected = self.t_on_read+self.t_read_duration
        
        dt_trigger = 0.1 # Duration of the trigger (us)
    
        # Create the ChannePulse for when to read
        channel_read = ChannelPulses(channel=1, name='Read')      
        channel_read.add_pulses([self.t_on_read, t_off_read_corrected])
        
        # Create the ChannePulse for the laser output
        channel_laser = ChannelPulses(channel=DIO_laser, name='Laser')      
        channel_laser.add_pulses([t_on_laser, t_off_laser])   
        
        # Create a channel for the pulse modulation of the RF1 if we want
        channel_RF1 = ChannelPulses(channel=DIO_PM1, name='RF1 modulation')
        if DIO_PM1 >= 0:
            t_RF1_on  = self.treeDic_settings['t_RF1_raise']
            t_RF1_off = self.treeDic_settings['t_RF1_fall']
            channel_RF1.add_pulses([t_RF1_on, t_RF1_off])
            
        # Create a channel for the pulse modulation of the RF2 if we want
        channel_RF2 = ChannelPulses(channel=DIO_PM2, name='RF2 modulation')
        if DIO_PM2 >= 0:
            t_RF2_on  = self.treeDic_settings['t_RF2_raise']
            t_RF2_off = self.treeDic_settings['t_RF2_fall']
            channel_RF2.add_pulses([t_RF2_on, t_RF2_off])
            
        
        # Create a channel for the end state (use full for the scope)
        channel_sync = ChannelPulses(channel=DIO_sync, name='Synchronize scope')
        # Add a pulse only if the DIO is not -1
        if DIO_sync >= 0:
            channel_sync.add_pulses([t_off_read_corrected, 
                                     t_off_read_corrected+dt_trigger]) # Same duration as trigger
        
        # Put the pulses into a block
        block = PulsePatternBlock(name='Block cool')
        block.add_channelEvents([channel_read, 
                                 channel_laser,
                                 channel_RF1,
                                 channel_RF2,
                                 channel_sync])
        
        # Put the block into a sequence
        self.sequence = Sequence(name='Calibration')
        self.sequence.add_block(block)

    def databoxplot_update(self):
        """
        Update the plot
        """
        _debug('GUICalibration: databoxplot_update')
        # CLear the plot
        self.databoxplot.clear() 
                
        tmin = self.t_on_read
        tmax = tmin+len(self.counts_total)/120  # Maximum time is the lenght times the tick duration
        
        self.databoxplot['Time_(us)'] = np.linspace(tmin, tmax, len(self.counts_total))
        self.databoxplot['Total_counts'] = self.counts_total
        
        # Show it
        self.databoxplot.plot()      
        
    def after_one_loop(self, fpga_output, iteration, rep):
        """
        What to do after one loop of the fpga. 

        This is called after each loop (single run) of the fpga. 
        
        fpga_output:
            Output of the fpga for wich we extract the counts. 
            We should be in Count Each Tick (CET) mode. Therefore this 
            parameter should be an a array of number. Each number should 
            correspond to 32 ticks that we need to unbundle. 
        iteration:
            int corresponding to which iteration are we at
            
        rep:
            Number of repetition of the sequence into the fpga instruction
            """
        _debug('GUICalibration after_one_loop')
        
        self.count_processor = _fc.ProcessFPGACounts(fpga_output)
        self.counts = self.count_processor.get_sum_count_per_repetition_CET_mode(rep)
        
        # Interprete the array 
        
        if iteration == 0:
            # Get the count and the correct shape for the array
            self.counts_total = np.array(self.counts)  
        else:
            # Increment the counts
            self.counts_total += np.array(self.counts) 
            
        
            
        print('Counts: ', self.counts)
        print('Lenght = ', len(self.counts))

        # Update the plot
        self.databoxplot_update()
            

        
    def event_prepare_experiment(self): 
        """
        Dummy function to be overrid
        This is was should be done after that the pulse sequence is defined. 
        """        
        return 

class GUISpinContrast(egg.gui.Window):
    """
    GUI for studying the spin contrast between ms=0 state and ms= +-1
    The count is in each tick mode. 
    """
    
    def __init__(self, name="Calibration", size=[1000,500]): 
        """
        Initialize
        """    
        _debug('GUISpinContrast:__init__')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Initialise the GUI
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUISpinContrast: initialize_GUI')
        _debug('The difference between who you are and who you want to be is what you do.')
        
        # A button for preparing stuff
        self.button_prepare_experiment = egg.gui.Button('Prepare',
                                                        tip='Prepare the measurement before running')
        self.place_object(self.button_prepare_experiment, row=1, column=0)
        self.connect(self.button_prepare_experiment.signal_clicked, 
                     self.button_prepare_experiment_clicked)
        
        # Place a list of the possible sequence
        self.list_sequence = ['Two_states_one_sigGen',
                              'Tree_states_two_sigGen']
        self.comboxBox_list_sequence = egg.gui.ComboBox(self.list_sequence,
                                                        tip='Which sequence to generate.')
        self.place_object( self.comboxBox_list_sequence, 
                          row=1, column=1)
        self.connect(self.comboxBox_list_sequence.signal_changed, self.comboxBox_list_sequence_changed)
        self.comboxBox_list_sequence_changed() # Initiate the value
        
        # Add a Data Box plotter for the incoming data
        self.databoxplot = egg.gui.DataboxPlot(autosettings_path='plot_calibration')
        self.place_object(self.databoxplot, row=2, column = 2, row_span=2) 
        self.databoxplot.button_multi.set_value(False) # Make all on the same plot

    def comboxBox_list_sequence_changed(self):
        """
        What to do when the value changes
        """
        _debug('GUISpinContrast: comboxBox_list_sequence_changed')
        # Note the type of sequence
        self.type_sequence = self.comboxBox_list_sequence.get_text()
        # Reinitialize the tree dicrtionnary
        self.initiate_treeDictionnary()
        
        
        
    def initiate_treeDictionnary(self):
        """
        Initiate the three dictionnary depending on the type of sequence
        """
        _debug('GUISpinContrast: initiate_treeDictionnary')

        if self.type_sequence == 'Two_states_one_sigGen':
            # tree dictionnarry for the settings
            self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_pulse_calibration_two_states')
            self.place_object(self.treeDic_settings, row=2, column=0)    
            
    
            self.treeDic_settings.add_parameter('t_read_start', 0, 
                                                type='float', step=0.1, 
                                                bounds=[0, None], suffix=' us',
                                                tip='Time at which we start to read') 
    
            self.treeDic_settings.add_parameter('t_read_end', 3, 
                                                type='float', step=0.1, 
                                                bounds=[0, None], suffix=' us',
                                                tip='Time at which we stop to read') 
            
            self.treeDic_settings.add_parameter('t_laser_raise', 1, 
                                                type='float', step=0.1, 
                                                bounds=[0, None], suffix=' us',
                                                tip='Time at which the laser raises')    
            
            self.treeDic_settings.add_parameter('t_laser_fall', 2, 
                                                type='float', step=0.1, 
                                                bounds=[0, None], suffix=' us',
                                                tip='Time at which the laser fall') 
     
            self.treeDic_settings.add_parameter('Power', -20, 
                                                type='float', step=1, 
                                                bounds=[-50,30], suffix=' dBm',
                                                tip='Constant power of the RF')
            self.treeDic_settings.add_parameter('Frequency', 3, 
                                                type='float', step=0.1, 
                                                bounds=[0,10], suffix=' GHz',
                                                tip='Frequency of the RF')     
            self.treeDic_settings.add_parameter('dt_pi_pulse', 0.3, 
                                                type='float', step=0.1, 
                                                bounds=[0,None], suffix=' us',
                                                tip='Duration of pi pulse (RF)')            
            
            self.treeDic_settings.add_parameter('DIO_pulse_modulation', 3, 
                                                type='int', step=1, 
                                                bounds=[0,16],
                                                tip='DIO for modulating the pulse.')          
            self.treeDic_settings.add_parameter('DIO_laser', 2, 
                                                type='int', step=1, 
                                                bounds=[0,16],
                                                tip='DIO for the laser')   
            self.treeDic_settings.add_parameter('DIO_sync_scope', 5, 
                                                type='int', step=1, 
                                                bounds=[-1,16],
                                                tip='DIO for synchronizing the oscilloscope. Put -1 for nothing')
            
        elif self.type_sequence == 'Tree_states_two_sigGen':
            self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_pulse_calibration_tree_states')
            self.place_object(self.treeDic_settings, row=2, column=0)    
            
    
            self.treeDic_settings.add_parameter('t_read_start', 0, 
                                                type='float', step=0.1, 
                                                bounds=[0, None], suffix=' us',
                                                tip='Time at which we start to read') 
    
            self.treeDic_settings.add_parameter('t_read_end', 3, 
                                                type='float', step=0.1, 
                                                bounds=[0, None], suffix=' us',
                                                tip='Time at which we stop to read') 
            
            self.treeDic_settings.add_parameter('t_laser_raise', 1, 
                                                type='float', step=0.1, 
                                                bounds=[0, None], suffix=' us',
                                                tip='Time at which the laser raises')    
            
            self.treeDic_settings.add_parameter('t_laser_fall', 2, 
                                                type='float', step=0.1, 
                                                bounds=[0, None], suffix=' us',
                                                tip='Time at which the laser fall') 
      
            self.treeDic_settings.add_parameter('Power', 10, 
                                                type='float', step=1, 
                                                bounds=[-50,30], suffix=' dBm',
                                                tip='Constant power of the pi pulse of ms=+1')
            self.treeDic_settings.add_parameter('Frequency', 3.01, 
                                                type='float', step=0.1, 
                                                bounds=[0,10], suffix=' GHz',
                                                tip='Frequency of the pi pulse of ms=+1')     
            self.treeDic_settings.add_parameter('dt_pi_pulse_ms_+1', 0.3, 
                                                type='float', step=0.1, 
                                                bounds=[0,None], suffix=' us',
                                                tip='Duration of pi pulse (RF) for ms=+1')        
            self.treeDic_settings.add_parameter('dt_pi_pulse_ms_-1', 0.3, 
                                                type='float', step=0.1, 
                                                bounds=[0,None], suffix=' us',
                                                tip='Duration of pi pulse (RF) for ms=-1')   
            
            self.treeDic_settings.add_parameter('DIO_pulse_modulation', 3, 
                                                type='int', step=1, 
                                                bounds=[0,16],
                                                tip='DIO for modulating the pulse.')          
            self.treeDic_settings.add_parameter('DIO_laser', 2, 
                                                type='int', step=1, 
                                                bounds=[0,16],
                                                tip='DIO for the laser')   
            self.treeDic_settings.add_parameter('DIO_sync_scope', 5, 
                                                type='int', step=1, 
                                                bounds=[-1,16],
                                                tip='DIO for synchronizing the oscilloscope. Put -1 for nothing')
            self.treeDic_settings.add_parameter('DIO_TTL_switch', 4, 
                                                type='int', step=1, 
                                                bounds=[-1,16],
                                                tip='DIO for setting the TTL switch for choosing which signal generator is selected./nIn the current setup, it is the TTL input of the mini-circuit RF switch./nThis is used only if we measure the three states.')        
    
            
            
            
            
        
    def button_prepare_experiment_clicked(self):
        """
        Prepare the experiment:
            Prepare the pulse sequence in the fpga
            Prepare the signal generator
            Prepare the plot
        """
        _debug('GUISpinContrast: button_prepare_experiment_clicked')   
        
        # Prepare the pulse sequence depending on which type do we want
        if self.type_sequence == 'Two_states_one_sigGen':
            self.prepare_pulse_sequence_two_states()
        elif self.type_sequence == 'Tree_states_two_sigGen':
            self.prepare_pulse_sequence_tree_states()
        
        
        
        # Trigger a dummy function for signaling to prepare stuffs
        self.event_prepare_experiment()
        
        
    def prepare_pulse_sequence_two_states(self):
        """
        Prepare the pulse sequence.  
        It generates the objet to be converted into a data array. 
        
        This is a sequence where we measure the PC from ms=0 ans ms=+-
        in CET mode. 
        """
        _debug('GUISpinContrast: prepare_pulse_sequence_two_states')
        
        DIO_laser   = self.treeDic_settings['DIO_laser']
        DIO_sync    = self.treeDic_settings['DIO_sync_scope']
        DIO_PM      = self.treeDic_settings['DIO_pulse_modulation']
        
        t_on_laser       = self.treeDic_settings['t_laser_raise']
        t_off_laser      = self.treeDic_settings['t_laser_fall']
        self.t_on_read   = self.treeDic_settings['t_read_start']
        t_off_read_aimed = self.treeDic_settings['t_read_end']
        dt_pi_pulse      = self.treeDic_settings['dt_pi_pulse'] # Duration of the pi-pulse
                
        dt_trigger = 0.1 # Duration of the trigger for the scope (us)
        dt_wait_after_pi_pulse = 0.5 # Duration of how long do we wait after the pi pulse
        
        t_read_duration = t_off_read_aimed - self.t_on_read
        
        # FORCE THE TOTAL NUMBER OF TICKS TO BE MULTIPLE OF 32
        # THIS IS BECAUSE THE FPGA BUNDLE EACH 32 COUNTS INTO A SINGLE INT32
        # IF THE NUMBER OF TICKS IS NOT A MULTIPLE OF 32, IT WILL BUNDLE THE 
        # TICKS OF TWO SUCCESSIVE REPEATED SEQUENCE. THAT WOULD COMPLICATE 
        # THE UNBUNDLING PROCESS. THEREFORE, TO KEEP IT SIMPLE, WE GONNA FORCE
        # THE NUMBER OF TICKS TO BE MULTIPLE OF 32.
        self.aimed_duration = t_read_duration
        self.nb_aimed_ticks = self.aimed_duration*120 # That's the aimed number of ticks. 
        self.nb_excess_ticks = self.nb_aimed_ticks%32 # That's how much too much ticks there are
        # Compute a corrected number of ticks which will be a mutliple of 32
        self.nb_corrected_ticks = self.nb_aimed_ticks - self.nb_excess_ticks + 32 # Add 32 extra tick to have more counts than asked :)
        # Get the correction duration for reading
        self.t_read_duration  = self.nb_corrected_ticks/120
        t_off_read_corrected = self.t_on_read+self.t_read_duration


        # Create the ChannePulse for when to read
        # Create the ChannePulse for the laser output
        # Create a channel for the pulse modulation of the RF for the pi pulse
        channel_read  = ChannelPulses(channel=1, name='Read')  
        channel_laser = ChannelPulses(channel=DIO_laser, name='Laser')  
        channel_RF    = ChannelPulses(channel=DIO_PM, name='RF modulation')
        
        # Create the pulses for ms=0
        channel_read .add_pulses([self.t_on_read, t_off_read_corrected])
        channel_laser.add_pulses([t_on_laser, t_off_laser])   
        
        # Assuming that the state is still in ms=0 (it didn't decay yet)
        # Sent a pi-pulse
        t0 = channel_read.get_pulses_times()[-1]
        channel_RF.add_pulses([t0, t0+dt_pi_pulse])
        
        # Now the state is ms=+-1. Repeat the same thing that we did for ms=0
        # Translated by t0
        t0 = channel_RF.get_pulses_times()[-1] + dt_wait_after_pi_pulse
        channel_read .add_pulses([t0 + self.t_on_read, t0 + t_off_read_corrected])
        channel_laser.add_pulses([t0 + t_on_laser, t0 + t_off_laser])      
        
        # Create a channel for the end state (useful for checking on the scope)
        channel_sync = ChannelPulses(channel=DIO_sync, name='Synchronize scope')
        # Add a pulse only if the DIO is not -1
        if DIO_sync >= 0:
            channel_sync.add_pulses([t_off_read_corrected, 
                                     t_off_read_corrected+dt_trigger]) # Same duration as trigger
       
        # Put the pulses into a block
        block = PulsePatternBlock(name='Block cool')
        block.add_channelEvents([channel_read, 
                                 channel_laser,
                                 channel_RF,
                                 channel_sync])
        
        # Put the block into a sequence
        self.sequence = Sequence(name='Spin Contrast')
        self.sequence.add_block(block)

    def prepare_pulse_sequence_tree_states(self):
        """
        Prepare the pulse sequence.  
        It generates the objet to be converted into a data array. 
        
        This is a sequence where we measure the PC from ms=0 ans ms=+-
        in CET mode.         
        """
        _debug('GUISpinContrast: prepare_pulse_sequence')
        
        DIO_laser   = self.treeDic_settings['DIO_laser']
        DIO_sync    = self.treeDic_settings['DIO_sync_scope']
        DIO_PM      = self.treeDic_settings['DIO_pulse_modulation']
        DIO_TTL     = self.treeDic_settings['DIO_TTL_switch']
        
        t_on_laser       = self.treeDic_settings['t_laser_raise']
        t_off_laser      = self.treeDic_settings['t_laser_fall']
        self.t_on_read   = self.treeDic_settings['t_read_start']
        t_off_read_aimed = self.treeDic_settings['t_read_end']
        dt_pi_pulse_m1   = self.treeDic_settings['dt_pi_pulse_ms_-1'] # Duration of the pi-pulse for ms=-1
        dt_pi_pulse_p1   = self.treeDic_settings['dt_pi_pulse_ms_+1'] # Duration of the pi-pulse for ms=+1
                
        dt_trigger = 0.1 # Duration of the trigger for the scope (us)
        dt_wait_after_pi_pulse = 0.5 # Duration of how long do we wait after the pi pulse
        
        t_read_duration = t_off_read_aimed - self.t_on_read
        
        # FORCE THE TOTAL NUMBER OF TICKS TO BE MULTIPLE OF 32
        # THIS IS BECAUSE THE FPGA BUNDLE EACH 32 COUNTS INTO A SINGLE INT32
        # IF THE NUMBER OF TICKS IS NOT A MULTIPLE OF 32, IT WILL BUNDLE THE 
        # TICKS OF TWO SUCCESSIVE REPEATED SEQUENCE. THAT WOULD COMPLICATE 
        # THE UNBUNDLING PROCESS. THEREFORE, TO KEEP IT SIMPLE, WE GONNA FORCE
        # THE NUMBER OF TICKS TO BE MULTIPLE OF 32.
        self.aimed_duration = t_read_duration
        self.nb_aimed_ticks = self.aimed_duration*120 # That's the aimed number of ticks. 
        self.nb_excess_ticks = self.nb_aimed_ticks%32 # That's how much too much ticks there are
        # Compute a corrected number of ticks which will be a mutliple of 32
        self.nb_corrected_ticks = self.nb_aimed_ticks - self.nb_excess_ticks + 32 # Add 32 extra tick to have more counts than asked :)
        # Get the correction duration for reading
        self.t_read_duration  = self.nb_corrected_ticks/120
        t_off_read_corrected = self.t_on_read+self.t_read_duration


        # Create the ChannePulse for when to read
        # Create the ChannePulse for the laser output
        # Create a channel for the pulse modulation of the RF for the first pi pulse
        # Create a channel for the pulse modulation of the second pi pulse
        channel_read  = ChannelPulses(channel=1, name='Read')  
        channel_laser = ChannelPulses(channel=DIO_laser, name='Laser')  
        channel_RF1   = ChannelPulses(channel=DIO_PM , name='RF modulation #1')
        channel_RF2   = ChannelPulses(channel=DIO_TTL, name='RF modulation #2')
        
        
        # Create the pulses for ms=0
        channel_read .add_pulses([self.t_on_read, t_off_read_corrected])
        channel_laser.add_pulses([t_on_laser, t_off_laser])   
        
        # Assuming that the state is still in ms=0 (it didn't decay yet)
        # Sent a pi-pulse for flipping into ms=+1
        t0 = channel_read.get_pulses_times()[-1]
        channel_RF1.add_pulses([t0, t0+dt_pi_pulse_p1])
        
        # Now the state is ms=+1. Repeat the same thing that we did for ms=0
        # Translated by t0
        t0 = channel_RF1.get_pulses_times()[-1] + dt_wait_after_pi_pulse
        channel_read .add_pulses([t0 + self.t_on_read, t0 + t_off_read_corrected])
        channel_laser.add_pulses([t0 + t_on_laser, t0 + t_off_laser])    
        
        
        # Assuming that the state is still in ms=0 (it didn't decay yet)
        # Sent a pi-pulse for flipping into ms=-1
        t0 = channel_read.get_pulses_times()[-1]
        channel_RF2.add_pulses([t0, t0+dt_pi_pulse_m1])
        
        # Now the state is ms=-1. Repeat the same thing that we did for ms=0
        # Translated by t0
        t0 = channel_RF2.get_pulses_times()[-1] + dt_wait_after_pi_pulse
        channel_read .add_pulses([t0 + self.t_on_read, t0 + t_off_read_corrected])
        channel_laser.add_pulses([t0 + t_on_laser, t0 + t_off_laser])            
        
        # Create a channel for the end state (useful for checking on the scope)
        channel_sync = ChannelPulses(channel=DIO_sync, name='Synchronize scope')
        # Add a pulse only if the DIO is not -1
        if DIO_sync >= 0:
            channel_sync.add_pulses([t_off_read_corrected, 
                                     t_off_read_corrected+dt_trigger]) # Same duration as trigger
       
        # Put the pulses into a block
        block = PulsePatternBlock(name='Block cool')
        block.add_channelEvents([channel_read, 
                                 channel_laser,
                                 channel_RF1,
                                 channel_RF2,
                                 channel_sync])
        
        # Put the block into a sequence
        self.sequence = Sequence(name='Spin Contrast')
        self.sequence.add_block(block)

    def databoxplot_update(self):
        """
        Update the plot
        """
        _debug('GUISpinContrast: databoxplot_update')
        # CLear the plot
        self.databoxplot.clear() 
                
        print('Get that better!!') 
        Npts = len(self.counts_total_s[0])
        tmin = self.t_on_read
        tmax = tmin+Npts/120  # Maximum time is the lenght times the tick duration
        
        self.databoxplot['Time_(us)'] = np.linspace(tmin, tmax, Npts)
        
        for i, counts in enumerate(self.counts_total_s):
            self.databoxplot['Total_counts_%d'%i] = counts
        # Show it
        self.databoxplot.plot()      
        
    def after_one_loop(self, fpga_output, iteration, rep):
        """
        What to do after one loop of the fpga. 

        This is called after each loop (single run) of the fpga. 
        
        fpga_output:
            Output of the fpga for wich we extract the counts. 
            We should be in Count Each Tick (CET) mode. Therefore this 
            parameter should be an a array of number. Each number should 
            correspond to 32 ticks that we need to unbundle. 
        iteration:
            int corresponding to which iteration are we at
            
        rep:
            Number of repetition of the sequence into the fpga instruction
            """
        _debug('GUISpinContrast: after_one_loop')
        
        # Collect the array for all the counts while the reading channel was on
        self.count_processor = _fc.ProcessFPGACounts(fpga_output)
        self.counts_all_together = self.count_processor.get_sum_count_per_repetition_CET_mode(rep)
        
        # Split the array depending on which sequence do we have
        if self.type_sequence == 'Two_states_one_sigGen':
            #Split it in two, for each state
            self.counts_s = np.split(self.counts_all_together, 2)
        elif self.type_sequence == 'Tree_states_two_sigGen':
            #Split it in two, for each state
            self.counts_s = np.split(self.counts_all_together, 3)       

        
        if iteration == 0:
            # Get the count and the correct shape for the array
            self.counts_total_s = np.array(self.counts_s)  
        else:
            # Increment the counts
            self.counts_total_s += np.array(self.counts_s) 

        # Update the plot
        self.databoxplot_update()
        
        
    def event_prepare_experiment(self): 
        """
        Dummy function to be overrid
        This is was should be done after that the pulse sequence is defined. 
        """        
        return 

class GUIT1TimeTrace2(egg.gui.Window):
    """
    GUI for preparing the pulse sequence for a T1 measurement. 
    The measurement is a time trace for two state (ms=0 and ms=+-1)
    
    """
    
    def __init__(self, name="T1", size=[1000,500]): 
        """
        Initialize
        """    
        _debug('GUIT1TimeTrace2:__init__')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Initialise the GUI
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIT1TimeTrace2: initialize_GUI')
        _debug('Everything is hard before it is easy. – Goethe')
        
        # A button for preparing stuff
        self.button_prepare_experiment = egg.gui.Button('Prepare',
                                                        tip='Prepare the measurement before running')
        self.place_object(self.button_prepare_experiment, row=1, column=0)
        self.connect(self.button_prepare_experiment.signal_clicked, 
                     self.button_prepare_experiment_clicked)
            
        # tree dictionnarry for the settings
        self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_T1_trace3')
        self.place_object(self.treeDic_settings, row=2, column=0)

        self.treeDic_settings.add_parameter('Power', -20, 
                                            type='float', step=1, 
                                            bounds=[-50,30], suffix=' dBm',
                                            tip='Constant power of the RF')
        self.treeDic_settings.add_parameter('Frequency', 3, 
                                            type='float', step=0.1, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Frequency of the RF')        
        self.treeDic_settings.add_parameter('N', 50, 
                                            type='int', step=10, 
                                            bounds=[0,None],
                                            tip='Number of points to sweep')         
        self.treeDic_settings.add_parameter('Spacing', ['Linear','Logarithmic'], 
                                            tip='Spacing between the points')         
        self.treeDic_settings.add_parameter('Log_factor', 4, 
                                            type='float', step=1, 
                                            bounds=[None,None],
                                            tip='Logarithmic factor for "how squeezed" the points are.\nThis takes effect only if Spacing is set to Logarithmic.')  
     
        self.treeDic_settings.add_parameter('t_in', 0, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Initialie time to probe') 
        self.treeDic_settings.add_parameter('t_end', 1, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Last time to probe')   

        self.treeDic_settings.add_parameter('dt_pi_pulse', 0.3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of pi pulse (RF)') 
        
        self.treeDic_settings.add_parameter('dt_laser_initiate', 3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of laser for initiating into ms=0')  
        self.treeDic_settings.add_parameter('dt_wait_after_initiate', 1.1, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of time to wait between the laser initialization into ms=0 and the pi-pulse') 
        
        self.treeDic_settings.add_parameter('dt_readout', 0.4, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of the readout') 
        self.treeDic_settings.add_parameter('delay_read_before_laser', 0.05, 
                                            type='float', step=0.01, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Delay that we read before shining the laser')  
        
        self.treeDic_settings.add_parameter('DIO_laser', 2, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for the laser')          
        self.treeDic_settings.add_parameter('DIO_pulse_modulation', 3, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for modulating the pulse. AKA for sending the RF.')  
        self.treeDic_settings.add_parameter('DIO_sync_scope', 5, 
                                            type='int', step=1, 
                                            bounds=[-1,16],
                                            tip='DIO for synchronizing the oscilloscope. Put -1 for nothing')
        
        # Add a Data Box plotter for the incoming data
        self.databoxplot = egg.gui.DataboxPlot(autosettings_path='plot_T1_trace3')
        self.place_object(self.databoxplot, row=2, column = 1, row_span=2) 
        self.databoxplot.button_multi.set_value(False) # Make all on the same plot
        
        # Make a label for showing some estimate
        self.label_estimates = egg.gui.Label('We have the best T1 gui on the market.')
        self.place_object(self.label_estimates, row=2, column=2)        

    def button_prepare_experiment_clicked(self):
        """
        Prepare the experiment:
            Prepare the pulse sequence in the fpga
            Prepare the signal generator
            Prepare the plot
        """
        _debug('GUIT1TimeTrace2: button_prepare_experiment_clicked')   
        
        # Prepare
        self.prepare_pulse_sequence()
        
        # Compute and show some estimate
        self.compute_show_estimate()
        
        # Trigger a dummy function for signaling to prepare stuffs
        self.event_prepare_experiment()
        
    def prepare_pulse_sequence(self):
        """
        Prepare the pulse sequence. 
        It generates the objet to be converted into a data array. 
        """
        _debug('GUIT1TimeTrace2: prepare_pulse_sequence')
        
        DIO_laser   = self.treeDic_settings['DIO_laser']
        DIO_PM      = self.treeDic_settings['DIO_pulse_modulation']
        DIO_sync    = self.treeDic_settings['DIO_sync_scope']
        
        dt_laser      = self.treeDic_settings['dt_laser_initiate'] # Interval of time for shining the laser
        dt_readout    = self.treeDic_settings['dt_readout']
        dt_wait_ms0_pi= self.treeDic_settings['dt_wait_after_initiate'] #How much time to wait between ms=0 and pi pulse
        dt_pi_pulse   = self.treeDic_settings['dt_pi_pulse'] # Duration of the pi-pulse
        delay_read    = self.treeDic_settings['delay_read_before_laser'] # Delay (us) that we read before shining the laser
        self.tmin       = self.treeDic_settings['t_in'] # Minimum time  to probe
        self.tmax       = self.treeDic_settings['t_end'] # Maximum time  to probe        
        self.nb_block   = self.treeDic_settings['N'] # Number of point to take 
        self.log_factor = self.treeDic_settings['Log_factor']
        
        # Finnally, here is a strong advantahe of this python approach. 
        # We have the option for a logarithmic spacing  
        if self.treeDic_settings['Spacing'] == 'Linear':
            self.t_probe_s = np.linspace(self.tmin  , self.tmax , self.nb_block)
        elif self.treeDic_settings['Spacing'] == 'Logarithmic':
            #Define the time to probe
            tlin = np.linspace(self.tmin  , self.tmax , self.nb_block) 
            tmin = self.tmin
            tmax = self.tmax
            #Transform it to a log scale
            beta  = self.log_factor/(tmax-tmin) #Factor for the logaritmic spacing (how squeezed will be the point near tmin) 
            B_log = (tmax-tmin)/(np.exp(beta*tmax)-np.exp(beta*tmin))
            A_log = tmin - B_log*np.exp(beta*tmin) 
            self.t_probe_s = A_log + B_log*np.exp(beta*tlin)  #Lograritmic spacing
        
        dt_trigger = 1 # Duration of the trigger for synchronizing the scope (us)
        

        # Initiate the sequence on which we gonna construct
        sequence = Sequence(name='T1 2 states')

        # Create a channel for the trigger
        channel_sync = ChannelPulses(channel=DIO_sync, name='Sync oscilloscope')
        channel_sync.add_pulses([0, dt_trigger])  
        
        # Create a block for each time to probe
        for i in range(len(self.t_probe_s)):
            t_probe = self.t_probe_s[i]
            
            # Each block will consist of twos steps: read ms0, +-1 
            
            # Laser channel for each ms state
            channel_laser = ChannelPulses(channel=DIO_laser, name='Laser')      
            # Read channel for each state
            channel_read  = ChannelPulses(channel=1, name='Read')
            # Channel for the Pi-pulse initializing ms=+-1
            channel_RF    = ChannelPulses(channel=DIO_PM , name='RF')
           
            # Prepare and read ms=0
            # Prepare the state
            channel_laser.add_pulses([dt_trigger, dt_trigger+dt_laser])
            # Let evolve the state
            tref = channel_laser.get_pulses_times()[-1] + t_probe 
            # Read it. Start to read slightly a little bit before the laser if shone
            channel_read.add_pulses([tref - delay_read, tref + dt_readout])    
            
            # Shine the laser for both reading and for initializing into ms=0
            channel_laser.add_pulses([tref, tref+dt_laser])
            # Re-read at the end of the shining as a reference
            tref = channel_laser.get_pulses_times()[-1] 
            channel_read.add_pulses([tref - dt_readout, tref]) 
            
            # At this point the state is ms=0 and t = tref
            
            # Prepare and read ms=+1
            # Note at which time to start the RF for flipping the state
            tref_RF = tref + dt_wait_ms0_pi
            channel_RF.add_pulses([tref_RF, tref_RF + dt_pi_pulse]) # Flip in ms=-1
            # Let evolve the state 
            tref = channel_RF.get_pulses_times()[-1] + t_probe
            # Read it. Start to read slightly a little bit before the laser if shone
            channel_read.add_pulses([tref - delay_read, tref + dt_readout])  

            # Shine the laser for reading 
            #TODO use this reading for initializing for the next block !!!!!
            channel_laser.add_pulses([tref, tref+dt_laser])
            # Re-read at the end of the shining as a reference
            tref = channel_laser.get_pulses_times()[-1] 
            channel_read.add_pulses([tref - dt_readout, tref])             
            
            
            # Add all that masterpiece to a block
            block = PulsePatternBlock(name='Block tprobe = %.2f us'%t_probe)
            block.add_channelEvents([channel_laser, channel_RF, channel_read])
            # Add the trigger for synchronizing the scope only on the first block
            if i ==0:
                block.add_channelEvents([channel_sync])
            
            # Add the block to the sequence
            sequence.add_block(block)             
            
        self.sequence =  sequence

    def databoxplot_update(self):
        """
        Update the plot
        """
        _debug('GUIT1TimeTrace2: databoxplot_update')
        # Clear the plot
        self.databoxplot.clear() 
        
                
        self.databoxplot['Time_(us)'] = self.t_probe_s
        # Loop over each readout 
        for i, count_per_readout in enumerate(self.counts_total):
            # Create a curve
            self.databoxplot['Total_counts_%d'%i] = count_per_readout
            
        # Show it
        self.databoxplot.plot()   
        
    def after_one_loop(self, counts, iteration, rep):
        """
        What to do after one loop of the fpga. 

        This is called after each loop (single run) of the fpga. 
        
        counts:
            Array of counts that the fpga get. 
        iteration:
            int corresponding to which iteration are we at
            
        rep:
            Number of repetition of the sequence into the fpga instruction
            """
        _debug('GUIT1TimeTrace2: after_one_loop')
        
        # Get the counts per readout per block
        self.count_processor = _fc.ProcessFPGACounts(counts)
        self.block_ind, self.counts = self.count_processor.get_count_per_readout_vs_block(rep, self.nb_block)

#        print(self.counts)
        # If its the first iteration
        if iteration == 0:
            # Get the count and the correct shape for the array
            self.counts_total = np.array(self.counts)  
        else:
            # Increment the counts
            self.counts_total += np.array(self.counts)  
            
        # Update the plot
        self.databoxplot_update()
        
    def event_prepare_experiment(self): 
        """
        Dummy function to be overrid
        This is was should be done after that the pulse sequence is defined. 
        """        
        return         
    
    def compute_show_estimate(self):
        """
        Compute and show some estimate for the pulse sequence. 
        """
        _debug('GUIT1TimeTrace2: compute_show_estimate')
        
        # See notebook of Michael Caouette-Mansour on July 24 2020 for details 
        # of how the minimum time is estimated
        
        # Compute roughly the total time for a single sequence. 
        # This is assuming that the dominating time are the times to probe
        # Multiply by 2 because we do it twice, for each state
        T_seq = 2* ( 0.5*(self.nb_block+1)*self.tmax + 0.5*(self.nb_block-1)*self.tmin )
        
        C0 = 0.04 # Mean count per each readout for ms=0
        c  = 0.1  # Contrast between the states
        C1 = C0*(1-c) # Mean count per readout for ms=+-1
        
        # Compute the minimum number of readout for distinguishing the states
        N_min = (np.sqrt(C0) + np.sqrt(C1))**2/(C0-C1)**2
        
        T_minimum = T_seq*N_min # Minimum elapsed time before distinguishing the states
        
        # It should be in us. Let's convert it in minutes
        T_minutes = T_minimum*1e-6/60 
        
        # Set the text and the label
        text =   'Assuming %0.3f count per readout on state ms=0.'%C0
        text+= '\nAssuming %0.3f count per readout on state ms=+-1.'%C1
        text+= '\nNote that the contrast is %0.1f percente'%c
        text+='\nIt should take %d readout before distinguishing those states'%N_min
        text+='\nWith the current sequence, this should take at least %0.2f minutes'%T_minutes
        self.label_estimates.set_text(text)
        
class GUIT1TimeTrace3(egg.gui.Window):
    """
    GUI for preparing the pulse sequence for a T1 measurement. 
    The measurement is a time trace for three state (ms=0 and ms=-1 and ms=+1)
    
    """   
    def __init__(self, name="T1", size=[1000,500]): 
        """
        Initialize
        """    
        _debug('GUIT1TimeTrace3:__init__')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Initialise the GUI
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIT1TimeTrace3: initialize_GUI')
        _debug('I want to be remembered as the one who tried. – Dr. Dorothy Height')
        
        # A button for preparing stuff
        self.button_prepare_experiment = egg.gui.Button('Prepare',
                                                        tip='Prepare the measurement before running')
        self.place_object(self.button_prepare_experiment, row=1, column=0)
        self.connect(self.button_prepare_experiment.signal_clicked, 
                     self.button_prepare_experiment_clicked)
            
        # tree dictionnarry for the settings
        self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_T1_trace3')
        self.place_object(self.treeDic_settings, row=2, column=0)

        self.treeDic_settings.add_parameter('Power', -20, 
                                            type='float', step=1, 
                                            bounds=[-50,30], suffix=' dBm',
                                            tip='Constant power of the RF')
        self.treeDic_settings.add_parameter('Frequency', 3, 
                                            type='float', step=0.1, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Frequency of the RF')        
        self.treeDic_settings.add_parameter('N', 50, 
                                            type='int', step=10, 
                                            bounds=[0,None],
                                            tip='Number of points to sweep')         
        self.treeDic_settings.add_parameter('Spacing', ['Linear','Logarithmic'], 
                                            tip='Spacing between the points')         
        self.treeDic_settings.add_parameter('Log_factor', 3, 
                                            type='float', step=1, 
                                            bounds=[None,None],
                                            tip='Logarithmic factor for "how squeezed" the points are.\nThis takes effect only if Spacing is set to Logarithmic.')  
     
        self.treeDic_settings.add_parameter('t_in', 0, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Initialie time to probe') 
        self.treeDic_settings.add_parameter('t_end', 1, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Last time to probe')   

        self.treeDic_settings.add_parameter('dt_pi_pulse_ms+1', 0.3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of pi pulse for ms=+1(RF)') 
        self.treeDic_settings.add_parameter('dt_pi_pulse_ms-1', 0.3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of pi pulse for ms=-1(RF)') 
        
        self.treeDic_settings.add_parameter('dt_laser_initiate', 3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of laser for initiating into ms=0')  
        self.treeDic_settings.add_parameter('dt_wait_after_initiate', 1.1, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of time to wait between the laser initialization into ms=0 and the pi-pulse') 
        
        self.treeDic_settings.add_parameter('dt_readout', 0.4, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of the readout') 
        self.treeDic_settings.add_parameter('delay_read_before_laser', 0.05, 
                                            type='float', step=0.01, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Delay that we read before shining the laser')  
        
        self.treeDic_settings.add_parameter('DIO_laser', 2, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for the laser')          
        self.treeDic_settings.add_parameter('DIO_pulse_modulation_ms+1', 3, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for modulating the pi pulse of ms=+1. AKA for sending the RF.')  
        self.treeDic_settings.add_parameter('DIO_pulse_modulation_ms-1', 4, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for modulating the pi pulse of ms=-1. AKA for sending the RF.')  

        self.treeDic_settings.add_parameter('DIO_sync_scope', 5, 
                                            type='int', step=1, 
                                            bounds=[-1,16],
                                            tip='DIO for synchronizing the oscilloscope. Put -1 for nothing')
        
        # Add a Data Box plotter for the incoming data
        self.databoxplot = egg.gui.DataboxPlot(autosettings_path='plot_T1_trace3')
        self.place_object(self.databoxplot, row=2, column = 1, row_span=2) 
        self.databoxplot.button_multi.set_value(False) # Make all on the same plot
        
        # Make a label for showing some estimate
        self.label_estimates = egg.gui.Label('We have the best T1 tracer gui on the market.')
        self.place_object(self.label_estimates, row=2, column=2)        

    def initialize_treeDictionary_V1(self):
        """
        Not used for now
        """
        # tree dictionnarry for the settings
        self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_T1_trace3')
        self.place_object(self.treeDic_settings, row=2, column=0)

        self.treeDic_settings.add_parameter('Power_ms_+1', -20, 
                                            type='float', step=1, 
                                            bounds=[-50,30], suffix=' dBm',
                                            tip='Constant power of the pi pulse of ms=+1')
        self.treeDic_settings.add_parameter('Frequency_ms_+1', 3, 
                                            type='float', step=0.1, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Frequency of the pi pulse of ms=+1')     
        self.treeDic_settings.add_parameter('dt_pi_pulse_ms_+1', 0.3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of pi pulse (RF) for ms=+1')         
        self.treeDic_settings.add_parameter('Power_ms_-1', -20, 
                                            type='float', step=1, 
                                            bounds=[-50,30], suffix=' dBm',
                                            tip='Constant power of the pi pulse of ms=-1')
        self.treeDic_settings.add_parameter('Frequency_ms_-1', 3, 
                                            type='float', step=0.1, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Frequency of the pi pulse of ms=-1')     
        self.treeDic_settings.add_parameter('dt_pi_pulse_ms_-1', 0.3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of pi pulse (RF) for ms=-1')   

        self.treeDic_settings.add_parameter('wait_time_switch_frequency' , 100, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='How much time it takes for the signal generator for switching frequency after the trigger.') 
        self.treeDic_settings.add_parameter('N_repeat_same_state', 3, 
                                            type='int', step=1, 
                                            bounds=[0,None],
                                            tip='Number of time to repeat the measure of one state at the same time before measuring the next state.\nThis is useful if it is long for switching frequency.') 

 
        self.treeDic_settings.add_parameter('t_in', 0, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Initialie time to probe') 
        self.treeDic_settings.add_parameter('t_end', 1, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Last time to probe')   
        self.treeDic_settings.add_parameter('N', 2, 
                                            type='int', step=10, 
                                            bounds=[0,None],
                                            tip='Number of points to sweep') 
        self.treeDic_settings.add_parameter('Spacing', ['Linear','Logarithmic'], 
                                            tip='Spacing between the points')         
        self.treeDic_settings.add_parameter('Log_factor', 4, 
                                            type='float', step=1, 
                                            bounds=[None,None],
                                            tip='Logarithmic factor for "how squeezed" the points are.\nThis takes effect only if Spacing is set to Logarithmic.')  


        self.treeDic_settings.add_parameter('dt_laser_initiate', 3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of laser for initiating into ms=0')  
        self.treeDic_settings.add_parameter('dt_wait_after_initiate', 1.1, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of time to wait between the laser initialization into ms=0 and the pi-pulse') 
        
        self.treeDic_settings.add_parameter('dt_readout', 0.4, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of the readout') 
        self.treeDic_settings.add_parameter('delay_read_before_laser', 0.05, 
                                            type='float', step=0.01, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Delay that we read before shining the laser')  
        
        self.treeDic_settings.add_parameter('DIO_laser', 2, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for the laser')          
        self.treeDic_settings.add_parameter('DIO_pulse_modulation', 3, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for modulating the pulse. AKA for sending the RF.')  
        self.treeDic_settings.add_parameter('DIO_change_frequency', 7, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for triggering the change in frequency')  
        self.treeDic_settings.add_parameter('DIO_sync_scope', 5, 
                                            type='int', step=1, 
                                            bounds=[-1,16],
                                            tip='DIO for synchronizing the oscilloscope. Put -1 for nothing')        
        
    def button_prepare_experiment_clicked(self):
        """
        Prepare the experiment:
            Prepare the pulse sequence in the fpga
            Prepare the signal generator
            Prepare the plot
        """
        _debug('GUIT1TimeTrace3: button_prepare_experiment_clicked')   
        
        # Prepare
#        self.prepare_pulse_sequence_V1()
        self.prepare_pulse_sequence_V2()
        
        # Compute and show some estimate
        self.compute_show_estimate()
        
        # Trigger a dummy function for signaling to prepare stuffs
        self.event_prepare_experiment()
        
    def prepare_pulse_sequence_V1(self):
        """
        Prepare the pulse sequence. 
        It generates the objet to be converted into a data array. 
        """
        _debug('GUIT1TimeTrace3: prepare_pulse_sequence')
        
        DIO_laser       = self.treeDic_settings['DIO_laser']
        DIO_PM          = self.treeDic_settings['DIO_pulse_modulation']
        DIO_sync        = self.treeDic_settings['DIO_sync_scope']
        DIO_change_freq = self.treeDic_settings['DIO_change_frequency']
        
        dt_laser      = self.treeDic_settings['dt_laser_initiate'] # Interval of time for shining the laser
        dt_readout    = self.treeDic_settings['dt_readout']
        dt_wait_ms0_pi= self.treeDic_settings['dt_wait_after_initiate'] #How much time to wait between ms=0 and pi pulse
        dt_pi_pulse_m1   = self.treeDic_settings['dt_pi_pulse_ms_-1'] # Duration of the pi-pulse for ms=-1
        dt_pi_pulse_p1   = self.treeDic_settings['dt_pi_pulse_ms_+1'] # Duration of the pi-pulse for ms=+1
        delay_read    = self.treeDic_settings['delay_read_before_laser'] # Delay (us) that we read before shining the laser
        self.tmin       = self.treeDic_settings['t_in'] # Minimum time  to probe
        self.tmax       = self.treeDic_settings['t_end'] # Maximum time  to probe        
        self.nb_block = self.treeDic_settings['N'] # Number of point to take      
        self.log_factor = self.treeDic_settings['Log_factor']
        self.N_repeat_same_state = self.treeDic_settings['N_repeat_same_state']
        wait_time_switch_frequency = self.treeDic_settings['wait_time_switch_frequency']
        
        # Finnally, here is a strong advantahe of this python approach. 
        # We have the option for a logarithmic spacing  
        if self.treeDic_settings['Spacing'] == 'Linear':
            self.t_probe_s = np.linspace(self.tmin  , self.tmax , self.nb_block)
        elif self.treeDic_settings['Spacing'] == 'Logarithmic':
            #Define the time to probe
            tlin = np.linspace(self.tmin  , self.tmax , self.nb_block) 
            tmin = self.tmin
            tmax = self.tmax
            #Transform it to a log scale
            beta  = self.log_factor/(tmax-tmin) #Factor for the logaritmic spacing (how squeezed will be the point near tmin) 
            B_log = (tmax-tmin)/(np.exp(beta*tmax)-np.exp(beta*tmin))
            A_log = tmin - B_log*np.exp(beta*tmin) 
            self.t_probe_s = A_log + B_log*np.exp(beta*tlin)  #Lograritmic spacing
            
        
        dt_sync_scope = 1   # Duration of the trigger for synchronizing the scope (us)
        dt_switch_f   = 100 # Duration of the trigger for switching the frequency on the signal generator
        

        # WE NOW BUILT THE SEQUENCE
        # To be efficient, we gonna use the laser for reading and as an 
        # initialization in ms=0 for the next measurement. 

        # Initiate the sequence on which we gonna construct
        sequence = Sequence(name='T1 3 states')

        # Create a channel for the trigger
        channel_sync = ChannelPulses(channel=DIO_sync, name='Sync oscilloscope')
        channel_sync.add_pulses([0, dt_sync_scope]) 
        

        
        # Create a block for each time to probe
        for i in range(len(self.t_probe_s)):
            t_probe = self.t_probe_s[i]
            
            # Each block will consist of three step: read ms0, 1 and -1
            
            # Laser channel for each ms state
            channel_laser = ChannelPulses(channel=DIO_laser, name='Laser')      
            # Read channel for each state
            channel_read  = ChannelPulses(channel=1, name='Read')
            # Channel for the Pi-pulse initializing ms=+1 and ms=-1
            channel_RF    = ChannelPulses(channel=DIO_PM , name='RF Pi pulse')
            # Channel for switching the frequency
            channel_switch_f = ChannelPulses(channel=DIO_change_freq, name='Switch frequency')        
            
            # Set the reference time
            t0 = dt_sync_scope

            # Switch the frequency now, because it might take a while
            # before it is effective. 
            t0_switch_f = t0 # Note when we started to switch
            channel_switch_f.add_pulses([t0_switch_f, t0_switch_f+dt_switch_f])
            
            # First prepare the state  ms=0 befiore the loop
            channel_laser.add_pulses([t0, t0+dt_laser])
            # Repeat the measurement of state ms=0
            for j in range(self.N_repeat_same_state):
                # Let evolve the state
                tref = channel_laser.get_pulses_times()[-1] + t_probe 
                # Read it. Start to read slightly a little bit before the laser is shone
                channel_read.add_pulses([tref - delay_read, tref + dt_readout])    
                
                # Shine the laser for both reading and for initializing into ms=0
                channel_laser.add_pulses([tref, tref+dt_laser])
        
                # Update the reference time
                t0 = channel_laser.get_pulses_times()[-1]
                
                # At this point, the state is ms=0
                
            # Make sure that enough time elapsed for the switching of the frequency
            if (t0 - t0_switch_f) < wait_time_switch_frequency:
                # If not enough time elapsed, update the reference time. 
                dt_supplementaire = wait_time_switch_frequency - (t0 - t0_switch_f)
                t0 = t0 + dt_supplementaire
                
            # Repeat the measurement of state ms=-1
            for j in range(self.N_repeat_same_state):
               #  At this point the state is ms=0
            
                # Let's flip the state
                # Note at which time to start the RF for flipping the state
                tref_RF = t0 + dt_wait_ms0_pi
                channel_RF.add_pulses([tref_RF, tref_RF + dt_pi_pulse_m1]) # Flip in ms=-1
                
                if j== (self.N_repeat_same_state-1):
                    # If it is the last pi pulse for this state
                    # Switch the frequency now, because it might take a while
                    # before it is effective. 
                    t0_switch_f = channel_RF.get_pulses_times()[-1] # It gonna start just after the pi-pulse
                    channel_switch_f.add_pulses([t0_switch_f, t0_switch_f+dt_switch_f])
                
                # Let evolve the state 
                tref = channel_RF.get_pulses_times()[-1] + t_probe
                # Read it. Start to read slightly a little bit before the laser is shone
                channel_read.add_pulses([tref - delay_read, tref + dt_readout])  
    
                # Shine the laser for both reading and for initializing into ms=0
                channel_laser.add_pulses([tref, tref+dt_laser])          

                # Update the reference time
                t0 = channel_laser.get_pulses_times()[-1]
                
                # At this point, the state is ms=0       
                
            # Make sure that enough time elapsed for the switching of the frequency
            if (t0 - t0_switch_f) < wait_time_switch_frequency:
                # If not enough time elapsed, update the reference time. 
                dt_supplementaire = wait_time_switch_frequency - (t0 - t0_switch_f)
                t0 = t0 + dt_supplementaire
                
            # Repeat the measurement of state ms=+1
            for j in range(self.N_repeat_same_state):
               #  At this point the state is ms=0
            
                # Let's flip the state
                # Note at which time to start the RF for flipping the state
                tref_RF = t0 + dt_wait_ms0_pi
                channel_RF.add_pulses([tref_RF, tref_RF + dt_pi_pulse_p1]) # Flip in ms=+1
                # Let evolve the state 
                tref = channel_RF.get_pulses_times()[-1] + t_probe
                # Read it. Start to read slightly a little bit before the laser is shone
                channel_read.add_pulses([tref - delay_read, tref + dt_readout])  
    
                # Shine the laser for both reading and for initializing into ms=0
                channel_laser.add_pulses([tref, tref+dt_laser])          
                
                #TODO uncomment for if we want a reference.
#                 If we do so, we gonna need to interpret the new counts from this!
#                if j == (self.N_repeat_same_state-1) :
#                    # If it is the last shining laser of the block
#                    # Re-read at the end for a reference
#                    tref = channel_laser.get_pulses_times()[-1] 
#                    channel_read.add_pulses([tref - dt_readout, tref]) 

                # Update the reference time
                t0 = channel_laser.get_pulses_times()[-1]
                
                
                
                # At this point, the state is ms=0                       
                
                
            # Add all that masterpiece to a block
            block = PulsePatternBlock(name='Block tprobe = %.2f us'%t_probe)
            block.add_channelEvents([channel_laser, 
                                     channel_RF, 
                                     channel_read,
                                     channel_switch_f])
            # Add the trigger for synchronizing the scope only on the first block
            if i ==0:
                block.add_channelEvents([channel_sync])
            
            # Add the block to the sequence
            sequence.add_block(block)             
            
        self.sequence =  sequence

    def prepare_pulse_sequence_V2(self):
        """
        Prepare the pulse sequence. 
        It generates the objet to be converted into a data array. 
        """
        _debug('GUIT1TimeTrace3: prepare_pulse_sequence_V2')
        
        
        DIO_laser   = self.treeDic_settings['DIO_laser']
        DIO_PM_p      = self.treeDic_settings['DIO_pulse_modulation_ms+1']
        DIO_PM_m      = self.treeDic_settings['DIO_pulse_modulation_ms-1']
        DIO_sync    = self.treeDic_settings['DIO_sync_scope']
        
        dt_laser      = self.treeDic_settings['dt_laser_initiate'] # Interval of time for shining the laser
        dt_readout    = self.treeDic_settings['dt_readout']
        dt_wait_ms0_pi= self.treeDic_settings['dt_wait_after_initiate'] #How much time to wait between ms=0 and pi pulse
        dt_pi_pulse_p   = self.treeDic_settings['dt_pi_pulse_ms+1'] # Duration of the pi-pulse
        dt_pi_pulse_m   = self.treeDic_settings['dt_pi_pulse_ms-1'] # Duration of the pi-pulse
        delay_read    = self.treeDic_settings['delay_read_before_laser'] # Delay (us) that we read before shining the laser
        self.tmin       = self.treeDic_settings['t_in'] # Minimum time  to probe
        self.tmax       = self.treeDic_settings['t_end'] # Maximum time  to probe        
        self.nb_block   = self.treeDic_settings['N'] # Number of point to take 
        self.log_factor = self.treeDic_settings['Log_factor']
        
        # Finnally, here is a strong advantahe of this python approach. 
        # We have the option for a logarithmic spacing  
        if self.treeDic_settings['Spacing'] == 'Linear':
            self.t_probe_s = np.linspace(self.tmin  , self.tmax , self.nb_block)
        elif self.treeDic_settings['Spacing'] == 'Logarithmic':
            #Define the time to probe
            tlin = np.linspace(self.tmin  , self.tmax , self.nb_block) 
            tmin = self.tmin
            tmax = self.tmax
            #Transform it to a log scale
            beta  = self.log_factor/(tmax-tmin) #Factor for the logaritmic spacing (how squeezed will be the point near tmin) 
            B_log = (tmax-tmin)/(np.exp(beta*tmax)-np.exp(beta*tmin))
            A_log = tmin - B_log*np.exp(beta*tmin) 
            self.t_probe_s = A_log + B_log*np.exp(beta*tlin)  #Lograritmic spacing
        
        dt_trigger = 1 # Duration of the trigger for synchronizing the scope (us)
        

        # Initiate the sequence on which we gonna construct
        sequence = Sequence(name='T1 3 states')

        # Create a channel for the trigger
        channel_sync = ChannelPulses(channel=DIO_sync, name='Sync oscilloscope')
        channel_sync.add_pulses([0, dt_trigger])  
        
        # Create a block for each time to probe
        for i in range(len(self.t_probe_s)):
            t_probe = self.t_probe_s[i]
            
            # Each block will consist of twos steps: read ms0, +-1 
            
            # Laser channel for each ms state
            channel_laser = ChannelPulses(channel=DIO_laser, name='Laser')      
            # Read channel for each state
            channel_read  = ChannelPulses(channel=1, name='Read')
            # Channel for the Pi-pulse initializing ms=+1
            channel_RF_p    = ChannelPulses(channel=DIO_PM_p , name='RF ms=+1')
            # Channel for the Pi-pulse initializing ms=-1
            channel_RF_m    = ChannelPulses(channel=DIO_PM_m , name='RF ms=-1')
            
            # Prepare and read ms=0
            if i==0:
                # Prepare it on the first block only. For the next block, 
                # we use the last readout for the initialization
                # Prepare the state
                channel_laser.add_pulses([dt_trigger, dt_trigger+dt_laser])
                # Let evolve the state
                tref = channel_laser.get_pulses_times()[-1] + t_probe 
            else:
                # We only wait for the prob time.
                tref = t_probe
                
            # Read it. Start to read slightly a little bit before the laser if shone
            channel_read.add_pulses([tref - delay_read, tref + dt_readout])   
            # Shine the laser for both reading and for initializing into ms=0
            channel_laser.add_pulses([tref, tref+dt_laser])
            
            # At this point the state is ms=0 and t = tref
            
            # Prepare and read ms=+1
            # Note at which time to start the RF for flipping the state
            tref_RF = channel_laser.get_pulses_times()[-1] + dt_wait_ms0_pi
            channel_RF_p.add_pulses([tref_RF, tref_RF + dt_pi_pulse_p]) # Flip in ms=-1
            # Let evolve the state 
            tref = channel_RF_p.get_pulses_times()[-1] + t_probe
            # Read it. Start to read slightly a little bit before the laser if shone
            channel_read.add_pulses([tref - delay_read, tref + dt_readout])  
            # Shine the laser for reading 
            channel_laser.add_pulses([tref, tref+dt_laser])            

            # At this point the state is ms=0 and t = tref
            
            # Prepare and read ms=-1
            # Note at which time to start the RF for flipping the state
            tref_RF = channel_laser.get_pulses_times()[-1] + dt_wait_ms0_pi
            channel_RF_m.add_pulses([tref_RF, tref_RF + dt_pi_pulse_m]) # Flip in ms=-1
            # Let evolve the state 
            tref = channel_RF_m.get_pulses_times()[-1] + t_probe
            # Read it. Start to read slightly a little bit before the laser if shone
            channel_read.add_pulses([tref - delay_read, tref + dt_readout])  
            # Shine the laser for reading 
            channel_laser.add_pulses([tref, tref+dt_laser])  
            
            # Re-read at the end of the shining as a reference
            tref = channel_laser.get_pulses_times()[-1] 
            channel_read.add_pulses([tref - dt_readout, tref])             
            
            
            
            # Add all that masterpiece to a block
            block = PulsePatternBlock(name='Block tprobe = %.2f us'%t_probe)
            block.add_channelEvents([channel_laser, 
                                     channel_RF_p,
                                     channel_RF_m,
                                     channel_read])
            # Add the trigger for synchronizing the scope only on the first block
            if i ==0:
                block.add_channelEvents([channel_sync])
            
            # Add the block to the sequence
            sequence.add_block(block)             
            
        self.sequence =  sequence

    def databoxplot_update(self):
        """
        Update the plot
        """
        _debug('GUIT1TimeTrace2: databoxplot_update')
        # Clear the plot
        self.databoxplot.clear() 
        
                
        self.databoxplot['Time_(us)'] = self.t_probe_s
        # Loop over each readout 
        for i, count_per_readout in enumerate(self.counts_total):
            # Create a curve
            self.databoxplot['Total_counts_%d'%i] = count_per_readout
            
        # Show it
        self.databoxplot.plot()   
        
    def after_one_loop(self, counts, iteration, rep):
        """
        What to do after one loop of the fpga. 

        This is called after each loop (single run) of the fpga. 
        
        counts:
            Array of counts that the fpga get. 
        iteration:
            int corresponding to which iteration are we at
            
        rep:
            Number of repetition of the sequence into the fpga instruction
            """
        _debug('GUIT1TimeTrace2: after_one_loop')
        
        # Get the counts per readout per block
        self.count_processor = _fc.ProcessFPGACounts(counts)
        self.block_ind, self.counts = self.count_processor.get_count_per_readout_vs_block(rep, self.nb_block)

#        print(self.counts)
        # If its the first iteration
        if iteration == 0:
            # Get the count and the correct shape for the array
            self.counts_total = np.array(self.counts)  
        else:
            # Increment the counts
            self.counts_total += np.array(self.counts)  
            
        # Update the plot
        self.databoxplot_update()
        
#    def databoxplot_update(self):
#        """
#        Update the plot
#        """
#        _debug('GUIT1TimeTrace3: databoxplot_update')
#        # Clear the plot
#        self.databoxplot.clear() 
#                
#        self.databoxplot['Time_(us)'] = self.t_probe_s
#        # Loop over each readout 
#        for i, count_per_readout in enumerate(self.counts_total):
#            # Create a curve
#            self.databoxplot['Total_counts_%d'%i] = count_per_readout
#        # Show it
#        self.databoxplot.plot()   
#        
#    def after_one_loop(self, counts, iteration, rep):
#        """
#        What to do after one loop of the fpga. 
#
#        This is called after each loop (single run) of the fpga. 
#        
#        counts:
#            Array of counts that the fpga get. 
#        iteration:
#            int corresponding to which iteration are we at
#            
#        rep:
#            Number of repetition of the sequence into the fpga instruction
#            """
#        _debug('GUIT1TimeTrace3: after_one_loop')
#        
#        # Get the counts per readout per block
#        self.count_processor = _fc.ProcessFPGACounts(counts)
#        
#        # Since we repeated the measurements for each state, many counts
#        # refer to the same state. Therefore we need to split this. 
#        
#        # Get the array of counts 
#        self.counts_per_block_s =  self.count_processor.get_sum_count_per_block(rep, self.nb_block)
#        
#        # For each block, we gonna have to sum up each batch of measurement. 
#        self.count_vs_block_ms0  = np.zeros(self.nb_block) # Store the total count for each block
#        self.count_vs_block_msm1 = np.zeros(self.nb_block) # Store the total count for each block
#        self.count_vs_block_msp1 = np.zeros(self.nb_block) # Store the total count for each block
#        for i, counts_per_block in enumerate(self.counts_per_block_s):
#            # Let's decompose each block for which measurement it correspond to
#            # And sum each batch of measurement. 
#            self.count_ms0  = np.sum( counts_per_block[                         0 :   self.N_repeat_same_state] )
#            self.count_msm1 = np.sum( counts_per_block[  self.N_repeat_same_state : 2*self.N_repeat_same_state] )
#            self.count_msp1 = np.sum( counts_per_block[2*self.N_repeat_same_state : 3*self.N_repeat_same_state] )
#            # Note the total count for this block
#            self.count_vs_block_ms0[i]  = self.count_ms0
#            self.count_vs_block_msm1[i] = self.count_msm1
#            self.count_vs_block_msp1[i] = self.count_msp1
#            
#        # Structure the counts for the rest of the code
#        self.counts = [self.count_vs_block_ms0,
#                       self.count_vs_block_msm1,
#                       self.count_vs_block_msp1]
#            
#
#        
#
##        print(self.counts)
#        # If its the first iteration
#        if iteration == 0:
#            # Get the count and the correct shape for the array
#            self.counts_total = np.array(self.counts)  
#        else:
#            # Increment the counts
#            self.counts_total += np.array(self.counts)  
#            
#        # Update the plot
#        self.databoxplot_update()
        
    def event_prepare_experiment(self): 
        """
        Dummy function to be overrid
        This is was should be done after that the pulse sequence is defined. 
        """        
        return         
    
    def compute_show_estimate(self):
        """
        Compute and show some estimate for the pulse sequence. 
        """
        _debug('GUIT1TimeTrace3: compute_show_estimate')
        
        # See notebook of Michael Caouette-Mansour on July 24 2020 for details 
        # of how the minimum time is estimated
        
        # Compute roughly the total time for a single sequence. 
        # This is assuming that the dominating time are the times to probe
        # Multiply by 3 because we do it three time, for each ms state
        T_seq = 3* ( 0.5*(self.nb_block+1)*self.tmax + 0.5*(self.nb_block-1)*self.tmin )
        
        C0 = 0.04 # Mean count per each readout for ms=0
        c  = 0.1  # Contrast between the states
        C1 = C0*(1-c) # Mean count per readout for ms=+-1
        
        # Compute the minimum number of readout for distinguishing the states
        N_min = (np.sqrt(C0) + np.sqrt(C1))**2/(C0-C1)**2
        
        T_minimum = T_seq*N_min # Minimum elapsed time before distinguishing the states
        
        # It should be in us. Let's convert it in minutes
        T_minutes = T_minimum*1e-6/60 
        
        # Set the text and the label
        text =   'Assuming %0.3f count per readout on state ms=0.'%C0
        text+= '\nAssuming %0.3f count per readout on state ms=+-1.'%C1
        text+= '\nNote that the contrast is %0.1f percente'%c
        text+='\nIt should take %d readout before distinguishing those states'%N_min
        text+='\nWith the current sequence, this should take at least %0.2f minutes'%T_minutes
        self.label_estimates.set_text(text)        
  
      
class GUIT1probeOneTime(egg.gui.Window):
    """
    GUI for preparing the states and let them decay until a single time.
    """   
    
    def __init__(self, name="Single probe T1", size=[1000,500]): 
        """
        Initialize
        """    
        _debug('GUIT1probeOneTime:__init__')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Initialise the GUI
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIT1probeOneTime: initialize_GUI')
        _debug('Punctuality is not just limited to arriving at a place at right time, it is also about taking actions at right time. ― Amit Kalantri')
        
        # A button for preparing stuff
        self.button_prepare_experiment = egg.gui.Button('Prepare',
                                                        tip='Prepare the measurement before running')
        self.place_object(self.button_prepare_experiment, row=1, column=0)
        self.connect(self.button_prepare_experiment.signal_clicked, 
                     self.button_prepare_experiment_clicked)
            
        # A button for preparing stuff
        self.button_prepare_experiment = egg.gui.Button('Prepare',
                                                        tip='Prepare the measurement before running')
        self.place_object(self.button_prepare_experiment, row=1, column=0)
        self.connect(self.button_prepare_experiment.signal_clicked, 
                     self.button_prepare_experiment_clicked)
            
        # tree dictionnarry for the settings
        self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_T1_singleTime')
        self.place_object(self.treeDic_settings, row=2, column=0)

        self.treeDic_settings.add_parameter('Power', -20, 
                                            type='float', step=1, 
                                            bounds=[-50,30], suffix=' dBm',
                                            tip='Constant power of the RF')
        self.treeDic_settings.add_parameter('Frequency', 3, 
                                            type='float', step=0.1, 
                                            bounds=[0,10], suffix=' GHz',
                                            tip='Frequency of the RF') 
        
        self.treeDic_settings.add_parameter('t_probe', 10, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Time to probe.') 

        self.treeDic_settings.add_parameter('dt_pi_pulse_ms+1', 0.3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of pi pulse for ms=+1(RF)') 
        self.treeDic_settings.add_parameter('dt_pi_pulse_ms-1', 0.3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of pi pulse for ms=-1(RF)') 
        
        self.treeDic_settings.add_parameter('dt_laser_initiate', 3, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of laser for initiating into ms=0')  
        self.treeDic_settings.add_parameter('dt_wait_after_initiate', 1.1, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of time to wait between the laser initialization into ms=0 and the pi-pulse') 
        
        self.treeDic_settings.add_parameter('dt_readout', 0.4, 
                                            type='float', step=0.1, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Duration of the readout') 
        self.treeDic_settings.add_parameter('delay_read_before_laser', 0.05, 
                                            type='float', step=0.01, 
                                            bounds=[0,None], suffix=' us',
                                            tip='Delay that we read before shining the laser')  
        
        self.treeDic_settings.add_parameter('DIO_laser', 2, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for the laser')          
        self.treeDic_settings.add_parameter('DIO_pulse_modulation_ms+1', 3, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for modulating the pi pulse of ms=+1. AKA for sending the RF.')  
        self.treeDic_settings.add_parameter('DIO_pulse_modulation_ms-1', 4, 
                                            type='int', step=1, 
                                            bounds=[0,16],
                                            tip='DIO for modulating the pi pulse of ms=-1. AKA for sending the RF.')  

        self.treeDic_settings.add_parameter('DIO_sync_scope', 5, 
                                            type='int', step=1, 
                                            bounds=[-1,16],
                                            tip='DIO for synchronizing the oscilloscope. Put -1 for nothing')

        # Add a Data Box plotter for the incoming data
        self.databoxplot = egg.gui.DataboxPlot(autosettings_path='plot_probeOneTime')
        self.place_object(self.databoxplot, row=2, column = 1, row_span=2) 
        self.databoxplot.button_multi.set_value(False) # Make all on the same plot
        
        # Make a label for showing some estimate
        self.label_estimates = egg.gui.Label('We have the best T1 prober on the market.')
        self.place_object(self.label_estimates, row=2, column=2)        

    def button_prepare_experiment_clicked(self):
        """
        Prepare the experiment:
            Prepare the pulse sequence in the fpga
            Prepare the signal generator
            Prepare the plot
        """
        _debug('GUIT1probeOneTimes: button_prepare_experiment_clicked')   

        # Prepare the sequence accoring to the best knowledge that we have so far. 
        self.prepare_pulse_sequence()
        
        # Trigger a dummy function for signaling to prepare stuffs
        self.event_prepare_experiment()
        
       
        
    def prepare_pulse_sequence(self):
        """
        Prepare the pulse sequence. 
        It generates the objet to be converted into a data array. 
        """
        _debug('GUIT1probeOneTimes: prepare_pulse_sequence')
        
        DIO_laser         = self.treeDic_settings['DIO_laser']
        DIO_PM_p          = self.treeDic_settings['DIO_pulse_modulation_ms+1']
        DIO_PM_m          = self.treeDic_settings['DIO_pulse_modulation_ms-1']
        DIO_sync          = self.treeDic_settings['DIO_sync_scope']
        
        dt_laser      = self.treeDic_settings['dt_laser_initiate'] # Interval of time for shining the laser
        dt_readout    = self.treeDic_settings['dt_readout']
        dt_wait_ms0_pi= self.treeDic_settings['dt_wait_after_initiate'] #How much time to wait between ms=0 and pi pulse
        dt_pi_pulse_m1   = self.treeDic_settings['dt_pi_pulse_ms-1'] # Duration of the pi-pulse for ms=-1
        dt_pi_pulse_p1   = self.treeDic_settings['dt_pi_pulse_ms+1'] # Duration of the pi-pulse for ms=+1
        delay_read    = self.treeDic_settings['delay_read_before_laser'] # Delay (us) that we read before shining the laser 
            
        self.t_probe = self.treeDic_settings['t_probe']
        
        dt_sync_scope = 1   # Duration of the trigger for synchronizing the scope (us)
        
        # WE NOW BUILT THE SEQUENCE
        # To be efficient, we gonna use the laser for reading and as an 
        # initialization in ms=0 for the next measurement. 

        # Initiate the sequence on which we gonna construct
        sequence = Sequence(name='T1 3 states at single probing time')

        # Create a channel for the synchronization with the scope. 
        channel_sync = ChannelPulses(channel=DIO_sync, name='Sync oscilloscope')
        channel_sync.add_pulses([0, dt_sync_scope]) 
        
        # We gonna do three steps: iniate and read ms0, 1 and -1
        
        # Laser channel for each ms state
        channel_laser = ChannelPulses(channel=DIO_laser, name='Laser')      
        # Read channel for each state
        channel_read  = ChannelPulses(channel=1, name='Read')
        # Channel for the Pi-pulse initializing ms=+1 
        channel_RF_p    = ChannelPulses(channel=DIO_PM_p , name='Pi pulse ms+1')
        # Channel for the Pi-pulse initializing ms=-1 
        channel_RF_m    = ChannelPulses(channel=DIO_PM_m , name='Pi pulse ms-1')      
        
        # Set the reference time
        t0 = dt_sync_scope

        # First prepare the state  ms=0 
        channel_laser.add_pulses([t0, t0+dt_laser])
        
        # Let evolve the state
        tref = channel_laser.get_pulses_times()[-1] + self.t_probe
        
        # Read it. Start to read slightly a little bit before the laser is shone
        channel_read.add_pulses([tref - delay_read, tref + dt_readout])    
        
        # Shine the laser for both reading and for initializing into ms=0
        channel_laser.add_pulses([tref, tref+dt_laser])

        # Update the reference time
        t0 = channel_laser.get_pulses_times()[-1]
            
        # At this point, the state is ms=0
        
        # Let's flip the state into ms=-1
        # Note at which time to start the RF for flipping the state
        tref_RF = t0 + dt_wait_ms0_pi
        # Send the pi-pulse
        channel_RF_m.add_pulses([tref_RF, tref_RF + dt_pi_pulse_m1]) # Flip in ms=-1
        
        # Let evolve the state 
        tref = channel_RF_m.get_pulses_times()[-1] + self.t_probe 
        # Read it. Start to read slightly a little bit before the laser is shone
        channel_read.add_pulses([tref - delay_read, tref + dt_readout])  

        # Shine the laser for both reading and for initializing into ms=0
        channel_laser.add_pulses([tref, tref+dt_laser])          

        # Update the reference time
        t0 = channel_laser.get_pulses_times()[-1]
                
        # At this point, the state is ms=0       
            
        # Let's flip the state into ms=+1
        # Note at which time to start the RF for flipping the state
        tref_RF = t0 + dt_wait_ms0_pi
        # Send the pi-pulse
        channel_RF_p.add_pulses([tref_RF, tref_RF + dt_pi_pulse_p1]) # Flip in ms=-1
        # Let evolve the state 
        tref = channel_RF_p.get_pulses_times()[-1] + self.t_probe   
        # Read it. Start to read slightly a little bit before the laser is shone
        channel_read.add_pulses([tref - delay_read, tref + dt_readout])  

        # Shine the laser for both reading and for initializing into ms=0
        channel_laser.add_pulses([tref, tref+dt_laser])          
        
        # Read again at the end for the reference
        t0 = channel_laser.get_pulses_times()[-1]
        channel_read.add_pulses([t0 - dt_readout, t0])  


                
                
                
        # Add all that masterpiece to a block
        block = PulsePatternBlock(name='Block tprobe = %.2f us'%self.t_probe)
        block.add_channelEvents([channel_laser, 
                                 channel_RF_p, 
                                 channel_RF_m,
                                 channel_read])
        # Add the trigger for synchronizing the scope only on the first block
        block.add_channelEvents([channel_sync])
        
        # Add the block to the sequence
        sequence.add_block(block)             
            
        self.sequence =  sequence

    def databoxplot_update(self):
        """
        Update the plot
        """
        _debug('GUIT1probeOneTimes: databoxplot_update')
        
        
        # Clear the plot
        self.databoxplot.clear() 
        
        # Feed the databox plot with the data
        self.databoxplot['ms0']  = self.count_per_iter_ms0_s
        self.databoxplot['ms-1'] = self.count_per_iter_msm1_s
        self.databoxplot['ms+1'] = self.count_per_iter_msp1_s
        self.databoxplot['ref']  = self.count_per_iter_ref_s
        
            
        # Show it
        self.databoxplot.plot()   
        
    def after_one_loop(self, counts, iteration, rep):
        """
        What to do after one loop of the fpga. 

        This is called after each loop (single run) of the fpga. 
        
        counts:
            Array of counts that the fpga get. 
        iteration:
            int corresponding to which iteration are we at
            
        rep:
            Number of repetition of the sequence into the fpga instruction
            """
        _debug('GUIT1probeOneTimes: after_one_loop')
        
        # Get the counts per readout per block
        self.count_processor = _fc.ProcessFPGACounts(counts)
        
        # We only have one block we 4 readout in it. 
        
        # Get the array of counts 
        self.counts_per_block_s =  self.count_processor.get_sum_count_per_block(rep, 1)
        
        # Get the number of counts for each measurement
        self.counts_ms0  = self.counts_per_block_s[0][0]
        self.counts_msm1 = self.counts_per_block_s[0][1]
        self.counts_msp1 = self.counts_per_block_s[0][2]
        self.counts_ref  = self.counts_per_block_s[0][3]
        
        # If its the first iteration
        if iteration == 0:
            # Note the total number of readout for each state
            self.total_nb_readout = rep
            # Get the summed count per iteration
            self.count_per_iter_ms0_s  = [self.counts_ms0 ]
            self.count_per_iter_msm1_s = [self.counts_msm1]
            self.count_per_iter_msp1_s = [self.counts_msp1]
            self.count_per_iter_ref_s  = [self.counts_ref ]
        else:
            # Note the total number of readout for each state
            self.total_nb_readout += rep
            # Appened the summed count per iteration
            self.count_per_iter_ms0_s .append( self.counts_ms0)
            self.count_per_iter_msm1_s.append( self.counts_msm1)
            self.count_per_iter_msp1_s.append( self.counts_msp1)
            self.count_per_iter_ref_s .append( self.counts_ref)
        
        # Update the plot
        self.databoxplot_update()
            
        # Update the label
        self.mean_count_per_readout_ms0  = np.sum(self.count_per_iter_ms0_s)/rep/iteration
        self.mean_count_per_readout_msm1 = np.sum(self.count_per_iter_msm1_s)/rep/iteration
        self.mean_count_per_readout_msp1 = np.sum(self.count_per_iter_msp1_s)/rep/iteration
        self.mean_count_per_readout_ref  = np.sum(self.count_per_iter_ref_s)/rep/iteration
        
        text = (  'Mean count per readout'+
                '\nms0  : %f'%self.mean_count_per_readout_ms0 +
                '\nms-1 : %f'%self.mean_count_per_readout_msm1 +
                '\nms+1 : %f'%self.mean_count_per_readout_msp1 +
                '\nref  : %f'%self.mean_count_per_readout_ref)
        self.label_estimates.set_text(text)
        
        
    def event_prepare_experiment(self): 
        """
        Dummy function to be overrid
        This is was should be done after that the pulse sequence is defined. 
        """        
        return         
     
    
if __name__ == '__main__':
    _fc._debug_enabled = False
    _debug_enabled     = True


     # Create the fpga api
    bitfile_path = ("X:\DiamondCloud\Magnetometry\Acquisition\FPGA\Magnetometry Control\FPGA Bitfiles"
                    "\Pulsepattern(bet_FPGATarget_FPGAFULLV2_WZPA4vla3fk.lvbitx")
    resource_num = "RIO0"     
    
    fpga = _fc.FPGA_api(bitfile_path, resource_num) # Create the api   
    fpga.open_session()
    self = GuiMainPulseSequence(fpga) 
    self.show()

    
#    fpga_fake = _fc.FPGA_fake_api(bitfile_path, resource_num) # Create the api   
#    fpga_fake.open_session()
#    
#    self = GuiMainPulseSequence(fpga_fake) 
#    self.show()
    
#    self = GUIESR()
#    self.show()
#    
#    self = GUIPulseBuilder()
#    self.show()
    
#    self = GUIT1probeOneTime()
#    self.show()
#    # Show the pulse pattern
#    GUIPulsePattern(self.sequence)       























