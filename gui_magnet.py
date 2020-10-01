# -*- coding: utf-8 -*-
"""
Created on Fri Aug 21 10:41:45 2020

@author: Childresslab
"""

from api_actuator import ApiActuator

from analysis_mag_sweep_lines import plot_magSweepLinesResult
from prepare_mag_sweep_lines import plot_magSweepLinesSettings 
import spinmob     as _s
from spinmob import egg
import time
import mcphysics   as _mp
import numpy as np
from converter import Converter # This convert the sequence object into fpga data
import api_fpga as _fc # For using the FPGA
import gui_confocal_optimizer #For sing the optimizer

import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error

#Debug
_debug_enabled           = False






def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))


class GUISingleActuator(_mp.visa_tools.visa_gui_base):
    """
    Graphical front-end for the actuator.
    
    Parameters
    ----------
    name='Anapico'
        Make this unique for each object in a larger project. This 
        will also be the first part of the filename for the other settings files.
   
    show=True
        Whether to show the window immediately.
         
    block=False
        Whether to block the command line while showing the window.
    
    pyvisa_py=False
        Whether to use pyvisa_py or not.
    """

    def __init__(self, name='Actuator', show=True, block=False, timeout=2e3, write_sleep=0.1, pyvisa_py=False):
        _debug('GUISingleActuator.__init__()')
        
        # Run the basic stuff.
        _mp.visa_tools.visa_gui_base.__init__(self, name, show, block, ApiActuator, timeout=timeout, write_sleep=write_sleep, pyvisa_py=pyvisa_py, hello_query='1VE?', baud_rate=921600)
    
        #Give a name to the GUI, for helping debugging
        self.name = 'Bibi'
    
        # Add stuff to the GUI.
        #On the top
        self.button_reset       = self.grid_top.add(egg.gui.Button('Reset', checkable=True)).set_width(60).disable()
        self.button_state       = self.grid_top.add(egg.gui.Button('State', checkable=True)).set_width(75).disable()
        self.button_move        = self.grid_top.add(egg.gui.Button('Move', checkable=True)).set_width(100).disable()
        self.button_stop        = self.grid_top.add(egg.gui.Button('STOP', checkable=True, )).set_width(100).enable()
        self.button_stop.set_colors(text='red', background='yellow') #Be fancy
        #Elsewhere
        self.label_position     = self.grid_top.place_object(egg.gui.Label('Position = XX mm'), 0,1,column_span=2)
        self.label_state        = self.grid_top.place_object(egg.gui.Label('State = LOL'), 2,1,column_span=2)  
        self.label_name        = self.grid_top.place_object(egg.gui.Label('Name = '+self.name), 4,1,column_span=1)  
        
        #This is some setting
        self.settings.add_parameter('Motion/Target_position', bounds=(0,25), suffix=' mm')
        self.settings.add_parameter('Motion/Speed'          , bounds=(0,2) , suffix=' units/sec')
        
        
        #Add a timer for some update when the actuator moves
        self.timer_moving = egg.gui.Timer(interval_ms=500, single_shot=False)
        self.timer_moving._widget.timeout.connect( self._update ) #Each time it tick, it gonna do the function self._update
        
        # Place the instrument name at a more convient place
        self.grid_top.place_object(self.label_instrument_name,0,2,column_span=1)
        
        #Connection of the button to the function
        self.button_state           .signal_toggled.connect(self._button_state_toggled)
        self.button_reset           .signal_toggled.connect(self._button_reset_toggled)
        self.button_move            .signal_toggled.connect(self._button_move_toggled)
        self.button_stop            .signal_toggled.connect(self._button_stop_toggled)
        self.button_connect         .signal_toggled.connect(self._update)
        
        #Enable the button, set them weither they are checked or not. 
        self.button_state.set_checked(False,  block_events=True).enable()
        self.button_reset.set_checked(False,  block_events=True).enable()
        self.button_move .set_checked(False,  block_events=True).enable()
           
        
    def set_name(self, name):
        """
        Set the name of the GUI
        """
        self.name = name
        #Update the name in the GUI
        self.label_name.set_text('Name = '+name)
        
    def get_name(self):
        """
        Get the name of the GUI
        """
        return self.name
        
    def _button_reset_toggled(self, *a):
        """
        Reset the actuator. 
        WARNING: this will put back the actuator in position 0. 
        """
        _debug('GUISingleActuator.button_reset_toggled()')
        
        self.timer_moving.start() #It's gonna move, so update
        self.api.reset()
        #Put back the button unchecked
        self.button_reset.set_checked(False,  block_events=True).enable()
        
    def _button_state_toggled(self, *a):
        """
        Update the state of the actuator. This calls self._update()
        """
        _debug('GUISingleActuator._button_state_toggled()')
        
        #Update
        self._update()
        #Put it back unchecked
        self.button_state.set_checked(False,  block_events=True).enable()
        
    def _button_move_toggled(self, *a):
        """
        Move the actuator to position set by the parameter Motion/Target_position
        """
        _debug('GUISingleActuator._button_move_toggled()')
        
        #Set the velocity
        v = self.settings['Motion/Speed'] #Extract the velocity from the parameters
        self.api.set_velocity(v)
        #Set the position
        r = self.settings['Motion/Target_position'] #Extract the position from the parameters
        self.api.set_position_abs(r)
        
        #Start to udpate
        self.timer_moving.start()
        
    def _button_stop_toggled(self, *a):
        """
        Stop the motion of the actuator !
        """
        _debug('GUISingleActuator._button_stop_toggled()')
        
        self.api.stop_motion()
        self._update() #udpate the state
        self.button_stop.set_checked(value=False) #Make it 'Clickable' again 
    
    def _update(self):
        """
        Update the information shown.
        """
        _debug('GUISingleActuator._update()')
        
        #Update only if the api exist
        if self.api != None: 
            #Update the position of the actuator.
            strpos = 'Position = ' + str(self.api.get_position()) + ' mm'
            self.label_position.set_text(strpos)
            _debug(strpos) 
            #Update the state         
            strState = 'State = ' + self.api.get_state()
            self.label_state.set_text(strState)
            _debug(strState) 
            
            #If the actuator doesn't move or is not homing. 
            cond1 = 'MOVING' == self.api.get_state()
            cond2 = 'HOMING' == self.api.get_state()
            if not(cond1 or cond2):
                #Stop to trigger the update with the timer
                self.timer_moving.stop()
                #Also uncheck the move button if there is not motion
                self.button_move .set_checked(False,  block_events=True).enable()
                
                
