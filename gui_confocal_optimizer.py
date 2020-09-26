# -*- coding: utf-8 -*-
"""
Created on Thu May 21 15:27:02 2020


A GUI for optimizing the x,y and z axis

@author: Childresslab, Michael
"""

import numpy as np

from scipy.optimize import curve_fit

from spinmob import egg
import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error


from converter import Converter # For converting the pattern for counting

# Debug stuff.
_debug_enabled     = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))
        

  

class GUIOptimizer(egg.gui.Window):
    """
    GUI for optimizing around an NV. 
    """
    def __init__(self, fpga, name="Optimizer", size=[1300,600]): 
        """
        Initialize 
        
        fpga:
            "FPGA_api" object from api_fpga.py. 
            This is the object shared amoung the GUIs for controlling the fpga. 
            The session of the fpga must already be open.
            
        """    
        _debug('GUIOptimizer:__init__')
        _debug('I am enjoying my life because things aren’t going the way I planned. – Rohit Pandita')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Take possession of the fpga Mouahahaha...
        self.fpga = fpga
        
        self.is_optimizing = False # Weither or not we are optimizing

        # Fill up the GUI 
        self.initialize_GUI()
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIOptimizer: initialize_GUI')
        
        # Place a buttong for the scan
        self.button_optimize = self.place_object(egg.gui.Button('Optimize'))
        self.button_optimize.set_text('Optimize')
        self.button_optimize.set_style('background-color: rgb(0, 200, 0);')          
        self.connect(self.button_optimize.signal_clicked, self.button_optimize_clicked)
        
        # Place the dictionay three for all the parameters
        self.treeDic_settings  = egg.gui.TreeDictionary(autosettings_path='setting_optimizer')
        self.new_autorow()
        self.place_object(self.treeDic_settings)   
        # The next three are for setting the range under which to optimize
        self.treeDic_settings.add_parameter('Usual/Range_Vx', 0.1, 
                                           type='float', step=0.1, 
                                           bounds=[0,None], suffix=' V',
                                           tip='Range on which to optimize in Vx direction')
        self.treeDic_settings.add_parameter('Usual/Range_Vy', 0.1, 
                                           type='float', step=0.1, 
                                           bounds=[0,None], suffix=' V',
                                           tip='Range on which to optimize in Vy direction')
        self.treeDic_settings.add_parameter('Usual/Range_Vz', 0.1, 
                                           type='float', step=0.1, 
                                           bounds=[0,None], suffix=' V',
                                           tip='Range on which to optimize in Vz direction')  
        # Other useful parameters
        self.treeDic_settings.add_parameter('Usual/Count_time', 50, 
                                           type='float', step=0.1, 
                                           bounds=[0, None], suffix=' ms')
        self.treeDic_settings.add_parameter('Usual/Scan_points', 25, 
                                           type='int', step=1, 
                                           bounds=[3, None])
        # THe next three are for the offsets voltages if we want to optimize
        # elsewehre than the position probed. 
        self.treeDic_settings.add_parameter('Usual/Offset_Vx', 0, 
                                           type='float', step=0.1, 
                                           bounds=[-20,20], suffix=' V',
                                           tip='X_opt - X_probe')
        self.treeDic_settings.add_parameter('Usual/Offset_Vy', 0, 
                                           type='float', step=0.1, 
                                           bounds=[-20,20], suffix=' V',
                                           tip='Y_opt - Y_probe')
        self.treeDic_settings.add_parameter('Usual/Offset_Vz', 0, 
                                           type='float', step=0.1, 
                                           bounds=[-20,20], suffix=' V',
                                           tip='Z_opt - Z_probe')
        
        # The next parameters are used only for automatic optimization during
        # Pulse sequences or something else. 
        self.treeDic_settings.add_parameter('Automatic/Threshold_fraction', 0.95, 
                                           type='float', step=0.1, 
                                           bounds=[0,None], 
                                           tip='Like in Labview')    

        # Add a table for showing the selected R_probed and R_optimize
        self.table_Rs  = egg.gui.Table()
        self.place_object(self.table_Rs, row=2, column=0, column_span=2) 
        # Put some values
        self.table_Rs.set_value(column=1, row=0, value='Vx')
        self.table_Rs.set_value(column=2, row=0, value='Vy')
        self.table_Rs.set_value(column=3, row=0, value='Vz')
        self.table_Rs.set_value(column=0, row=1, value='R_probe')
        self.table_Rs.set_value(column=0, row=2, value='R_opt')      
        self.table_Rs.set_value(column=1, row=1, value=0)
        self.table_Rs.set_value(column=2, row=1, value=0)
        self.table_Rs.set_value(column=3, row=1, value=0)
        self.table_Rs.set_value(column=1, row=2, value=0)
        self.table_Rs.set_value(column=2, row=2, value=0)
        self.table_Rs.set_value(column=3, row=2, value=0)        

        # Place a button for setting r_probe
        self.button_set_r_probe = self.place_object(
                egg.gui.Button('Set R_probe'), row=3, column=0)       
        self.connect(self.button_set_r_probe.signal_clicked, self.button_set_r_probe_clicked)  
        # Place a button for setting r_optimize
        self.button_set_r_opt = self.place_object(
                egg.gui.Button('Set R_opt'), row=4, column=0)       
        self.connect(self.button_set_r_opt.signal_clicked, self.button_set_r_opt_clicked) 
        # Place a button for setting the offset
        self.button_set_r_offset = self.place_object(
                egg.gui.Button('Set R_offset'), row=5, column=0)       
        self.connect(self.button_set_r_offset.signal_clicked, self.button_set_r_offset_clicked)         
        
        # Tabs !
        self.tabs1 = self.place_object(
                egg.gui.TabArea(autosettings_path='optimizer_tabs1'),
                row_span=6)
        
        
        # A tab for the fits
        self.tab_fits = self.tabs1.add_tab('Fits')
        # Place the plot for showing the fits 
        self.win_plot_fits = egg.pyqtgraph.GraphicsWindow(title="Optimization")
        self.win_plot_fits.resize(1000,600)
        self.tab_fits.place_object(self.win_plot_fits,
                          row=0, column=1, row_span=3, alignment =1) 
        # Add the three plot for each direction
        self.plot_fit_z = self.win_plot_fits.addPlot(title="Z direction")
        self.plot_fit_x = self.win_plot_fits.addPlot(title="X direction")
        self.plot_fit_y = self.win_plot_fits.addPlot(title="Y direction")
        
        # A tab for tracking the positions
        self.tab_track = self.tabs1.add_tab('Track position')
        # Three databox for the three directions VS optimizations
        self.databoxplot_pos_x = egg.gui.DataboxPlot(autosettings_path='plot_optimzation_x')
        self.databoxplot_pos_y = egg.gui.DataboxPlot(autosettings_path='plot_optimzation_y')
        self.databoxplot_pos_z = egg.gui.DataboxPlot(autosettings_path='plot_optimzation_z')
        self.tab_track.place_object(self.databoxplot_pos_x, row=1, column=1)     
        self.tab_track.place_object(self.databoxplot_pos_y, row=2, column=1)  
        self.tab_track.place_object(self.databoxplot_pos_z, row=3, column=1)  
        
        
    
    def prepare_acquisition_pulse(self):
        """
        Prepare the acquisition of counts. 
        
        It prepares the pulse pattern and set the wait time. 
        
        """
        _debug('GUIOptimizer: prepare_acquisition')
        
        # Set the fpga NOT in each tick mode
        self.fpga.set_counting_mode(False)
        
        # Create the data array from counting
        # Prepare DIO1 in state 1
        self.fpga.prepare_DIOs([1], [1]) 
        # Get the actual DIOs, because there might be other DIOs open.
        self.dio_states = self.fpga.get_DIO_states() 
        # Convert the instruction into the data array
        conver = Converter() # Load the converter object.
        self.count_time_ms = self.treeDic_settings['Usual/Count_time']
        nb_ticks = self.count_time_ms*1e3/(conver.tickDuration)
        self.data_array = conver.convert_into_int32([(nb_ticks, self.dio_states)])
        
        # Upate the waiting time
        self.fpga.prepare_wait_time(self.wait_after_AOs_us)
        
         # Send the data_array to the FPGA
        self.fpga.prepare_pulse(self.data_array)
        
        # Call the event to say "hey, stuff changed on the fpga"
        self.event_fpga_change()        
        
    def button_optimize_clicked(self):
        """
        Button optimize clicked! 
        """
        _debug('GUIOptimizer: button_optimize_clicked')
        
        if self.is_optimizing == False:
            # Note that we are taking counts
            self.button_optimize.set_text('Stop Optimizing')
            self.button_optimize.set_style('background-color: rgb(255, 100, 100);')
            self.is_optimizing = True
            # Send a event saying "Hey everyone, optimization is starting !"
            self.event_optimize_starts()
            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events()               
            
            # Optimize !
            self.run_optimizing()
        else:
            # Stop to take counts if we were taking counts
            self.is_optimizing  = False
            # Update the GUI
            self.button_optimize.set_text('Optimize')
            self.button_optimize.set_style('background-color: rgb(0, 200, 0);')  
            # Send a event saying "Holla, optimization is done !"
            self.event_optimize_ends()

    def button_set_r_probe_clicked(self):
        """
        Note the actuall probed position
        """
        _debug('GUIOptimizer: button_set_r_probe_clicked')

        # Steal the AOs information of x,y,z from the map
        self.steal_AO_info() # This make sure that we have the good AO
        # Get the voltages
        Vx = self.fpga.get_AO_voltage(self.AOx)
        Vy = self.fpga.get_AO_voltage(self.AOy)
        Vz = self.fpga.get_AO_voltage(self.AOz)
        # Update the table
        self.table_Rs.set_value(column=1, row=1, value=Vx)
        self.table_Rs.set_value(column=2, row=1, value=Vy)
        self.table_Rs.set_value(column=3, row=1, value=Vz)        

    def button_set_r_opt_clicked(self):
        """
        Note the osition to optimize
        """
        _debug('GUIOptimizer: button_set_r_opt_clicked')

        # Steal the AOs information of x,y,z from the map
        self.steal_AO_info() # This make sure that we have the good AO
        # Get the voltages
        Vx = self.fpga.get_AO_voltage(self.AOx)
        Vy = self.fpga.get_AO_voltage(self.AOy)
        Vz = self.fpga.get_AO_voltage(self.AOz)
        # Update the table
        self.table_Rs.set_value(column=1, row=2, value=Vx)
        self.table_Rs.set_value(column=2, row=2, value=Vy)
        self.table_Rs.set_value(column=3, row=2, value=Vz)   
        
    def button_set_r_offset_clicked(self):
        """
        Set the relative position for optimizing. 
        """
        _debug('GUIOptimizer: button_set_r_offset_clicked')  
        
        # Take the position to optimize
        Vopt_x = float(self.table_Rs.get_value(column=1, row=2))
        Vopt_y = float(self.table_Rs.get_value(column=2, row=2))
        Vopt_z = float(self.table_Rs.get_value(column=3, row=2))
        # Take the position to probe
        Vprobe_x = float(self.table_Rs.get_value(column=1, row=1))
        Vprobe_y = float(self.table_Rs.get_value(column=2, row=1))
        Vprobe_z = float(self.table_Rs.get_value(column=3, row=1))
        # Get the offset voltages 
        Voffset_x = Vopt_x - Vprobe_x
        Voffset_y = Vopt_y - Vprobe_y
        Voffset_z = Vopt_z - Vprobe_z
        # Save this in the tree dictionnary
        self.treeDic_settings['Usual/Offset_Vx'] = Voffset_x
        self.treeDic_settings['Usual/Offset_Vy'] = Voffset_y
        self.treeDic_settings['Usual/Offset_Vz'] = Voffset_z
        
    def offset_put_them(self):
        """
        Shift the position of the piezo by the offset
        """        
        _debug('GUIOptimizer: offset_put_them')
        
        # Note the value of the offsets
        self.Voffset_x = self.treeDic_settings['Usual/Offset_Vx']
        self.Voffset_y = self.treeDic_settings['Usual/Offset_Vy']
        self.Voffset_z = self.treeDic_settings['Usual/Offset_Vz']  
        # Note the new position
        self.vx_new = self.fpga.get_AO_voltage(self.AOx) + self.Voffset_x
        self.vy_new = self.fpga.get_AO_voltage(self.AOy) + self.Voffset_y
        self.vz_new = self.fpga.get_AO_voltage(self.AOz) + self.Voffset_z
        _debug('GUIOptimizer: offset_put_them: ',
               self.vx_new, self.vy_new, self.vz_new)
        
        # Set the fpga in this new position 
        self.fpga.prepare_AOs([int(self.AOx), int(self.AOy), int(self.AOz)], 
                               [self.vx_new, self.vy_new, self.vz_new]) 
        # Run the FPGA for updating its settings
        # It gonna run also the pre-existing pulse sequence. Hopefully it's 
        # gonna be the counter. 
        self.fpga.lets_go_FPGA()
        
        # Call the event to say "hey, stuff changed on the fpga"
        self.event_fpga_change()          

    def offset_remove_them(self):
        """
        Shift the position of the piezo to remove the offset
        """        
        _debug('GUIOptimizer: offset_remove_them')
        
        # Note the new position
        self.vx_new = self.fpga.get_AO_voltage(self.AOx) - self.Voffset_x
        self.vy_new = self.fpga.get_AO_voltage(self.AOy) - self.Voffset_y
        self.vz_new = self.fpga.get_AO_voltage(self.AOz) - self.Voffset_z
        _debug('GUIOptimizer: offset_remove_them: ',
               self.vx_new, self.vy_new, self.vz_new)
        
        # Set the fpga in this new position 
        self.fpga.prepare_AOs([int(self.AOx), int(self.AOy), int(self.AOz)], 
                               [self.vx_new, self.vy_new, self.vz_new]) 
        # Run the FPGA for updating its settings
        # It gonna run also the pre-existing pulse sequence. Hopefully it's 
        # gonna be the counter. 
        self.fpga.lets_go_FPGA()
        
        # Call the event to say "hey, stuff changed on the fpga"
        self.event_fpga_change()            
            
    def parabola(self, x, x0, dx, y0):
        """
        A inverted parabola for the curve_fit function
        """
        return y0-((x-x0)/dx)**2
        
    def scan_1D(self):
        """
        Scan along one direction defined by the attribute self.AO
        The range of the scan is between the attributes self.Vmin and self.Vmax
        
        """
        _debug('GUIOptimizer: scan_1D: AO ', self.AO) 
        
        # Create an array of voltages centered on V0 with the range from the settings. 
        Npts = self.treeDic_settings['Usual/Scan_points']
        self.Vs = np.linspace(self.Vmin, self.Vmax, Npts)
        
        # Scan the array--> note the counts at each value
        self.count_array = []
        
        i = -1
        while self.is_optimizing and (i<(len(self.Vs)-1)):
            i += 1
            V = self.Vs[i]
            self.fpga.prepare_AOs([int(self.AO)], [V])
            
            # Get the count, finally ;) 
            # Two step: runt he pulse pattern and get the counts. 
            self.fpga.run_pulse() # This will also write the AOs
            self.counts =  self.fpga.get_counts()[0]
            
