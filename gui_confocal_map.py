# -*- coding: utf-8 -*-
"""
Created on Thu May 21 15:27:02 2020


A GUI for taking the maps


@author: Childresslab, Michael
"""

import numpy as np

import spinmob as sm
from spinmob import egg

import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error

import time

from converter import Converter # For converting the pattern for counting



# Debug stuff.
_debug_enabled     = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))

        
        
class GUIMap(egg.gui.Window):
    """
    GUI for mapping hte count as we change the x-y position. 
    We can also dive into Z. 
    
    This gui maps the counts by interfacing with the gui of the counts. 
    Therefore it needs the GUICounts. 
    
    
    """
    def __init__(self, fpga, name="Mapper", size=[1300,600]): 
        """
        Initialize 
        
        fpga:
            "FPGA_api" object from api_fpga.py. 
            This is the object shared amoung the GUIs for controlling the fpga. 
            The session of the fpga must already be open.
            
        """    
        _debug('GUIMap:__init__')
        _debug('Make each day your masterpiece. – John Wooden')
        
        # Run the basic stuff for the initialization
        egg.gui.Window.__init__(self, title=name, size=size)
        
        # Take possession of the GUIs. Mouahahaha...
        self.fpga = fpga

        # Some attibute
        self.is_scanning = False # Weither or not the scan is running
        self.list_databox_scans =[] # Store the informations for many slices 
        self.nb_of_slice = 0  # Actual number of stored slice    
        self.nb_max_slice = 5 # Maximum number of slice to store
        
        self.label_slice_date = '' # Label shown on the slice
        
        # Fill up the GUI 
        self.initialize_GUI()
        
        
    def initialize_GUI(self):
        """
        Fill up the GUI
        """        
        _debug('GUIMap: initialize_GUI')
        
        # Place a buttong for the scan
        self.button_scan = self.place_object(egg.gui.Button())
        self.button_scan.set_text('Scan :D')
        self.button_scan.set_style('background-color: rgb(0, 200, 0);')
        self.connect(self.button_scan.signal_clicked, self.button_scan_clicked)
        
        # Place a buttong for selecting a subregion
        self.is_selecting_subregion = False #Weither or not the button is selected or not
        self.button_subregion = self.place_object(egg.gui.Button(), alignment=1)
        self.button_subregion.set_text('Select a \nsubregion ;)')
        self.button_subregion.set_style('background-color: rgb(0, 200, 0);')
        self.connect(self.button_subregion.signal_clicked, self.button_subregion_clicked) 
 
        # Place a buttong for autosetting the region
        self.button_autoregion = self.place_object(egg.gui.Button(), alignment=1)
        self.button_autoregion.set_text('AutoSet region')
        self.button_autoregion.set_style('background-color: rgb(0, 200, 0);')
        self.connect(self.button_autoregion.signal_clicked, self.button_autoregion_clicked)        

        # Place a buttong for replacing the cross at the middle of the map
        self.button_center_cursor = self.place_object(egg.gui.Button(), alignment=1)
        self.button_center_cursor.set_text('Center Cursor')
        self.button_center_cursor.set_style('background-color: rgb(0, 200, 0);')
        self.connect(self.button_center_cursor.signal_clicked, self.button_center_cursor_clicked)    
        
        # Place a buttong for saving the scans
        self.button_save_scans = self.place_object(egg.gui.Button(), alignment=1)
        self.button_save_scans.set_text('Save scans :)')
        self.connect(self.button_save_scans.signal_clicked, self.button_save_scans_clicked)  

        # Place a buttong for loading the scans
        self.button_load_scans = self.place_object(egg.gui.Button(), alignment=1)
        self.button_load_scans.set_text('Load scan :D')
        self.connect(self.button_load_scans.signal_clicked, self.button_load_scans_clicked)  
        
        self.new_autorow()
        # Place a progres bar
        self.progress_bar = egg.pyqtgraph.Qt.QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.place_object(self.progress_bar,alignment=1)
        # Place a label
        self.label_progress = egg.gui.Label('We have the best scanner on the market.')
        self.place_object(self.label_progress, column_span=3)
        
        
        self.new_autorow()
        # Place the dictionay three for all the parameters
        self.treeDic_settings  = egg.gui.TreeDictionary(autosettings_path='setting_map')
        self.place_object(self.treeDic_settings, column=6, column_span=3)   
        self.treeDic_settings.add_parameter('Wait_after_AOs', 1, 
                                           type='float', step=1, 
                                           bounds=[0,None], suffix='us',
                                           tip='Time to wait after the AOs set.')
        self.treeDic_settings.add_parameter('Count_time', 1, 
                                           type='float', step=1, 
                                           bounds=[0,None], suffix='ms',
                                           tip='Count time during the scan')
        self.treeDic_settings.add_parameter('AO_x', 2, 
                                           type='int', step=1, 
                                           bounds=[0,7],
                                           tip='Which AO control x')   
        self.treeDic_settings.add_parameter('AO_y', 3, 
                                           type='int', step=1, 
                                           bounds=[0,7],
                                           tip='Which AO control y') 
        self.treeDic_settings.add_parameter('AO_z', 4, 
                                           type='int', step=1, 
                                           bounds=[0,7],
                                           tip='Which AO control z') 
        self.treeDic_settings.add_parameter('X_min', -5, 
                                           type='float', step=1, 
                                           bounds=[-10,10], suffix='V',
                                           tip='Minimum voltage to scan in the x direction.')        
        self.treeDic_settings.add_parameter('X_max', 5, 
                                           type='float', step=1, 
                                           bounds=[-10,10], suffix='V',
                                           tip='Maximum voltage to scan in the x direction.')   
        self.treeDic_settings.add_parameter('Nb_point_X', 100, 
                                           type='int', step=1, 
                                           bounds=[0, None],
                                           tip='Number of point to scan in the x direction.')           
        self.treeDic_settings.add_parameter('Y_min', -5, 
                                           type='float', step=1, 
                                           bounds=[-10,10], suffix='V',
                                           tip='Minimum voltage to scan in the y direction.')        
        self.treeDic_settings.add_parameter('Y_max', 5, 
                                           type='float', step=1, 
                                           bounds=[-10,10], suffix='V',
                                           tip='Maximum voltage to scan in the y direction.')   
        self.treeDic_settings.add_parameter('Nb_point_Y', 100, 
                                           type='int', step=1, 
                                           bounds=[0, None],
                                           tip='Number of point to scan in the y direction.')   
        
        self.treeDic_settings.add_parameter('Slice_shown', 0, 
                                           type='int', 
                                           suffix=' /%d'%(self.nb_max_slice-1),
                                           bounds=[0, self.nb_max_slice-1],
                                           tip='Which scan to shown')  
        
        list_colormap = PersonalColorMap().get_list_colormaps()
        self.treeDic_settings.add_parameter('Colormap', 0, 
                                           type='list', values=list_colormap)   

        self.treeDic_settings.add_parameter('Set_aspect', False, 
                                           type='bool',
                                           tip='Weither or not to set the axis to scale. ')  
        self.treeDic_settings.add_parameter('yfactor_aspect_ratio', 1, 
                                           type='float', step=0.1, 
                                           bounds=[None,None],
                                           tip='Factor by which we stretch the yaxis')  
        
        self.list_scanning_mode = ['Sawtooth', 'Snake', 'Random', 'Diagonal_sweep', 'Spiral']
        self.treeDic_settings.add_parameter('Scanning_mode', 0, 
                                           type='list', 
                                           values=self.list_scanning_mode,
                                           tip='On which kind of path to scan. \nSee the methods "scan_row_..." for more information.')  
        
        # Some connections
        self.treeDic_settings.connect_signal_changed('Slice_shown', self.update_slice_shown)
        self.treeDic_settings.connect_signal_changed('Colormap', self.update_colormap)
        self.treeDic_settings.connect_signal_changed('Set_aspect', self.update_image)
        self.treeDic_settings.connect_signal_changed('yfactor_aspect_ratio', self.update_image)
        

        # Create the slider for the z position before placing it, because a method needs it before, 
        self.slider_z_position = egg.gui.Slider(bounds=(-10,10),
                                                autosettings_path='map_slider_z',
                                                steps=1000)

        #TODO place the initialization of the map in a separated method       
        # PLace the Ultimate map
        # Create the ImgaeView within this. 
        # Prepare the container, expecially the axis.
        self.plot_item = egg.pyqtgraph.PlotItem()
        self.plot_image = egg.pyqtgraph.ImageView(view=self.plot_item)
        self.place_object(self.plot_image, column=0, column_span=6,
                          row_span=5,alignment=0)  
        self.original_width = self.plot_image.geometry().bottom() # Record the original width for the rescaling
        # Add the cross-hair lines
        self.vLine = egg.pyqtgraph.InfiniteLine(angle=90, movable=True,
                                                pen=(0,255,255))
        self.hLine = egg.pyqtgraph.InfiniteLine(angle=0, movable=True,
                                                pen=(0,255,255))
        self.plot_image.addItem(self.vLine, ignoreBounds=True)
        self.plot_image.addItem(self.hLine, ignoreBounds=True)   

        self.connect(self.vLine.sigPositionChanged, self.pos_vLine_changed)
        self.connect(self.hLine.sigPositionChanged, self.pos_hLine_changed)
        self.is_pos_vLine_changing = False # A usuful boolean to avoid infinite call
        self.is_pos_hLine_changing = False # A usuful boolean to avoid infinite call
        
        # Add a ROI
        self.ptROI = egg.pyqtgraph.ROI((0,0),pen=(0,255,255))
        self.plot_image.addItem(self.ptROI)
        self.connect(self.ptROI.sigRegionChanged, self.pos_ptROI_changed)    
        # A label for the slice
        self.label_slice_date = time.ctime(time.time())
        self.textitem_slice = egg.pyqtgraph.TextItem(text=self.label_slice_date, 
                                                     color=(200, 200, 255),
                                                     fill=(0, 0, 255, 100))          
        self.plot_image.addItem(self.textitem_slice)
        
        # Add a dummy map 
        x = np.linspace(1, 20, 100)
        y = np.linspace(1, 20, 100)
        X,Y = np.meshgrid(x,y)
        self.Z = np.cos(X*2)*np.sin(Y)*X*Y