class GUIMagnet(egg.gui.Window):
    """
    Class that combines 3 actuator GUIs in order to control the position of the magnet.  
    """
    
    def __init__(self, fpga, optimizer=-1,
                 name='Magnet', size=[1300,800]):
        """
        Create the GUI 
        
        fpga:
            "FPGA_api" object from api_fpga.py. 
            This is the object shared amoung the GUIs for controlling the fpga. 
            The session of the fpga must already be open.    
        optimizer:
            GUIOptimizer class object. It is for dealing with the optimization
            during the run of the pulse sequence. This object should be the 
            optimizer used in the higher level gui. Taking it as an input is
            just allowing us to use its functionnalities. 
            If it is set to -1, there will be just nothing happening when it 
            is time to optimize. 
            
        """
        _debug('GUIMagnet.__init__()', name)
        _debug('Success is going from failure to failure without losing your enthusiasm – Winston Churchill')

        # Get the inputs
        self.fpga = fpga           
        self.optimizer = optimizer

        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Remember the name. It is important a name, you know. 
        self.name = name
        
        #Save path to save file (useful when this GUI is inside probe_station)
        self.path_save_file = ''
                
        
        #Create the instance for the three actuator
        self.X = GUISingleActuator(show=False)
        self.X.settings['VISA/Device'] = 'COM5'
        self.X.set_name('Super-X')
        self.Y = GUISingleActuator(show=False)
        self.Y.settings['VISA/Device'] = 'COM4'
        self.Y.set_name('Mega-Y')
        self.Z = GUISingleActuator(show=False)
        self.Z.settings['VISA/Device'] = 'COM3'
        self.Z.set_name('Ultra-Z')

        # Add three actuator GUI
        self.place_object(egg.gui.Label('X: '), 0,0) #Set the label at position (0,0)
        self.place_object(self.X.window)
        self.new_autorow()
        self.place_object(egg.gui.Label('Y: '), 0,1) #Set the label at position (0,1)
        self.place_object(self.Y.window)
        self.new_autorow()
        self.place_object(egg.gui.Label('Z: '), 0,2) #Set the label at position (0,2)
        self.place_object(self.Z.window)
        
        # Place tabs for different task
        self.tabs1 = self.place_object(egg.gui.TabArea(), 
                                       row=0, column=1,
                                       column_span=5,  row_span=10,
                                       alignment=0)

        # Tab for sweeping lines
        self.gui_sweep_lines = GUIMagnetSweepLines(self, self.fpga, self.optimizer)
        self.tab_sweep_lines = self.tabs1.add_tab('Sweep lines')
        self.tab_sweep_lines.place_object(self.gui_sweep_lines, alignment=0)   
        
        # Tab for the list sweep
        self.gui_list_sweep = GUIMagnetSweepList(self)
        self.tab_list_sweep = self.tabs1.add_tab('List sweep')
        self.tab_list_sweep.place_object(self.gui_list_sweep, alignment=0)  
        


        
    def go_to_xyz(self, x, y, z, want_wait=False):
        """
        Go to x, y, z (in mm)
        
        want_wait:
            (boolean) Weither of not we want to wait before it finishes
        """
        _debug('GUIMagnet: go_to_xyz'  )
               
        # Set the target positions
        self.X.settings['Motion/Target_position'] = x
        self.Y.settings['Motion/Target_position'] = y
        self.Z.settings['Motion/Target_position'] = z       
        
        # Go for real
        self.X.button_move.click()
        self.Y.button_move.click()
        self.Z.button_move.click()

        if want_wait:
            #Wait that the actuators finished to move. 
            condition = True
            while condition:
                # Wait for not exploding the CPU
                time.sleep(0.1)
                 #Allow the GUI to update. This is important to avoid freezing of the GUI inside loop
                self.process_events()
                # Note the condition for keeping doing
                # As long as the three actuator move
                condition1 = self.X.api.get_state() == 'MOVING'
                condition2 = self.Y.api.get_state() == 'MOVING'
                condition3 = self.Z.api.get_state() == 'MOVING'
                condition = condition1 or condition2 or condition3
            