#            # FOR TESTING ONLY Add some fake to the data
#            self.counts+= np.random.poisson(1000-200*(V-self.V0)**2/(self.Vmax-self.V0)**2)
#            print(self.counts)
            self.count_array.append(self.counts)
            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events()   
            
            # Call the event to say "hey, stuff changed on the fpga"
            self.event_fpga_change()                 
            
    def find_max(self):
        """
        Find the voltage which maximizes the counts. 
        Use a parabola fit. 
        """
        _debug('GUIOptimizer: find_max') 
        
        # A parabola
        xdata = self.Vs
        ydata = self.count_array
        x0_guess = self.V0
        y0_guess = np.mean(ydata)
        dx1 = (xdata[-1]-x0_guess)/np.sqrt(np.abs(y0_guess-ydata[-1]))
        dx2 = (xdata[0]-x0_guess)/np.sqrt(np.abs(y0_guess-ydata[0]))
        dx_guess = max([dx1, dx2])
        self.p0 = [self.V0, dx_guess, y0_guess]
        
        # Try to fit. If it fails, do not change the AO
        try:
            self.popt, self.pcov = curve_fit(self.parabola, xdata, ydata, p0=self.p0)
            v_fit = self.popt[0]
            if v_fit > self.Vmax:
                _debug('GUIOptimizer: find_max: choose vmax!')
                self.v_best = self.Vmax
            elif v_fit < self.Vmin:
                _debug('GUIOptimizer: find_max: choose vmin!')
                self.v_best = self.Vmin
            else:
                _debug('GUIOptimizer: find_max: choose in the fit !')
                self.v_best = v_fit
            # Put the FPGA with this AO at the voltage of maximum counts
            self.fpga.prepare_AOs([int(self.AO)], [self.v_best])  
            
            # Call the event to say "hey, stuff changed on the fpga"
            self.event_fpga_change()                
            
            self.fit_worked = True
            
        except:
            _debug('GUIOptimizer: find_max: Cannot fit!')
            # Do not change the AO
            self.fit_worked = False
            # Still not the best V, for keeping track of it..
            self.v_best = self.V0 
            
        _debug('GUIOptimizer: find_max: v_best = ', self.v_best)
 
    def steal_AO_info(self):
        """
        Steal the AOs information of x,y,z from the setting of the map
        """
        _debug('GUIOptimizer: steal_AO_info') 
        self.treeDict_map = egg.gui.TreeDictionary(autosettings_path='setting_map')
        self.treeDict_map.add_parameter('AO_x')
        self.treeDict_map.add_parameter('AO_y')
        self.treeDict_map.add_parameter('AO_z')
        self.treeDict_map.add_parameter('Wait_after_AOs')
        self.AOx = self.treeDict_map['AO_x']
        self.AOy = self.treeDict_map['AO_y']
        self.AOz = self.treeDict_map['AO_z']
        self.wait_after_AOs_us = int(self.treeDict_map['Wait_after_AOs'])
        _debug(self.AOx, self.AOy, self.AOz, self.wait_after_AOs_us)
               
        
    def run_optimizing(self):
        """
        Run the optimization procedure.
        """
        _debug('GUIOptimizer: run_optimizing') 
        
        # Steal the AOs information of x,y,z from the map
        self.steal_AO_info()
        
        # Put the offsets
        self.offset_put_them()

        # Prepare the pulse sequence for getting the counts
        self.prepare_acquisition_pulse()
        
        # Optimize the X direction
        self.AO = self.AOx
        # The center voltage will be the actual voltage
        self.V0 = self.fpga.get_AO_voltage(self.AO) 
        self.Vmin = self.V0 - self.treeDic_settings['Usual/Range_Vx']/2
        self.Vmax = self.V0 + self.treeDic_settings['Usual/Range_Vx']/2
        # Trigger the scan
        self.scan_1D()
        # Process the scan only if it wasn't interrupted
        if self.is_optimizing:
            # Find the maxima
            self.find_max()
            # Update the plots
            self.update_plot_fit(self.plot_fit_x)   
            self.update_plot_position('x')
            
        
        # Optimize the Y direction
        self.AO = self.AOy
        # The center voltage will be the actual voltage
        self.V0 = self.fpga.get_AO_voltage(self.AO)
        self.Vmin = self.V0 - self.treeDic_settings['Usual/Range_Vy']/2
        self.Vmax = self.V0 + self.treeDic_settings['Usual/Range_Vy']/2
        # Trigger the scan
        self.scan_1D()
        # Process the scan only if it wasn't interrupted
        if self.is_optimizing:
            # Find the maxima
            self.find_max()
            # Update the plots
            self.update_plot_fit(self.plot_fit_y) 
            self.update_plot_position('y')

        # Optimize the Z direction
        self.AO = self.AOz
        # The center voltage will be the actual voltage
        self.V0 = self.fpga.get_AO_voltage(self.AO)        
        self.Vmin = self.V0 - self.treeDic_settings['Usual/Range_Vz']/2
        self.Vmax = self.V0 + self.treeDic_settings['Usual/Range_Vz']/2
        # Trigger the scan
        self.scan_1D()
        # Process the scan only if it wasn't interrupted
        if self.is_optimizing:            
            # Find the maxima
            self.find_max()
            # Update the plots 
            self.update_plot_fit(self.plot_fit_z)
            self.update_plot_position('z')
        
        if self.is_optimizing:
            # Will stop optimizing and uptage the button
            self.button_optimize_clicked()

        # Important: Remove the offsets
        self.offset_remove_them()
        
    def update_plot_fit(self, plot):
        """
        Plot the fit. 
        
        plot:
            "self.win_plot_fits.addPlot" object that we want to update. 
            
        """
        _debug('GUIOptimizer: update_plot_fit') 
        
        # Remove the previous plot
        plot.clear() 
        # plot the data and the fit
        plot.addLegend() 
        plot.plot(self.Vs, self.count_array, pen=(255,255,255), name="Data")
        x_fit = np.linspace(min(self.Vs), max(self.Vs), 100)
        # Show the fit if it worked. 
        if self.fit_worked:
            plot.plot(x_fit, self.parabola(x_fit, *self.popt), pen=(255,0,255),name="Fit")
            # Show the maximum
            self.cmax = self.popt[2]
            plot.plot([self.v_best], [self.cmax], symbolBrush=(255,0,255), symbolPen='w', symbol='o', symbolSize=14)  
        else:
            # Still show where is the max
            y = np.mean(self.count_array)
            plot.plot([self.V0], [y], symbolBrush=(255,0,255), symbolPen='w',
                      symbol='o', symbolSize=14, name='Fit did not work.\nThis is the value taken.')  
        
        # Show the guess
        plot.plot(x_fit, self.parabola(x_fit, *self.p0), pen=(0,255,255),name="Guess")

    def update_plot_position(self, axis):
        """
        Update the position of the fit. 
        
        axis:
            string, either x, y or z, for telling which point to update.
        """
        # For each axis, check if the plot exist (this will set the abscisse)
        # Then add the point
        if axis == 'x':
            _debug('GUIOptimizer: update_plot_position: x') 
            if 'Vx' in self.databoxplot_pos_x.ckeys:
                nb = len(self.databoxplot_pos_x['Vx'])
            else:
                nb = 0
            self.databoxplot_pos_x.append_data_point([nb, self.v_best],
                                                     ['Number of Optimization','Vx']).plot()
        if axis == 'y':
            _debug('GUIOptimizer: update_plot_position: y')
            if 'Vy' in self.databoxplot_pos_y.ckeys:
                nb = len(self.databoxplot_pos_y['Vy'])
            else:
                nb = 0
            self.databoxplot_pos_y.append_data_point([nb, self.v_best],
                                                     ['Number of Optimization','Vy']).plot()
        if axis == 'z':
            _debug('GUIOptimizer: update_plot_position: z')
            if 'Vz' in self.databoxplot_pos_z.ckeys:
                nb = len(self.databoxplot_pos_z['Vz'])
            else:
                nb = 0
            self.databoxplot_pos_z.append_data_point([nb, self.v_best],
                                                     ['Number of Optimization','Vz']).plot()
        

    def update_GUI_with_fpga(self):
        """
        Update the gui such that the widgets match with the fpga. 
        That is useful for the implementation with other GUI that also 
        modifies the fpga. 
        """
        # There is no widget to match for now
        return

    def event_optimize_starts(self):
        """
        Dummy funciton to be overrid. 
        
        It is called when the optimization starts.
        """
        return

    def event_optimize_ends(self):
        """
        Dummy funciton to be overrid. 
        
        It is called when the optimization ends.
        """
        return
    
    def event_fpga_change(self):
        """
        Dummy function to be overrid. 
        
        It is called after that the value on the fpga changed.
        """      
        return

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
    
    self = GUIOptimizer(fpga)
    self.show()

    