#        self.Z = -(X**2+Y**2-np.arctan(Y*0.01/X)**2)
        # The following are the typical steps for making the image.
        self.match_attributes_with_gui()
        self.initialize_image() 
        self.update_image()
        self.store_scan()
        
        # Place the slider
        self.new_autorow()
        self.place_object(self.slider_z_position, row=10,row_span=3, column_span=3)
        self.set_row_stretch(1,10)
        self.slider_z_position.event_changed = self.slider_z_position_changed
        
    
    def slider_z_position_changed(self, value):
        """
        Update the value of the voltage on the AOs. 
        Also Automatically write it on the FPGA.
        This is for when we change the value in the setting or with the cross. 
        """
        _debug('GUIMap: slider_z_position_changed')
        
        #TODO Add the x and y voltage from the cross
        AOz = self.treeDic_settings['AO_z']
        Vz = value
        
        # Prepare the fpga with the values    
        self.fpga.prepare_AOs([AOz], [Vz])
        
        # Run the FPGA for updating its settings
        # It gonna run also the pre-existing pulse sequence. Hopefully it's 
        # gonna be the counter. 
        self.fpga.lets_go_FPGA()

        # Call the event to say "hey, stuff changed on the fpga"
        self.event_fpga_change()
        
    def update_slice_shown(self):
        """
        Show the slice corresponding to the indices
        """
        _debug('GUIMap: update_slice_shown ', self.treeDic_settings['Slice_shown'] )
        
        n = self.treeDic_settings['Slice_shown']
        
        # Ajdust the value if it exceed the stored data
        if n>=self.nb_of_slice:
            self.treeDic_settings['Slice_shown'] = self.nb_of_slice-1
            n = self.treeDic_settings['Slice_shown']
        # Get the slice
        self.databox_scan = self.list_databox_scans[n]
        
        # Extract the data
        self.label_slice_date = self.databox_scan.h('date')
        self.Vxmin = self.databox_scan.h('Vx_min')
        self.Vxmax = self.databox_scan.h('Vx_max')
        self.Nx    = self.databox_scan.h('Nx')
        self.Vymin = self.databox_scan.h('Vy_min')
        self.Vymax = self.databox_scan.h('Vy_max')
        self.Ny    = self.databox_scan.h('Ny')
        
        self.Z = np.zeros([self.Nx, self.Ny])
        # Add each column 
        for i in range(self.Ny):
            self.Z[i] = self.databox_scan['Col%d'%i]      
            
        # Update the image
        self.initialize_image()
        self.update_image()
        
    def update_colormap(self):
        """
        Update the color of the image to fit the settings
        """        
        _debug('GUIMap: update_colormap ')
        
        name = self.treeDic_settings['Colormap']
        mycmap = PersonalColorMap().get_colormap(name)
        self.plot_image.setColorMap(mycmap)
            
    def button_scan_clicked(self):
        """
        Start or stop the scan
        """
        _debug('GUIMap: button_scan_clicked')
        
        if self.is_scanning == False:
            # Note that we are scanning
            self.button_scan.set_text('Stop :O')
            self.button_scan.set_style('background-color: rgb(255, 100, 100);')
            self.is_scanning = True
            
            # Remove the subregion if there is one
            if self.is_selecting_subregion:
                self.button_subregion_clicked()
            # Run the scan
            self.run_scan()
        else:
            # Stop to take counts if we were taking counts
            self.is_scanning = False # We stopped to scan
            self.button_scan.set_text('Scan :D')
            self.button_scan.set_style('background-color: rgb(0, 200, 0);')  

    def button_subregion_clicked(self):
        """
        This button is for allowing to select a subregion. 
        If we click, we show a ROI for selcting the subregion to select for 
        the next scan. 
        If we click again, we remove this subregion from the view. 
        
        """
        _debug('GUIMap: button_subregion_clicked')
        
        if self.is_selecting_subregion == False:
            # Note that we are scanning
            self.button_subregion.set_text('Remove the selection\nof subregion')
            self.button_subregion.set_style('background-color: rgb(255, 100, 100);')
            self.is_selecting_subregion = True
            
            # Place the ROI for selection the subregion
            size_x = (self.Vxmax-self.Vxmin)/2
            size_y = (self.Vymax-self.Vymin)/2
            self.ROI_subregion = egg.pyqtgraph.RectROI((self.vLine.getXPos()-size_x/2, 
                                            self.hLine.getYPos() -size_y/2),
                                           pen=(50,255,50),
                                           size=(size_x,size_y))
            self.plot_image.addItem(self.ROI_subregion)
            # Connect it
            self.connect(self.ROI_subregion.sigRegionChanged, self.ROI_subregion_change)            
            
        else:
            # Stop to take counts if we were taking counts
            self.is_selecting_subregion = False # We stopped to scan
            self.button_subregion.set_text('Select a \nsubregion ;)')
            self.button_subregion.set_style('background-color: rgb(0, 200, 0);')
            
            # Remove the ROI
            self.plot_image.removeItem(self.ROI_subregion)

    def button_autoregion_clicked(self):
        """
        Auto set the region to scan.
        TODO Add the option to preset the auto region ?
        """
        _debug('GUIMap: button_autoregion_clicked')
        # Update the settings
        self.treeDic_settings['X_min'] = -10
        self.treeDic_settings['Y_min'] = -10
        self.treeDic_settings['X_max'] = 10
        self.treeDic_settings['Y_max'] = 10      

    def button_center_cursor_clicked(self):
        """
        Recenter the cursor at the middle of the map.
        """        
        _debug('GUIMap: button_center_cursor_clicked')
        
        # Update the cross
        xmin = self.treeDic_settings['X_min'] 
        ymin = self.treeDic_settings['Y_min']  
        xmax = self.treeDic_settings['X_max'] 
        ymax = self.treeDic_settings['Y_max']  
        self.ptROI.setPos(( (xmin+xmax)/2 , (ymin+ymax)/2)  )      