class GUIMagnetSweepLines(egg.gui.Window):
    """
    Gui for making the actuator to sweep along various lines. 
    """
    def __init__(self, magnet3, fpga, optimizer=-1,
                 name='Magnet sweep lines', show=True,size=[1300,600]):
        """
        Create the GUI 
        
        magnet3:
            The gui object "GUIMagnet" that is used to control the three 
            actuators. 
        fpga:
            "FPGA_api" object from api_fpga.py. 
            This is the object shared amoung the GUIs for controlling the fpga. 
            The session of the fpga must already be open.    
        optimizer:
            GUIOptimizer class object. It is for dealing with the optimization
            during the run. This object should be the optimizer used in the 
            higher level gui. Taking it as an input is just allowing us to use 
            its functionnalities. 
            If it is set to -1, there will be just nothing happening when it 
            is time to optimize. 
            
        """
        _debug('GUIMagnetSweepLines: __init__')
        _debug('The best way to predict your future is to create it. – Abraham Lincoln')
        
        # Take the inputs
        self.magnet   = magnet3 # Steal the magnet gui, mouahhaha
        self.fpga     = fpga
        self.optimizer = optimizer
        
        
        # Get each axis component for saving precious characters lol
        self.X = magnet3.X
        self.Y = magnet3.Y
        self.Z = magnet3.Z
        
        # Some useful attribute
        self.is_running = False # Tell is the sweep is running
        self.iter = 0 # At which iteration we are on
        self.nb_iter = 0 # How many iteration to perform (number of lines to scan)
        self.path_setting = 'Data: No File loaded ;)' # This is the string for the path of the data
        self.statut = 'Waiting for settings.' # This will inform where we are in the tasks
        self.data_w = 0 # This is the 4-dimensional data to take at each magnet posiiont. Example: the photo-counts at each position. 
        self.info_date = 'No scan' # String for the data at which the scan is done
        self.speed = 999 # This gonna be the speed along the line
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)

        # A Button for starting the line sweep
        self.button_run = self.place_object(egg.gui.Button('Start'), 
                                            0,0, alignment=1)
        self.button_run.disable() # Disable until we have imported or set the settings
        self.connect(self.button_run.signal_clicked, self.button_run_clicked )  
        
        # A Button for resetting the sweep
        self.button_reset = self.place_object(egg.gui.Button('Reeeset'), 
                                              0,1, alignment=1)
        self.connect(self.button_reset.signal_clicked, self.button_reset_clicked )
        
        #Add a button for loading the data
        self.button_load_settings = self.place_object(egg.gui.Button('Load settings'),
                                                  1,0, alignment=1)
        self.connect(self.button_load_settings.signal_clicked, self.button_load_settings_clicked )
        #Add a button for looking at the settings
        self.button_look_setting = self.place_object(egg.gui.Button('Look the settings'), 
                                                     1,1, alignment=1)
        self.connect(self.button_look_setting.signal_clicked, self.button_look_setting_clicked )
        #Add a button for comparing the scan and with the setting
        self.button_compare = self.place_object(egg.gui.Button('Compare scan and settings'), 
                                                     2,1, alignment=1)
        self.connect(self.button_compare.signal_clicked, self.button_compare_clicked )
        #Add a button for saving the scanned data
        self.button_save_sweep = self.place_object(egg.gui.Button('Save sweep :D'),
                                                  2,0, alignment=1)
        self.connect(self.button_save_sweep.signal_clicked, self.button_save_sweep_clicked )
        
        # tree dictionnarry for some settings
        self.treeDic_settings = egg.gui.TreeDictionary(autosettings_path='setting_magSweepLines')
        self.place_object(self.treeDic_settings, row=5, column=0, column_span=2)

        self.treeDic_settings.add_parameter('time_per_point', 10, 
                                            type='float',  
                                            bounds=[0,None], suffix=' ms',
                                            tip='How much time to elapsed between recorded points. ') 
        self.treeDic_settings.add_parameter('resolution', 1, 
                                            type='float', 
                                            bounds=[0.0001, None], suffix=' um',
                                            tip='Distance between each point to record')
        self.treeDic_settings.add_parameter('nb_line_before_optimize', 1, 
                                            type='int', 
                                            bounds=[0, None],
                                            tip='Number of line to sweep before triggering the optimization.\nPut zero for never optimizing')
        # Add a table for the trajectories of the lines. 
        self.table_trajectories  = egg.gui.Table()
        self.place_object(self.table_trajectories, row=6, column=0, column_span=2) 
        # Fill it with some data
        xs = np.linspace(1,4, 7)
        ys = np.linspace(5,7, 7)
        zs = np.linspace(19, 23, 7)
        self.table_trajectories_fill(xs, ys, zs)

        #Add a button for removing a row
        self.button_remove_row = egg.gui.Button('Remove a row :/')
        self.place_object(self.button_remove_row,row=4, column=0, alignment=1)
        self.connect(self.button_remove_row.signal_clicked, self.button_remove_row_clicked )

        #Add a button for add a row
        self.button_add_row = egg.gui.Button('Add a row :3')
        self.place_object(self.button_add_row,row=4, column=1, alignment=1)
        self.connect(self.button_add_row.signal_clicked, self.button_add_row_clicked )
        
        #Add a button for saving the current settings
        self.button_save_settings = egg.gui.Button('Save current settings')
        self.place_object(self.button_save_settings,row=4, column=2, alignment=1)
        self.connect(self.button_save_settings.signal_clicked, self.button_save_settings_clicked )

        # Add a label
        self.label_info = self.place_object(egg.gui.Label(), 1,2 )
        self.label_info_update() 
        
        # Attempt to make the button together
        self.set_row_stretch(6, 10)
        self.set_column_stretch(2, 10)        

    def table_trajectories_fill(self, xs, ys, zs):
        """
        Fill up the table with the positions.
        
        xs, ys,zs:
            Same size list of x, y and z. 
        
        Return a string being:
            A succes message or 
            An error message corresponding to what happened. 
        """
        _debug('GUIMagnetSweepLines: table_trajectories_fill')
        
        #Try to open the data
        try: 
            #First check if the lenghts matche
            if not (len(xs) == len(ys)):
                return 'Lenght of xs and ys do not match !'
            if not (len(ys) == len(zs)):
                return 'Lenght of ys and zs do not match !'  
            if not (len(zs) == len(xs)):
                return 'Lenght of xs and zs do not match !' 
            
            #If we pass here, we are ready to extract the position from the data 
            #First destroy the previous table
            while (self.table_trajectories.get_row_count() > 0):
                self.table_trajectories._widget.removeRow(0)

            # The first row will be a label for indicating what are each collumns
            self.table_trajectories.set_value(column=0, row=0, value='xs (um)')
            self.table_trajectories.set_value(column=1, row=0, value='ys (um)') 
            self.table_trajectories.set_value(column=2, row=0, value='zs (um)')                 
            #Then input the new one. 
            for i in range(0, len(xs) ):
                #Extract the x position 
                self.table_trajectories.set_value(column=0, row=i+1, value=xs[i])
                #Extract the y position 
                self.table_trajectories.set_value(column=1, row=i+1, value=ys[i])                
                #Extract the z position 
                self.table_trajectories.set_value(column=2, row=i+1, value=zs[i]) 
                
            return 'Successfully fill up the table'
            
        except: 
            return 'Error in reading the data from the file :S '        

    def databox_setting_update(self):
        """
        Update the contain of the databox_setting for it to matche the settings
        on the gui. 
        """
        # Reinitiead the databox of the settings
        self.databox_settings = _s.data.databox()
        
        # The three dictionary
        for key in self.treeDic_settings.get_keys():
            # Add each element of the dictionnary three
            self.databox_settings.insert_header(key , self.treeDic_settings[key])
        # Add the trajectories in the table
        N = self.table_trajectories.get_row_count()
        xs = []
        ys = []
        zs = []
        for i in range (1, N):
            x = self.table_trajectories.get_value(column=0, row=i)
            y = self.table_trajectories.get_value(column=1, row=i)
            z = self.table_trajectories.get_value(column=2, row=i)
            xs.append(float(x))
            ys.append(float(y))
            zs.append(float(z))
        self.databox_settings['xs'] = xs
        self.databox_settings['ys'] = ys
        self.databox_settings['zs'] = zs
        
    def button_add_row_clicked(self):
        """
        Add a row on the table
        """
        _debug('GUIMagnetSweepLines.button_add_row_clicked')
        N = self.table_trajectories.get_row_count()
        self.table_trajectories.set_value(column=0, row=N, value=0)
        self.table_trajectories.set_value(column=1, row=N, value=0) 
        self.table_trajectories.set_value(column=2, row=N, value=0)      
        
    def button_remove_row_clicked(self):
        """
        Remove the last row on the table
        """
        _debug('GUIMagnetSweepLines.button_remove_row_clicked')
        N = self.table_trajectories.get_row_count()
        if N>1:
            self.table_trajectories._widget.removeRow(N-1)    
            
    def label_info_update(self):
        """
        Adjust the info shown with respect to the settings
        """
        _debug('GUIMagnetSweepLines.label_info_update')
        #Set the text. If sucess, the text is the name of the file. Otherwise it is an error message. 
        txt = ('Settings: '+ self.path_setting.split('/')[-1]+
               '\nStatut: '+ self.statut +
               '\nSpeed along line: %f mm/s'%self.speed+
               '\nNumber of lines: %d'%(self.nb_iter-1)+
               '\nCurrent line: %d'%self.iter)
        
        self.label_info.set_text( txt ) 
        
        
    def button_load_settings_clicked(self, *a):
        """
        Load a list of x,y,z points for the magnetic field sweep
        """
        _debug('GUIMagnetSweepLines._button_load_list_toggled()')
        
        #Load the list. 
        self.databox_settings = _s.data.load(text='Load the set of lines to sweep')
        self.path_setting = self.databox_settings.path
        
        #Updat the info shown
        self.statut = 'Settings are now loaded'
        self.label_info_update()
        # Fill up the table
        self.table_trajectories_fill(self.databox_settings['xs'],
                                     self.databox_settings['ys'],
                                     self.databox_settings['zs'])
        # Fill up the three dictionnary if the corresponding settings exists in the databox
        for key in self.treeDic_settings.get_keys():
            # For each available settings
            try:
                # Set it if it is present in the databox
                self.treeDic_settings[key] = self.databox_settings.h(key)
            except:
                _debug('Didnt found the key', key)
                pass
            
        # Enable the run button, since we now have data
        self.button_run.enable()
        self.button_run.set_colors(background='green')

    def button_save_settings_clicked(self, *a):
        """
        Save the settings of the line sweep
        """
        _debug('GUIMagnetSweepLines._button_save_list_toggled()')
        
        # First need to update all the settings in the databox
        self.databox_setting_update()
        
        # Now save
        self.databox_settings.save_file()
        
    def button_look_setting_clicked(self):
        """
        Show the lines that the magnet should follow
        """
        _debug('GUIMagnetSweepLines: button_look_setting_clicked')

        # First need to update all the settings in the databox
        self.databox_setting_update()
        
        # Pop up a GUI
        plot_magSweepLinesSettings(self.databox_settings, self.path_setting)
        
    def button_compare_clicked(self):
        """
        Compare the scanned data to the settings 
        """
        # Load the scanned data
        d_scanned_data = _s.data.load(text='Load a scanned data set')
        # Load the setting
        d_settings     = _s.data.load(text='Load the setting fpor comparison')
        # Pop up a GUI
        plot_magSweepLinesResult(d_scanned_data, d_settings,
                                 title = d_scanned_data.path)

    def button_save_sweep_clicked(self):
        """
        Save the result of the sweep
        """
        _debug('GUIMagnetSweepLines: button_save_sweep_clicked')
        
        # Prepare the databox to save
        self.databox_save_scan = _s.data.databox()
        # Put some header
        self.databox_save_scan.insert_header('name', 'Hakuna matata')
        self.databox_save_scan.insert_header('date', self.info_date)
        self.databox_save_scan.insert_header('setting_file', self.path_setting)
        
        # Copy the tree dictionnary
        for key in self.treeDic_settings.get_keys():
            # Add each element of the dictionnary three
            self.databox_save_scan.insert_header(key , self.treeDic_settings[key])        
        # Add each column for the scanned points
        self.databox_save_scan['xs'] = self.xs_scanned
        self.databox_save_scan['ys'] = self.ys_scanned
        self.databox_save_scan['zs'] = self.zs_scanned  
        self.databox_save_scan['ws'] = self.ws_scanned  
        
        # Pop up the window for saving the data
        self.databox_save_scan.save_file()
        

    def button_reset_clicked(self):
        """
        Reset the iteration and stop the running
        """
        _debug('GUIMagnetSweepLines: button_reset_clicked')

        # Reset
        self.iter = 0
        
        # Stop to run 
        if self.is_running:
            self.button_run_clicked()

        self.statut = 'Sweep is resetted'
        self.label_info_update()   
        
        # Reupdate the button, because the if was not met the first time. 
        self.button_run.set_text('Start')
        self.button_run.set_colors(background='green')          
                    

    def button_run_clicked(self):
        """
        Button for controlling the experiement, 
        """
        _debug('GUIMagnetSweepLines: button_run_clicked')
        
        if self.is_running == False:
            self.is_running = True
            self.button_run.set_text('Pause')
            self.button_run.set_colors(background='blue')
            self.run_sweep()
            
        else:
            # Stop to run if it is running
            self.is_running = False
            self.button_run.set_text('Continue')
            self.button_run.set_colors(background='green')         

    def initiate_line_sweep(self):
        """
        Initiate the fpga for the line  of the magnet. 
        """
        _debug('GUIMagnetSweepLines: initiate_line_sweep')
        
        # Very similiar to the method "prepare_acquisition" of GUICount
        # The main idea is to prepare the fpga for counting the right interval of time. 
        
        #First get the count time
        self.count_time_ms = self.treeDic_settings['time_per_point']
        
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

    def take_counts(self):
        """
        Take the photocounts and update the value. 
        """
        _debug('GUIMagnetSweepLines: take_counts')
        # The fpga should already contain the pulse sequence for taking the counts
        
        # Get the counts (d'uh !)
        # Two step: runt he pulse pattern and get the counts. 
        self.fpga.run_pulse() 
        self.counts =  self.fpga.get_counts()[0]
        self.data_w = self.counts
        # The following is just if we care
        #TODO remove it if this quantity is not used at all in the GUI
        # Note also that this quantity can be retrieved in the save file by 
        # knowing the count time. 
        self.counts_per_sec = 1e3*self.counts/self.count_time_ms  
    
    
    def one_line_is_swept(self):
        """
        Trigger the optimization. 
        """
        _debug('GUIMagnetSweepLines: scan_line_optimize')
        
        # Optimizae only if the sweep is still running. 
        #TODO Remove the first if, because if this is called, it is necessarly 
        #     because the magnet scan was running ! Check the example of 
        #     the optimizer ?
        if self.is_running:
            iteration = self.gui_magnet.gui_sweep_lines.iter
            m = self.gui_magnet.gui_sweep_lines.treeDic_settings['nb_line_before_optimize']
            if m != 0:
                # If it's zero, we never optimize
                if iteration % m == (m-1):
                    _debug('GUIMainExperiment: magnet_scan_line_optimize:decide to optimize')
                    
                    # Note that it was the magnet line scan that was running
                    self.magnet_scan_line_was_running_before_optimizing = True
                    # Optimize
                    self.gui_confocal.gui_optimizer.button_optimize_clicked()          
        
          
    def run_sweep(self):
        """
        Run the sweep along the lines. 
        First go on the initial position
        """
        _debug('GUIMagnetSweepLines: run_sweep')
        
        # If we are at the begining
        if self.iter == 0:
            
            # Update the settings of the databox
            self.databox_setting_update()
            
            # Extract the settings for easier access
            self.resolution = self.treeDic_settings['resolution']
            self.time_per_point = self.treeDic_settings['time_per_point']
            self.nb_line_before_optimize = self.treeDic_settings['nb_line_before_optimize']
            # Determine the scalar speed of the magnet
            self.speed = self.resolution/self.time_per_point # It should be in mm/s. The settings are in um/ms = mm/sec. Cool 
            # Adjust the settings if that makes a speed to high
            if self.speed >2:
                # Set the speed to its maximum value
                self.speed = 2 
                # Inccrease the count time accordingly
                self.time_per_point = self.resolution/self.speed
                self.treeDic_settings['time_per_point'] = self.time_per_point
                print('Warning. Speed was too high. Auto set the time for maximum allowed speed.')

            # Get the path 
            self.xs_setting = self.databox_settings['xs']
            self.ys_setting = self.databox_settings['ys']
            self.zs_setting = self.databox_settings['zs']
            self.nb_iter = len(self.xs_setting)
            
            # Signal the initialization
            self.initiate_line_sweep()
            # Go on the initial position 
            self.statut = 'Reaching the initial position'
            self.label_info_update()   
            # Have a descent speed
            self.X.settings['Motion/Speed'] = 1 # mm/sec
            self.Y.settings['Motion/Speed'] = 1 # mm/sec
            self.Z.settings['Motion/Speed'] = 1 # mm/sec
            # Then reach the position
            self.magnet.go_to_xyz(self.xs_setting[0],
                                  self.ys_setting[0],
                                  self.zs_setting[0],
                                  want_wait=True ) # Wait that we reach the position before continuing
            # This will store the positions that the actuatores reach at each checkpoint
            self.xs_scanned = []
            self.ys_scanned = []
            self.zs_scanned = []
            # This will store the 4-Dimensional data, for example the photo-counts
            self.ws_scanned = []
            # Increase ther iteration for not scanning the first poitn to the first point !
            self.iter = 1
            
        
        
        condition=True
        while condition:
            _debug('GUIMagnetSweepLines: run_sweep: iter', self.iter)
            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events()    
            # Update the info shown
            self.statut = 'Sweeping along line %d'%self.iter
            self.label_info_update()
            # Move along the line
            x = self.xs_setting[self.iter]
            y = self.ys_setting[self.iter]
            z = self.zs_setting[self.iter]
            xyzw = self.scan_single_line(x,y,z, 
                                        speed=self.speed)
            # Append the point
            self.xs_scanned.extend(xyzw[0])
            self.ys_scanned.extend(xyzw[1])
            self.zs_scanned.extend(xyzw[2])
            self.ws_scanned.extend(xyzw[3])
            
            # Update the info shown
            self.statut = 'The line %d is completed'%self.iter
            self.label_info_update()

            # Optimize if it is appropriate
            if (self.nb_line_before_optimize>0) and not(self.optimizer==-1):
                if self.iter%self.nb_line_before_optimize == self.nb_line_before_optimize-1:
                    _debug('GUIMagnetSweepLines: run_sweep: event_optimize sent!')
                    # Update the info
                    self.statut = 'Optimizing after the line %d'%self.iter
                    self.label_info_update()
                    # Optimize !
                    self.optimizer.button_optimize.click()
                    # The fpga settings change during optimization. 
                    #We need to put them back.
                    self.initiate_line_sweep()
            
            # Update the condition of the scan
            self.iter += 1
            condition = self.is_running and self.iter<self.nb_iter
            
        # Update the data
        self.info_date = time.ctime(time.time())
        _debug('GUIMagnetSweepLines: run_sweep: done')
        # If the scan is finished
        if self.iter>=self.nb_iter:
            # Reset everything 
            self.button_reset_clicked()
        
    def scan_single_line(self, xend=0, yend=0, zend=0, speed=1):
        """
        Move in a straight line from the current position to the target position. 
        Has it scans along the line, it is calling a dummy function to be overrid 
        for making some task. 
        
        xend:
            (in mm) Target x position
        yend:
            (in mm) Target y position
        zend:
            (in mm) Target z position    
        speed:
            (in mm/sec) Speed of the displacement along the line
            
        The function returns:
            xzyw:
                A tuple (xs, ys, zs, ws), where xs, ys and zs are array for the 
                positions of the actuator at each checkpoint. ws is the array 
                of the 4-dimension data taken (for example, the counts)
        """
        _debug('GUIMagnetSweepLines: scan_xyz_line')
        
        # Set the target positions
        self.X.settings['Motion/Target_position'] = xend
        self.Y.settings['Motion/Target_position'] = yend
        self.Z.settings['Motion/Target_position'] = zend
        
        # Find the speed of each actuator for them to reach the end at the same 
        # time and move in a straight line. 
        # We need to know the distance that they will have to travel 
        self.xin = self.X.api.get_position()
        self.yin = self.Y.api.get_position()
        self.zin = self.Z.api.get_position()
        self.dx = np.abs(self.xin - xend)
        self.dy = np.abs(self.yin - yend)
        self.dz = np.abs(self.zin - zend)
        ds = np.sqrt(self.dx**2 + self.dy**2 + self.dz**2) # Total distance to travel
        # Now project this speed along each axis
        self.vx = speed*self.dx/ds
        self.vy = speed*self.dy/ds
        self.vz = speed*self.dz/ds
        self.X.settings['Motion/Speed'] = self.vx
        self.Y.settings['Motion/Speed'] = self.vy
        self.Z.settings['Motion/Speed'] = self.vz
        
        # These will store the position of the magnet at each checkpoint
        xs = []
        ys = []
        zs = []
        # This will store the 4-dimension data at each x,y,z. For example, the photo-counts
        ws = [] 
 
         #Allow the GUI to update. This is important to avoid freezing of the GUI inside loop
        self.process_events()        
        
        # Go for real
        self.X.button_move.click()
        self.Y.button_move.click()
        self.Z.button_move.click()
        
        # Note the condition for keeping doing
        # As long as the three actuator move
        condition1 = self.X.api.get_state() == 'MOVING'
        condition2 = self.Y.api.get_state() == 'MOVING'
        condition3 = self.Z.api.get_state() == 'MOVING'
        condition = condition1 or condition2 or condition3
        while condition:

            # Let's take the positions
            xs.append( self.X.api.get_position() )
            ys.append( self.Y.api.get_position() )
            zs.append( self.Z.api.get_position() )
            _debug('GUIMagnetSweepLines: scan_xyz_line: Done')
            _debug('GUIMagnetSweepLines: scan_xyz_line: %f %f %f'%(xs[-1], ys[-1], zs[-1]))
             #Allow the GUI to update. This is important to avoid freezing of the GUI inside loop
            self.process_events()
            
            # Take the counts from the fpga
            # This function is in charge to give the time delay for not blowing the CPU with an almost infinite loop
            self.take_counts() # It updates self.data_w
            ws.append(self.data_w)
            
            # Note the condition for keeping doing
            # As long as the three actuator move
            condition1 = self.X.api.get_state() == 'MOVING'
            condition2 = self.Y.api.get_state() == 'MOVING'
            condition3 = self.Z.api.get_state() == 'MOVING'
            condition = condition1 or condition2 or condition3
        
        _debug('GUIMagnetSweepLines: scan_xyz_line: Done')
        
        return (xs, ys, zs, ws)
 
#TODO Remove the followings if everything is fine. 
#    def event_initiate_sweep(self):
#        """
#        Dummy function to be overrid. 
#        This is called when we start the sweep. 
#        For example, this can be overideen to prepare the photocounter. 
#        """
#        _debug('GUIMagnetSweepLines: event_scan_initiate_sweep')
#        print('Congratulation ! Its a neodymium !')
        
#    def event_scan_line_checkpoint(self):
#        """
#        Dummy function to be overrid. It should update the value of self.data_w
#        because this value will be appended to the list. 
#        This is done when we scan a straight line, each time that we reach a
#        point to record.
#        """
#        _debug('GUIMagnetSweepLines: event_scan_line_checkpoint')
#        print('Hey congratulation! You are at iteration ', self.iter)
#        # Fake the wait time for taking the counts. 
#        time.sleep(self.time_per_point*1e-3)
#        # fake 4-dimensional data. This should be overid, for example, by the 
#        # photocounts
#        self.data_w = np.random.poisson(1000)
        
#    def event_one_line_is_swept(self):
#        """
#        Dummy funciton to be overrid. 
#        This is called each time that one line is swept.
#        """
#        _debug('GUIMagnetSweepLines: event_one_line_is_swept')
        
        
class GUIMagnetSweepList(egg.gui.Window):
    """
    Gui for making the actuator to go at each position in the list and perform 
    a task at each single position.
    """
    #TODO Rewrite it and make sure that it does what it should.
    #TODO For example, like labview, run a pulse sequence at each position
    #TODO FOr example, exctrat X, Y and Z components of magnet3
    
    def __init__(self, magnet3, name='Magnet sweep list', show=True, size=[1300,600]):
        """
        Create the GUI 
        
        magnet3:
            The gui object "GUIMagnet" that is used to control the three actuator. 
        """
        _debug('GUIMagnetSweepList: __init__', name)
        _debug('Don’t watch the clock; do what it does. Keep going. – Sam Levenson')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        #Add other objects
        self.button_load_list   = self.place_object(egg.gui.Button('MAY THE FORCE BE WITH YOU', checkable=True), 2,0).set_width(100).disable()
        self.button_scan_magnet = self.place_object(egg.gui.Button('PLEASE IMPLEMENT THE GUI', checkable=True), 3,1).set_width(150).disable()
        self.label_load_file    = self.place_object(egg.gui.Label('THE GUI IS NOT READY'), 3,0 )
        self.table_positions    = self.place_object(egg.gui.Table(columns = 3, rows = 5), 2,1) #Table containing the xyz position of the magnet
        
        #Connect the button !
        self.button_load_list  .signal_toggled.connect(self._button_load_list_toggled)
        self.button_scan_magnet.signal_toggled.connect(self._button_scan_magnet_toggled)   
        
        #Enable the button
        self.button_load_list  .set_checked(False,  block_events=True).enable()
        self.button_scan_magnet.set_checked(False,  block_events=True).enable()