#TODO remove the "s" at scans in the name of the method !
    def button_save_scans_clicked(self):
        """
        Save the actually shown slice
        """                       
        _debug('GUIMap: button_save_scans_clicked')
        
        # Note the information on the actually scan
        # We do not store it, for note poping the last scan. 
        N_col = len(self.Z) # Number of columns
        self.databox_scan.insert_header('date', self.label_slice_date)
        self.databox_scan.insert_header('Vx_min', self.Vxmin)
        self.databox_scan.insert_header('Vx_max', self.Vxmax)
        self.databox_scan.insert_header('Nx', self.Nx)
        self.databox_scan.insert_header('Vy_min', self.Vymin)
        self.databox_scan.insert_header('Vy_max', self.Vymax)
        self.databox_scan.insert_header('Ny', self.Ny)
        self.databox_scan.insert_header('N_col', N_col)
        # Add all the element of the three dictionnary
        for key in self.treeDic_settings.get_keys():
            # Add each element of the dictionnary three
            self.databox_scan.insert_header(key , self.treeDic_settings[key])        
        # Add each column 
        for i in range(N_col):
            col = self.Z[i]
            self.databox_scan['Col%d'%i] = col    
            
        # This will open a dialog window for saving the databox
        self.databox_scan.save_file()

    def button_load_scans_clicked(self):
        """
        Load scans. 
        It load what is saved with the complement method "button_save_scans_clicked".
        
        If there is more than one databox selected, it gonna take them as the 
        list of databox's
        
        """                       
        _debug('GUIMap: button_load_scans_clicked')
        
        # Get the databob
        ds = sm.data.load_multiple(text='Load one or more scans')
        
        if len(ds)>1:
            # If we selected more than one databox, set them as the new list
            self.list_databox_scans = ds
        else:
            # If we selected only one databox, overid the last scan
            self.list_databox_scans[-1] = ds[0]
#            # Store the image
#            self.store_scan()

        # Take the last element to show. 
        self.databox_scan = self.list_databox_scans[-1]
            
        # Extract the data
        self.label_slice_date = self.databox_scan.h('date')
        self.Vxmin = self.databox_scan.h('Vx_min')
        self.Vxmax = self.databox_scan.h('Vx_max')
        self.Nx    = self.databox_scan.h('Nx')
        self.Vymin = self.databox_scan.h('Vy_min')
        self.Vymax = self.databox_scan.h('Vy_max')
        self.Ny    = self.databox_scan.h('Ny')
        
        # Set the tree dictionnary, in case that we would like to rescan the 
        # Same parameter
        self.treeDic_settings['X_min'] = self.Vxmin
        self.treeDic_settings['Y_min'] = self.Vymin
        self.treeDic_settings['X_max'] = self.Vxmax
        self.treeDic_settings['Y_max'] = self.Vymax
        self.treeDic_settings['Nb_point_X'] = self.Nx 
        self.treeDic_settings['Nb_point_Y'] = self.Ny
        
        self.Z = np.zeros([self.Ny, self.Nx])
        # Add each column 
        for i in range(self.Ny):
            self.Z[i] = self.databox_scan['Col%d'%i]      
            
        # Update the image
        self.initialize_image()
        self.update_image()
        
        
    def ROI_subregion_change(self):
        """
        Adjust the boundary of the subregion to be scan
        """
#        _debug('GUIMap: ROI_subregion_change')
        
        # Get the boundary
        xmin = self.ROI_subregion.viewPos().x()
        ymin = self.ROI_subregion.viewPos().y()
        xmax = xmin + self.ROI_subregion.size()[0]
        ymax = ymin + self.ROI_subregion.size()[1]
        
        # Update the settings
        self.treeDic_settings['X_min'] = xmin
        self.treeDic_settings['Y_min'] = ymin
        self.treeDic_settings['X_max'] = xmax
        self.treeDic_settings['Y_max'] = ymax
        
            
    def prepare_acquisition_pulse(self):
        """
        Prepare the acquisition of counts.
        
        It prepare the pulse pattern and set the wait time. 
        """
        _debug('GUICounts: prepare_acquisition')
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
        
        # Update the wait time
        wait_AO_time = self.treeDic_settings['Wait_after_AOs']
        self.fpga.prepare_wait_time(wait_AO_time)
        
         # Send the data_array to the FPGA
        self.fpga.prepare_pulse(self.data_array)

    def match_attributes_with_gui(self):
        """
        make the attributes to match with the settings on the gui
        """
        _debug('GUIMap: match_attributes_with_gui')
        
        # Determine some parameters for the image 
        self.Vxmin = self.treeDic_settings['X_min']
        self.Vxmax = self.treeDic_settings['X_max']
        self.Nx    = self.treeDic_settings['Nb_point_X']
        self.Vymin = self.treeDic_settings['Y_min']
        self.Vymax = self.treeDic_settings['Y_max']        
        self.Ny    = self.treeDic_settings['Nb_point_Y']
        self.Vz    = self.slider_z_position.get_value()
        
        
    def initialize_image(self):
        """
        Prepare the image to be shown with the actual parameters. 
        This sets up the axis, the ROIs, etc. 
        TODO Reorganiz the way we initialize and update the image
        """
        _debug('GUIMap: initialize_image')
        
        # Set the axis
        self.plot_item.setLabel('bottom', text='Vx')
        self.plot_item.setLabel('left', text='Vy')
              
        # Get the right scaling
        self.scale_x = (self.Vxmax- self.Vxmin)/self.Nx
        self.scale_y = (self.Vymax- self.Vymin)/self.Ny
        
        # Update the ROI for the center of the cursor
        self.size_ptROI_x = (self.Vxmax-self.Vxmin)/20
        self.size_ptROI_y = (self.Vymax-self.Vymin)/20
        self.pos_ptROI_x = self.vLine.getXPos()
        self.pos_ptROI_y = self.hLine.getYPos()
        
        x = self.pos_ptROI_x-self.size_ptROI_x/2
        y = self.pos_ptROI_y-self.size_ptROI_y/2
        self.ptROI.setPos((x,y))
        self.ptROI.setSize( (self.size_ptROI_x,self.size_ptROI_y) )
        
        # Update the cross-hair
        self.vLine.setPos((self.Vxmin+self.Vxmax)/2)
        self.hLine.setPos((self.Vymin+self.Vymax)/2)        

        # Update the text label 
        self.textitem_slice.setText(self.label_slice_date)
        self.textitem_slice.setPos(self.Vxmin, self.Vymin)        
        
        
    def update_image(self):
        """
        Update the map with the actual Z
        """
        _debug('GUIMap: update_image')

        # Set the ratio according to the wishes
        value = self.treeDic_settings['Set_aspect']
        self.plot_image.view.setAspectLocked(value) # Input True for having the scaling right. 
        
        # Multiply the y axis by the factor
        yfactor = self.treeDic_settings['yfactor_aspect_ratio']
        