#        
#        self.table_positions._widget.cellClicked(1,1)        
        

    def _button_load_list_toggled(self, *a):
        """
        Load a list of x,y,z points for the magnetic field sweep
        """
        _debug('GUIMagnetSweepList._button_load_list_toggled()')
        
        #Load the list. 
        self.d = _s.data.load(text='Load list of x,y,z positions ;)', filters="*.csv")
        
        #Set the text. If sucess, the text is the name of the file. Otherwise it is an error message. 
        self.label_load_file.set_text( self.fill_table_positions(self.d) )
        
        #Uncheck the button
        self.button_load_list  .set_checked(False,  block_events=True).enable()
        
        
    def _button_scan_magnet_toggled(self, *a):
        """
        Move the actuator at each x,y,z position loaded in the table self.table_positions
        Perfom something at each of these position. We have to thing more about how to implement this within the master GUI. 
        """
        _debug('GUIMagnetSweepList._button_scan_magnet_toggled')
        

        
        # Only run the sweep if we have enabled the button
        if self.button_scan_magnet.is_checked():
            
            
            #Ask a path to save anything
            self.path_save_file = _s.dialogs.select_directory(text='Select Directory to save datas' )
            
            #Disable the load of file, because loading a file while scanning would be sad. 
            self.button_load_list.disable()
            
            #Note how much scan will be perfomed. 
            nbScan = self.table_positions.get_row_count() 
            #Update the text on the button
            self.button_scan_magnet.set_height(50)
            self.button_scan_magnet.set_text('Scanning over %d positions...\nClick to STOP !'%nbScan)
            
            #Start the scan.
            for i in range (nbScan):
                
                #Break out if cancel. 
                if not self.button_scan_magnet.is_checked(): 
                    #Stop the actuators !
                    self.X.button_stop.click()
                    self.Y.button_stop.click()
                    self.Z.button_stop.click()
                    break
                
                #Move ! The function waits that the actuator stop to move before keeping goinf. 
                self.go_to(self.X, column=0, row=i)
                self.go_to(self.Y, column=1, row=i)
                self.go_to(self.Z, column=2, row=i)
                
                #Allow the GUI to update. This is important to avoid freezing of the GUI inside loop
                self.window.process_events() 
                
                #Perfom a task on the i'th row
                # This is where you could insert some interesting code.
                self.after_scan_set_positions(i)
            
            #Enable back buttons and update their "checkability" lol 
            self.button_load_list  .set_checked(False,  block_events=True).enable()
            self.button_scan_magnet.set_checked(False,  block_events=True)
            self.button_scan_magnet.set_height(25)
            self.button_scan_magnet.set_text('Scan Magnet')
            
    def fill_table_positions(self, data):
        """
        Fill up self.table_positions with the three first columns of data. 
        The three first columns of data must have the same lenght. 
        
        Return a string being:
            The name of the file if it succed OR
            An error message corresponding to what happened. 
        """
        _debug('GUIMagnetSweepList.fill_table_positions()')
        
        #Try to open the data
        try: 
            #First check if the lenghts matche
            if not (len(data[0]) == len(data[1])):
                return 'Lenght of first and second columns do not match !'
            if not (len(data[1]) == len(data[2])):
                return 'Lenght of second and third columns do not match !'  
            if not (len(data[2]) == len(data[0])):
                return 'Lenght of first and third columns do not match !' 
            
            #If we pass here, we are ready to extract the position from the data 
            #First destroy the previous table
            while (self.table_positions.get_row_count() > 0):
                self.table_positions._widget.removeRow(0)
                
            #Then input the new one. 
            for i in range( len(data[0]) ):
                #Extract the x position 
                self.table_positions.set_value(column=0, row=i, value=data[0][i])
                #Extract the y position 
                self.table_positions.set_value(column=1, row=i, value=data[1][i])                
                #Extract the z position 
                self.table_positions.set_value(column=2, row=i, value=data[2][i])   
            
            self.label_load_file.set_colors(text='black',background=None)
            return data.path.split()[-1]
            
        except: 
            self.label_load_file.set_colors(text='red',background=None)
            return 'Error in reading the data from the file :S '
        
    def go_to(self, actuator, column =0, row =0):
        """
        Make the actuator go to the position in the (column, row) in the table. 
        - acturator = _actuator.actuator() object (ie, self.X, self.Y or self.Z) 
                      that we want to move. 
        - column    = column to read in self.table_positions
        - row       = row to read in self.table_positions
        
        The function wait that the actuator finish to move. 
        
        Possible upgrade: Make the three actuators to move at the same time. 
                          Then wait that the three actuator finish to move. 
        
        """
        _debug('GUIMagnetSweepList.go_to()', actuator, column, row)
        
        #Set the target position
        r = self.table_positions.get_value(column=column, row=row)
        actuator.settings['Motion/Target_position'] = r
        #Update the information on the GUI
        self.window.process_events()
        
        #Make it move !
        actuator.button_move.click()
        #Wait that the actuator finished to move. 
        while actuator.api.get_state() == 'MOVING':
            #Wait a little bit to not explode the processor. 
            time.sleep(0.1)
            #Allow the GUI to update. This is important to avoid freezing of the GUI inside loop
            self.window.process_events()
            #Update the position and state.
            actuator._update()
        if not 'READY' in actuator.api.get_state():
            print('WARNING ! Actuator ' + actuator.get_name() + 'Is not in Ready State')
        return

    def go_to_xyz(self, x, y, z, want_wait=False):
        """
        Go to x, y, z (in mm)
        
        want_wait:
            (boolean) Weither of not we want to wait before it finishes
        """
        
        # Set the target positions
        self.X.settings['Motion/Target_position'] = x
        self.Y.settings['Motion/Target_position'] = y
        self.Z.settings['Motion/Target_position'] = z       
        
        # Go for real
        self.X.button_move.click()
        self.Y.button_move.click()
        self.Z.button_move.click()

        if want_wait:
            #Wait that the actuators finished to move. 
            condition = True
            while condition:
                # Wait for not exploding the CPU
                time.sleep(0.1)
                 #Allow the GUI to update. This is important to avoid freezing of the GUI inside loop
                self.window.process_events()
                # Note the condition for keeping doing
                # As long as the three actuator move
                condition1 = self.X.api.get_state() == 'MOVING'
                condition2 = self.Y.api.get_state() == 'MOVING'
                condition3 = self.Z.api.get_state() == 'MOVING'
                condition = condition1 or condition2 or condition3
                
    def after_scan_set_positions(self, i=0):
        """
        Task to perfom at the position corresponding to the i'th row of
        self.table_position.
        
        To overwrite for doing stuff like GHz sweep or anything ;)
        i is the iteration in the table (the i'th row), such that we can perform 
        a task depending on the iteration. 
        """
        _debug('GUIMagnetSweepList: after_scan_set_positions', i)
        
        print('On the %dth row ;)'%i)        


#By default set the object
if __name__ == '__main__':
    _debug_enabled = True
    import api_actuator
    api_actuator._debug_enabled
    
#    cc = ApiActuator().


    bitfile_path = ("X:\DiamondCloud\Magnetometry\Acquisition\FPGA\Magnetometry Control\FPGA Bitfiles"
                    "\Pulsepattern(bet_FPGATarget_FPGAFULLV2_WZPA4vla3fk.lvbitx")
    resource_num = "RIO0"         
    fpga = _fc.FPGA_api(bitfile_path, resource_num) # Create the api   
    fpga.open_session()
    
    optimizer = gui_confocal_optimizer.GUIOptimizer(fpga)
    optimizer.show() # Hoh yess, we want to see it !

    self = GUIMagnet(fpga, optimizer, name='Magnetooooo') 
    self.show()


    