#        self.transform =self.plot_image.view.transform()
#        self.t1 = self.transform.shear(1,yfactor)
        self.plot_image.setImage(self.Z.T,
                                 pos=(self.Vxmin, self.Vymin),
                                 scale =(self.scale_x, self.scale_y*yfactor))
        
        # scale/pan the view to fit the image.
        self.plot_image.autoRange()
        
        # Update the color map
        self.update_colormap()
        
    def store_scan(self):
        """
        Store the information of the actual shown scan. 
        """    
        _debug('GUIMap: store_scan')
        
        # Create the databox
        self.databox_scan = sm.data.databox()
        
        N_col = len(self.Z) # Number of columns
        self.databox_scan.insert_header('date', self.label_slice_date)
        self.databox_scan.insert_header('Vx_min', self.Vxmin)
        self.databox_scan.insert_header('Vx_max', self.Vxmax)
        self.databox_scan.insert_header('Nx', self.Nx)
        self.databox_scan.insert_header('Vy_min', self.Vymin)
        self.databox_scan.insert_header('Vy_max', self.Vymax)
        self.databox_scan.insert_header('Ny', self.Ny)
        self.databox_scan.insert_header('N_col', N_col)
        # Add each column 
        for i in range(N_col):
            col = self.Z[i]
            self.databox_scan['Col%d'%i] = col              


        if self.nb_of_slice > self.nb_max_slice:
            # Pop the oldest stored slice if we exceed the nb of slices
            _debug('GUIMap: store_scan: poping oldest scan.')
            self.list_databox_scans.pop(0)

        # Append the new scan
        self.list_databox_scans.append(self.databox_scan)
        
        # Update the number of slice
        self.nb_of_slice = len(self.list_databox_scans)    
        
        

        
    def run_scan(self):
        """
        Ultimate function which scans !
        """
        _debug('GUIMap: run_scan')
        
        # First initiate the scan
        
        # Prepare the pulse sequence
        self.prepare_acquisition_pulse()
        
        # Take the attributes in the gui. 
        self.match_attributes_with_gui()
        # Prepare the image
        self.initialize_image()
        
        # Note the date of the scan
        self.label_slice_date = time.ctime(time.time())
        
        # Prepare the x and y position to scan
        self.xs = np.linspace(self.Vxmin, self.Vxmax, self.Nx)
        self.ys = np.linspace(self.Vymin, self.Vymax, self.Ny)
        
        self.X,self.Y = np.meshgrid(self.xs,self.ys)
        self.Z = np.zeros(np.shape(self.X))
        
        
        # Note the AOs to take
        self.AOx = self.treeDic_settings['AO_x']
        self.AOy = self.treeDic_settings['AO_y']
        self.AOz = self.treeDic_settings['AO_z']
        
        # Prepare the progress bar
        self.progress_bar.setValue(0)       
        
        
        # Now we can scan, according to which type of scan to do
        if   self.treeDic_settings['Scanning_mode'] == 'Sawtooth':
            self.scan_row_sawtooth()
        elif self.treeDic_settings['Scanning_mode'] == 'Snake':
            self.scan_row_snake()       
        elif self.treeDic_settings['Scanning_mode'] == 'Spiral':
            self.scan_spiral()   
        elif self.treeDic_settings['Scanning_mode'] == 'Diagonal_sweep':
            self.scan_diagonal_sweep()
        elif self.treeDic_settings['Scanning_mode'] == 'Random':
            self.scan_random_points()   
            
        # At this poin the scan is completed or stopped
        # Store the scan
        self.store_scan()
        
        # recenter the Cursor
        self.button_center_cursor_clicked()
        
        # Update the GUI
        if self.is_scanning:
            # This stop the scan if self.is_scanning = True
            self.button_scan_clicked()       
        
    def scan_row_sawtooth(self):
        """
        This scans each row and update the image after each row. 
        It is called sawtooth because, after each row, the voltage in x is coming
        back to the initial x voltage. 
        
        """
        _debug('GUIMap: scan_row_sawtooth')
             
        # Start the scan
        self.row = 0
        while self.is_scanning and self.row<len(self.ys):
            # Note the time at which the row starts
            self.time_row_start = time.time()
            _debug('sawtooth Row ', self.row)
        
            # Get the voltrage in Y
            Vy = self.ys[self.row]
            
            for i in range(len(self.xs)):
                # Get the voltage in x
                Vx = self.xs[i]
                
                # Update the voltage of the AOs
                self.list_AOs = [self.AOx, self.AOy, self.AOz]
                self.list_Vs = [Vx, Vy, self.Vz]
                self.fpga.prepare_AOs(self.list_AOs, self.list_Vs)
                
                # Get the count, finally ;) 
                # Two step: runt he pulse pattern and get the counts. 
                self.fpga.run_pulse() # This will also write the AOs
                self.counts =  self.fpga.get_counts()[0]
                self.counts_per_sec = 1e3*self.counts/self.count_time_ms
                
                # Since zero is boring, let's add something
#                image = self.counts + np.random.poisson( np.abs(1000*np.cos(Vx*Vy*0.5)) )
#                self.Z[self.row][i]= image
                self.Z[self.row][i] = self.counts_per_sec
                    
            # Update the image after each row   
            self.update_image()
            
            # Note how much time it takes for the row
            self.time_row_elapsed = time.time() - self.time_row_start
            
            # Update the progress bar
            progress = 100*(self.row+1)/len(self.ys)
            self.progress_bar.setValue(progress)
            # Update the label for the progress
            nb_row_remaining = len(self.ys) - (self.row+1)
            sec = self.time_row_elapsed*nb_row_remaining
            self.label_progress.set_text('Time remaining: %.2f s'%sec)
            
            # Update the row for the next iteration
            self.row +=1
            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events()    

    def scan_row_snake(self):
        """
        This scans each row and update the image after each row. 
        It is called snake because, after each row, the voltage in x start at 
        it's previous value, instead of coming back to the other extrema like 
        the sawtooth.
        
        """
        _debug('GUIMap: scan_row_snake')
             
        # Start the scan
        self.row = 0
        while self.is_scanning and self.row<len(self.ys):
            # Note the time at which the row starts
            self.time_row_start = time.time()
            _debug('Sssssssnake Row ', self.row)
        
            # Get the voltrage in Y
            Vy = self.ys[self.row]
            
            # Note the order of the index to scan depending on which row we 
            # have for doing the snake scan.
            if self.row%2 == 0:
                i_s = range(len( self.xs ))
            else:
                i_s  = np.flip(range(len( self.xs )))
            
            # Scan this set of index
            for i in i_s:
                
                # Get the voltage in x
                Vx = self.xs[i]
                
                # Update the voltage of the AOs
                self.list_AOs = [self.AOx, self.AOy, self.AOz]
                self.list_Vs = [Vx, Vy, self.Vz]
                self.fpga.prepare_AOs(self.list_AOs, self.list_Vs)
                
                # Get the count, finally ;) 
                # Two step: runt he pulse pattern and get the counts. 
                self.fpga.run_pulse() # This will also write the AOs
                self.counts =  self.fpga.get_counts()[0]
                self.counts_per_sec = 1e3*self.counts/self.count_time_ms
                
                # Since zero is boring, let's add something
    #                image = self.counts + np.random.poisson( np.abs(1000*np.cos(Vx*Vy*0.5)) )
    #                self.Z[self.row][i]= image
                self.Z[self.row][i] = self.counts_per_sec


                   
            # Update the image after each row   
            self.update_image()
            
            # Note how much time it takes for the row
            self.time_row_elapsed = time.time() - self.time_row_start
            
            # Update the progress bar
            progress = 100*(self.row+1)/len(self.ys)
            self.progress_bar.setValue(progress)
            # Update the label for the progress
            nb_row_remaining = len(self.ys) - (self.row+1)
            sec = self.time_row_elapsed*nb_row_remaining
            self.label_progress.set_text('Time remaining: %.2f s'%sec)
            
            # Update the row for the next iteration
            self.row +=1
            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events()    

    def scan_random_points(self):
        """
        This scans random points on the map. 
        """
        _debug('GUIMap: scan_random_points')
        
        self.Ntotal = self.Nx*self.Ny # Total number of point to scan
        # create a list for labelling ALL the points
        self.list_pts = range(self.Ntotal) # This 
        
        # Scan until all the points got scanned
        self.iteration = 0
        while self.is_scanning and len(self.list_pts)>0:
            
            # Note the time at which a batch starts
            self.time_row_start = time.time()
            self.iteration +=1 
            _debug('GUIMap: scan_random_points', self.iteration)
            
            # To speed up, do batches before updating
            for i in range(self.Nx):
                # Pick a random number
                self.pt_choosen = np.random.choice(self.list_pts)
                # Extract the corresponding row and column
                self.row    = int(self.pt_choosen/self.Nx) 
                self.column = int(self.pt_choosen - self.Nx*self.row)
                # Delete this number from the list for the next pickup
                self.index_to_delete = np.where(self.list_pts==self.pt_choosen)[0][0]
                self.list_pts = np.delete(self.list_pts, self.index_to_delete)
#                # for debugging
#                print('self.index_to_delete = ',self.index_to_delete)
#                print('len(self.list_pts) = ',len(self.list_pts))
                
                # Get the voltrage in Y
                Vy = self.ys[self.row]            
                # Get the voltage in x
                Vx = self.xs[self.column]        

                # Update the voltage of the AOs
                self.list_AOs = [self.AOx, self.AOy, self.AOz]
                self.list_Vs = [Vx, Vy, self.Vz]
                self.fpga.prepare_AOs(self.list_AOs, self.list_Vs)
                
                # Get the count, finally ;) 
                # Two step: runt he pulse pattern and get the counts. 
                self.fpga.run_pulse() # This will also write the AOs
                self.counts =  self.fpga.get_counts()[0]
                self.counts_per_sec = 1e3*self.counts/self.count_time_ms
                
#                # Since zero is boring, let's add something
#                image =  100+np.random.poisson( np.abs(10000*np.cos(Vx*Vy*0.5)) )
#                self.Z[self.row][self.column]= image
                
                self.Z[self.row][self.column] = self.counts_per_sec     
                
                   
            # Update the image after each row   
            self.update_image()
            
            # Note how much time it takes for the row
            self.time_row_elapsed = time.time() - self.time_row_start
            
            # Update the progress bar
            progress = 100*(self.iteration)/self.Ny
            self.progress_bar.setValue(progress)
            # Update the label for the progress
            nb_iter_remaining = self.Ny - self.iteration # Number of iteration remaining
            sec = self.time_row_elapsed*nb_iter_remaining
            self.label_progress.set_text('Time remaining: %.2f s'%sec)
            
            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events()    

            
    def scan_diagonal_sweep(self):
        """
        This scans by sweeping in diagonal. 
        
        #TODO complete this ! Scan the other half and deal with different
        # Size for x and y
        """
        _debug('GUIMap: scan_diagonal_sweep')
        
        #Note the sizes
        Nx = len(self.xs)
        Ny = len(self.ys)

        # Note the indices to scan
        i_s = range(Nx)
        j_s = range(Ny)
        
        # Estimate the total area for the progress bar
        total_area = Nx*Ny 

        # Note the time at which we start
        self.time_start = time.time()
            
        # Start the scan
        self.diagonal = 0
        # Scan each diagonal
        while self.is_scanning and self.diagonal<Ny:

            
            _debug('Diagonal :D ', self.diagonal)
            # Do the diagonal !
            for k in range(self.diagonal+1):
                i = i_s[k]
                j = j_s[self.diagonal-k]
                
                Vx = self.xs[i]
                Vy = self.ys[j]
                
                # Update the voltage of the AOs
                self.list_AOs = [self.AOx, self.AOy, self.AOz]
                self.list_Vs = [Vx, Vy, self.Vz]
                self.fpga.prepare_AOs(self.list_AOs, self.list_Vs)
                
                # Get the count, finally ;) 
                # Two step: runt he pulse pattern and get the counts. 
                self.fpga.run_pulse() # This will also write the AOs
                self.counts =  self.fpga.get_counts()[0]
                self.counts_per_sec = 1e3*self.counts/self.count_time_ms
                
                # Since zero is boring, let's add something
#                image = self.counts + np.random.poisson( np.abs(1000*np.cos(Vx*Vy*0.5)) )
#                self.Z[j][i]= 100+np.random.poisson( np.abs(10000*np.cos(Vx*Vy*0.5)) )
                self.Z[j][i] = self.counts_per_sec         
                
                
                    
            # Update the image after each row   
            self.update_image()
            
            # Note how much time it tooks so far
            self.time_elapsed = time.time() - self.time_start
            
            # Updathe the labels
            # Update the progress bar
            area_swept = (self.diagonal+1)**2/2
            progress = 100*area_swept/total_area
            self.progress_bar.setValue(progress)
            # Update the label for the progress
            t_tot = self.time_elapsed*total_area/area_swept
            t_remaining=  t_tot - self.time_elapsed
            self.label_progress.set_text('Time remaining: %.2f s / %.2f'%(t_remaining,t_tot))
            
            # Update the row for the next iteration
            self.diagonal +=1
            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events()    
            
            
    def scan_spiral(self):
        """
        This scans by following a spiral. 
        It starts at the middle, than whirl around the image lol. 
        
        """
        _debug('GUIMap: scan_row_spiral')
        
        #Note the sizes
        Nx = len(self.xs)
        Ny = len(self.ys)
        
        # Note the indices to scan
        i_s = range(Nx)
        j_s = range(Ny)
        
        # Starting point
        i_start = int(Nx/2)
        j_start = int(Ny/2)
        
        
        
        
        # Start the scan
        self.row = 0
        while self.is_scanning and self.row<len(self.ys):
            # Note the time at which the row starts
            self.time_row_start = time.time()
            
            _debug('Spiral ! ')
            print('THIS IS NOT IMPLEMENTED LOL')
            time.sleep(0.2)
            
                    
            # Update the image after each row   
            self.update_image()
            
            # Note how much time it takes for the row
            self.time_row_elapsed = time.time() - self.time_row_start
            
            # Update the progress bar
            progress = 100*(self.row+1)/len(self.ys)
            self.progress_bar.setValue(progress)
            # Update the label for the progress
            nb_row_remaining = len(self.ys) - (self.row+1)
            sec = self.time_row_elapsed*nb_row_remaining
            self.label_progress.set_text('Time remaining: %.2f s'%sec)
            
            # Update the row for the next iteration
            self.row +=1
            # Allow the GUI to update. This is important to avoid freezing of the GUI inside loops
            self.process_events()    
            
    def pos_ptROI_changed(self):
        """
        When the centre ROI change.
        Change the lines to fit the center
        """
        
        # Important condition for avoiding infinite call
        if (not(self.is_pos_vLine_changing) and
            not(self.is_pos_hLine_changing)):
            _debug('GUIMap: pos_ptROI_changed')
            
            #Set the position of the cross-hair lines
            self.vLine.setPos(self.ptROI.pos()[0]+self.size_ptROI_x/2)
            self.hLine.setPos(self.ptROI.pos()[1]+self.size_ptROI_y/2)
    
    def pos_vLine_changed(self):
        """
        When the position of the vLine changes.
        Adjust the central ROI
        """
        _debug('GUIMap: pos_vLine_changed')
        
        # Update the boolean to avoid inifinite call
        self.is_pos_vLine_changing = True
        # Keep the y position, but change x
        self.ptROI.setPos((self.vLine.getPos()[0]-self.size_ptROI_x/2,
                           self.ptROI.pos()[1]))
        # Set the voltage if it's outside of a scan
        if not(self.is_scanning):
            self.set_voltage_x(self.vLine.getXPos())
        # Update the boolean  
        self.is_pos_vLine_changing = False

    def pos_hLine_changed(self):
        """
        When the position of the hLine changes.
        Adjust the central ROI
        """
        _debug('GUIMap: pos_hLine_changed')
        
        # Update the boolean to avoid inifinite call
        self.is_pos_hLine_changing = True
        # Keep the x position, but change y
        self.ptROI.setPos((self.ptROI.pos()[0],
                          self.hLine.getPos()[1]-self.size_ptROI_y/2 ))  
        # Set the voltage if it's outside of a scan
        if not(self.is_scanning):
            self.set_voltage_y(self.hLine.getYPos())
        # Update the boolean    
        self.is_pos_hLine_changing = False
        
        
        
    def set_voltage_x(self, Vx):
        """
        Set the voltage of x
        """
        _debug('GUIMap: set_voltage_x')

        # Note the AOs to take
        self.AOx = self.treeDic_settings['AO_x']
        self.list_AOs = [self.AOx]
        # Prepare the voltage
        self.list_Vs = [Vx]
        self.fpga.prepare_AOs(self.list_AOs, self.list_Vs)   
        
        # Run the FPGA for updating its settings
        # It gonna run also the pre-existing pulse sequence. Hopefully it's 
        # gonna be the counter. 
        self.fpga.lets_go_FPGA()

        # Call the event to say "hey, stuff changed on the fpga"
        self.event_fpga_change()
        
    def set_voltage_y(self, Vy):
        """
        Set the voltage of y
        """
        _debug('GUIMap: set_voltage_y')

        # Note the AOs to take
        self.AOy = self.treeDic_settings['AO_y']
        self.list_AOs = [self.AOy]
        # Prepare the voltage
        self.list_Vs = [Vy]
        self.fpga.prepare_AOs(self.list_AOs, self.list_Vs)  
    
        # Run the FPGA for updating its settings
        # It gonna run also the pre-existing pulse sequence. Hopefully it's 
        # gonna be the counter. 
        self.fpga.lets_go_FPGA()

        # Call the event to say "hey, stuff changed on the fpga"
        self.event_fpga_change()
        
    def update_GUI_with_fpga(self):
        """
        Update the gui such that the widgets match with the fpga. 
        That is useful for the implementation with other GUI that also 
        modifies the fpga. 
        """
        _debug('GUIMap: update_GUI_with_fpga')
        
        if not(self.is_scanning): # Don't mess up with the scan lol
            # Update the value of the Z voltage
            AO = self.treeDic_settings['AO_z']
            self.slider_z_position.set_value(self.fpga.get_AO_voltage(AO))
            # Update the cross
            AOx = self.treeDic_settings['AO_x']
            Vx = self.fpga.get_AO_voltage(AOx)
            AOy = self.treeDic_settings['AO_y']
            Vy = self.fpga.get_AO_voltage(AOy)
            self.ptROI.setPos((Vx - self.size_ptROI_x/2,
                               Vy - self.size_ptROI_y/2))       
            
    def event_fpga_change(self):
        """
        Dummy function to be overrid. 
        
        It is called after that the value on the fpga changed.
        Not call during the scan, because it would be too much.
        """           
        return
        
      
        
class PersonalColorMap():
    """
    This class is aimed to store various colormap that we would like to use. 
    """
    def __init__(self):
        """
        """
        
        # Contains all the name of the color map that we have. 
        self.list_colormaps = ['Awesome', 
                               'old_time',
                               'stairway_to_heaven',
                               'halloween',
                               'fear_of_the_dark',
                               'sonic_supersonic',
                               'ca_va_bien_aller']
        
    def get_list_colormaps(self):
        return self.list_colormaps
    
    def get_colormap(self, name):
        """
        name:
            String contained in list_colormaps. 
            
        """
        if name == 'Awesome':
            return self.awesome()
        if name == 'old_time':
            return self.old_time()
        if name == 'halloween':
            return self.halloween()
        if name == 'stairway_to_heaven':
            return self.heaven()
        if name == 'sonic_supersonic':
            return self.sonic_supersonic()
        if name == 'ca_va_bien_aller':
            return self.ca_va_bien_aller()
        if name == 'fear_of_the_dark':
            return self.black_red_black()
        
    def awesome(self):
        """
        This is in the pyqtgraph example
        """
        
        colors = [
            (0, 0, 0),
            (45, 5, 61),
            (84, 42, 55),
            (150, 87, 60),
            (208, 171, 141),
            (255, 255, 255)
        ]
        
        return egg.pyqtgraph.colormap.ColorMap(pos=np.linspace(0.0, 1.0, 6), color=colors)
        
    def old_time(self):
        """
        Black and white. 
        """
        colors = [
                (0, 0, 0),
                (255, 255, 255)]
        
        return egg.pyqtgraph.colormap.ColorMap(pos=np.linspace(0.0, 1.0, 2), color=colors)
        
    def halloween(self):
        """
        Black to orange to red
        """        
        colors = [
                (0, 0, 0),
                (255, 127, 39),
                (255, 0, 0)]
        
        return egg.pyqtgraph.colormap.ColorMap(pos=np.linspace(0.0, 1.0, 3), color=colors)        

    def heaven(self):
        """
        White to yellow to cyan
        """        
        colors = [
                (255, 255, 255),
                (255, 255, 20),
                (0, 255, 255)]
        
        return egg.pyqtgraph.colormap.ColorMap(pos=np.linspace(0.0, 1.0, 3), color=colors) 
    
    def black_red_black(self):
        """
        Black, red in the middle, black again
        """
        colors = [
                (0, 0, 0),
                (255, 127, 39),
                (255, 0, 0),
                (255, 127, 39),
                (0, 0, 0)]
        
        return egg.pyqtgraph.colormap.ColorMap(pos=np.linspace(0.0, 1.0, len(colors)), color=colors)  
    
    
    def sonic_supersonic(self):
        """
        White to yellow to blue
        """        
        colors = [
                (255, 255, 255),
                (155, 155, 0),
                (0, 0, 200)]
        
        return egg.pyqtgraph.colormap.ColorMap(pos=np.linspace(0.0, 1.0, 3), color=colors) 
    
    def ca_va_bien_aller(self):
        """
        Rainbow 
        """
        
        colors = [
                (255, 0, 0),
                (255, 255, 0),
                (0, 255, 0),
                (0, 255, 255),
                (0, 0, 255),
                (255, 0, 255)]
        
        return egg.pyqtgraph.colormap.ColorMap(pos=np.linspace(0.0, 1.0, len(colors)), color=colors)         
    
    
    
        
    
    
    

if __name__ == '__main__':
    
    import api_fpga as _fc
    
    _debug_enabled     = True
    _fc._debug_enabled = False
    
    sm.settings['dark_theme'] = False
    
    print('Hey on es-tu bin en coton-watte')
    
     # Create the fpga api
    bitfile_path = ("X:\DiamondCloud\Magnetometry\Acquisition\FPGA\Magnetometry Control\FPGA Bitfiles"
                    "\Pulsepattern(bet_FPGATarget_FPGAFULLV2_WZPA4vla3fk.lvbitx")
    resource_num = "RIO0"     
    fpga = _fc.FPGA_api(bitfile_path, resource_num) # Create the api   
    fpga.open_session()
    
    
    self = GUIMap(fpga)
    self.show()
    





