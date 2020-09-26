# -*- coding: utf-8 -*-
"""
Created on Thu Apr  9 14:52:12 2020

Goal: Convert the use-friendly pulse patterns into fpga instruction. 
      The conversion process replicates what Lily implemented in labview 
      with this VI:  Host Pattern SubVI LC.vi

@author: Michael
"""

#Module from Python
import numpy as np
import matplotlib.pyplot as plt

# Debug stuff.
_debug_enabled                = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))


class Converter():
    """
    Goal: convert a sequence of pulse pattern into the corresponding FPGA
          instruction
    TODO: explain each step of the process of conversion  
    """
    
    def __init__(self, tickDuration=1/120, nbChannel=16, maxTicks=2**16-1):
        """
        Input
        nbChannel: 
            Total number of channel on the FPGA
        tickDuration:
            Duration of a ticks (us) on the FPGA
        maxTicks: 
            Maximum number of ticks per single instuction on the FPGA
        """
        self.tickDuration = tickDuration
        self.nbChannel = nbChannel
        self.maxTicks = maxTicks
    
    def pattern_to_FPGA(self, block_pattern):
        """
        Ultimate function thats input the pulse patterns that the user wants and 
        convert it into a sequence of instruction for the FPGA, in the form of 
        a data array of int32. 
        
        Each step of this conversion is commented bellow. 
        To visualize how the pattern is converted into FPGA instruction at each
        step, enable the debugger (set _debug_enabled=True at the begining of 
        the script). 
        
        Input:
            block_pattern
            PulsePatternBlock object to be converted into a list of int32 for the
            FPGA. This object is from "pulses.py"   
                       
        Return :
            data_FPGA
            Array of int32 corresponding to the data to be sent to the FPGA.  
        
        """
        self.block_pattern = block_pattern 
        
        # Step 1: For each channel events in the block, create an structure 
        # for what happens at each tick
        self.events_channels_s= self.structure_block(self.block_pattern)
        _debug()
        _debug('Step 1: Restructure the instruction of each pulse pattern.')
        _debug(self.events_channels_s)
        
        # Step 2: Sort the events
        self.events_channels_s_sorted = np.sort(self.events_channels_s, order='Time')
        _debug()
        _debug('Step 2: Sort the events')
        _debug(self.events_channels_s_sorted) 
        
        # Step 3:  Merge the time that are equal to each other
        self.events_channels_s_merged = self.merge_events(
                self.events_channels_s_sorted)
        _debug()
        _debug('Step 3: Merge the events')
        _debug(self.events_channels_s_merged)    
        
        # Step 4: Take the time difference and add the events together
        self.instructions = self.time_diff(self.events_channels_s_merged)
        _debug()
        _debug('Step 4: Take time difference')
        _debug(self.instructions)

        # Step 6: Convert each instruction into int32 
        self.data_block = self.convert_into_int32(self.instructions)
        _debug()
        _debug('Step 6: Convert each instruction into int32 ')
        _debug(self.data_block)       
        _debug()
        
        return self.data_block
        
    
    def structure_block(self, block_pattern):
        """
        Re-structure the informations contained in block_pattern. 
        It transform the block of pulse pattern into an object called 
        "events_channels_s", which contains the times at which the channels are 
        turned ON and OFF. This object is explained in the return section below. 
        
        
        Input
        block_pattern: PulsePatternBlock object to be converted into a list of int32
                       for the FPGA.  
        return
        events_channels_s: 
                      Array of tuple. Each tuple corresponds to an event. 
                      The tuple contains a time and an array of channel event.
                      The time is the time at which the event occurs.
                      Each element of the array of channel event is an 
                      event for the corresponfing channel (The first element 
                      correspond to channel 0, the second to channel 1, etc.). 
                      The event is 0, +1 or -1:
                          0  means that the channel doesn't change its state. 
                          +1 means that the channel raises (Turn ON)
                          -1 means that the channel falls (Turn OFF)
                      To summarize:
                      channels_events_s = [channels_events1, channels_events2, ...]
                      Where
                      channels_eventsi = (time, events)
                      Where 
                      time = time at which event occurs
                      events = [event_channel0, event_channel1, ...]
                      Where 
                      event_channeli = 0,+1 or -1 = what is happening with 
                                                    channel #i
                     
        """
        
        # Define what is the structure of each row of the outputs
        self.dtype = [('Time', float), ('channels events', np.ndarray)] # These definition will be usefull for the numpy sort algorithm
        
        # Initialize the first event to be state OFF for each channel
        events_channels_s = [(0, tuple(np.zeros(self.nbChannel)))] # Initialize the first instruction to be state OFF for each channel
        
        # Append all the events from each channel
        for channel_object in block_pattern.get_pulse_pattern():
            #Extract information about the pulse pattern
            times   = channel_object.get_pulses_tick() # Times at which events occur (in ticks)
            channel = channel_object.get_channel() # Channel at which the event occurs
            nbEvent = len(times)      # Number of event to verify
            
            #Initialize an array containing the state for this channel
            #In this array, 0 means no changes. 1 means switch ON. -1 means switch OFF
            events = np.zeros(self.nbChannel) 
            for i in range(nbEvent):
                #The "even" elements of "times" correspond to a swtich ON and the
                #"odd" elements correspond to a switch OFF. 
                if i%2 == 0:
                    #If the element is even, it corresponds to a switch ON
                    events[channel] = 1 #Assign 1
                else:
                    #If the element is odd, it corresponds to a switch OFF
                    events[channel] = -1 #Assign -1 
                #Append the instruction to the instructions structure
                channels_events = (times[i], tuple(events))
                events_channels_s.append(channels_events )
                
        ## create a structured array. This will ease the ordering with numpy
        events_channels_s = np.array(events_channels_s, dtype=self.dtype)      
        return events_channels_s
    
    def merge_events(self, events_channels_s_sorted):
        """
        Merge the events which are happening at the same time. 
        
        input: 
            events_channels_s_sorted
            Result of step 2 in the method "pattern_to_FPGA". 
            It is the list event sorted in time
        
        return:
            events_channels_s_merged
            The events sorted, with same time merged.
        """
        #This will contain the merged instructions
        events_channels_s_merged = []
        
        old_time = 0 #This  will store the time for the previous instruction in the loop
        events = np.zeros(self.nbChannel) #This will store the events for each instruction that occur at the same time
        
        # Scan over each event sorted
        for events_channels in events_channels_s_sorted:
            #Note the information of the current instruction
            new_time   = events_channels[0]
            new_events = events_channels[1]
            #Verify if the time of this instruction is the same as the last instruction
            if new_time == old_time:
                #If the times are equals, merge the state
                events += np.array(new_events) 
            else:
                #If the it is a new time
                #Append the previous instruction for the state before redefining the new states
                events_channels_s_merged.append((old_time,  tuple(events) ) )
                #Restart the events array with the actual instruction
                events = np.array(new_events)
            #Note the time of this instruction, for comparison with the next instruction
            old_time = new_time    
        
        #Append the last instruction that was not appended in the loop, because of the if
        events_channels_s_merged.append((old_time,  tuple(events) ) )
        
        # Verify if the first instruction is not all channel off
        if np.sum(events_channels_s_merged[0][1]) >0:
            # If all the channel are not off at the beginning, add an 
            # instruction to make them off. This solve many trouble, especially
            # with how the fpga will interprete reading the counts if DIO1 is 
            # ON at t=0
            first= (events_channels_s_merged[0][0],  tuple(np.zeros(self.nbChannel)) )
            events_channels_s_merged.insert(0, first)
        
        # Create a structured array. Especillay useful for investigating the array
        events_channels_s_merged = np.array(events_channels_s_merged, dtype=self.dtype)        
        return events_channels_s_merged
    
    def time_diff(self,events_channels_s_merged):
        """
        Take the time difference and add the events together to create the 
        state. 
        
        Input:
            events_channels_s_merged
            This is the ouput of the method "merge_events" 
       return:
           instructions
           Contain each time interval and the corresponding channel state 
            
        """

        #This will contain each time interval and the corresponding DIO state 
        instructions = []
    
        #Note the initial time
        prev_time   = events_channels_s_merged[0][0]
        prev_events = np.array(events_channels_s_merged[0][1])
        
        for i in range(len(events_channels_s_merged)-1):
            
            #Exract the time and the state
            new_time = events_channels_s_merged[i+1][0]
            new_events = np.array(events_channels_s_merged[i][1])
            #Take the time difference
            dt = new_time - prev_time
            channel_states = new_events+prev_events # Adding the events arrays create the states array
            #Append the instruction
            instructions.append((dt,  tuple(channel_states) ) )
            #Update the previous value
            prev_time   = new_time
            prev_events = channel_states          
    
        # Create a structured array. Especillay useful for investigating the array
        return np.array(instructions, dtype=self.dtype)

    def single_pulse_to_fpga(self,ticks, DIOstates):
        """
        Convert a single pulse instruction to 
        an FPGA instruction (a 32-bit number). 
        
        ticks: number of ticks that the FPGA will spend for this set of states. 
               ticks should be a less than 16 bit number, because it is the first 
               16 bits of the final number which represent the nb of ticks. 
               
        DIOstates: 16-lenght array. Each element correspond to the state of the 
                   corresponding DIO. 0=OFF; 1=ON 
        
        return: 32-bit number associated with these instruction. 
        """
        #TODO USE bitwise stuff instead !!!!! That night speed up things. 
        # Or keep it as it is if it is not more clear. 
        #Put the number of ticks into the 32 bit number. 
        x = int(ticks) #The first 16-bit is associated with the nb of ticks
        
        #The next 16 bits encode the state of the corresponding channel (0 = Off, 1 = On)
        for i in range(16, 32):
            #Each DIO state is either 0 or 1. So we write the next 16 bit in binary. 
            x += DIOstates[i-16]*2**i 
        #Return the 32 bit number.
        return x       

    def convert_into_int32(self, instructions):
        """
        Convert each instruction of time delay and channel into int32.
        
        Input:
            instructions
            This is the output of the method "time_diff". It is an array of 
            tuple=(dt, channel_states), where dt is the time interval (in tick)
            on which the state of each channel is defined by channel_states. 
            Each element of the array channel_states correspond to the state 
            of that channel (0=OFF, 1=ON)
            
        Return:
            data_FPGA
            Array of instructions in the form of int32 for the FPGA. 
            Each element of the array is a int32 and correspond to a single
            instruction for the FPGA. 
        """
        data_FPGA = [] # Contain instructions in the form of int32 for the FPGA
        
        for i, instruction in enumerate( instructions):
            # Extract the information for the the instruction
            ticks = instruction[0] # Number of ticks
            channel_states = instruction[1] # Channel states array
            
            # If there is too much tick for a single instruction, we gonna copy 
            # the same instruction many time. 
            if ticks > self.maxTicks:
                nbRepatedInstruction = int(ticks/(self.maxTicks))
                ExtraTicks = ticks - nbRepatedInstruction*self.maxTicks
                #Repeat the instruction 
                for jj in range(nbRepatedInstruction):
                    data_FPGA.append( self.single_pulse_to_fpga(self.maxTicks,
                                                          channel_states) )
                #If there are extra ticks, add them
                if ExtraTicks != 0:
                    data_FPGA.append( self.single_pulse_to_fpga(ExtraTicks, 
                                                               channel_states) )        
            else:
                #If the number of tick is below the number of extra tick, just append normaly
                data_FPGA.append( self.single_pulse_to_fpga(ticks, 
                                                           channel_states) )         
        return data_FPGA

    def sequence_to_FPGA(self, sequence, repetition):
        """
        Convert a sequence of pulse pattern into instruction for the FPGA, in 
        the form of a data array of int32.
        
        Input:
            sequence
            List of pulse patterns. This object is from "pulses.py" 
            
            repetition
            Number of time to repeat the sequence
         
        Return:
            data_FPGA
            Array of instructions in the form of int32 for the FPGA. 
            Each element of the array is a int32 and correspond to a single
            instruction for the FPGA.             
        """
        self.repetition = repetition
        
        self.data_blocks = [] # List of FPGA instruction for each block in the sequence 
        self.length_data_block_s = [] # List of the length of the data array for each block
        # Get the list of pulse pattern
        blocks = sequence.get_block_s()
        # Get the FPGA instruction for each block
        for block in blocks:
            self.data_array_per_block = self.pattern_to_FPGA(block)
            self.data_blocks.append( self.data_array_per_block )
            self.length_data_block_s.append(len(self.data_array_per_block))
            
            _debug('Length of block: ', self.length_data_block_s[-1])
        
        # Need to concatenate it before repeating it. 
        d_seq = np.concatenate(self.data_blocks)
        # Repeat the sequence
        self.data_FPGA = np.concatenate( [d_seq for _ in range(repetition)] )
        return self.data_FPGA
    
    def get_repetition(self):
        """
        Return the number of repetition of the sequence in the data array
        """
        return self.repetition
    
    def get_length_data_block_s(self):
        """
        Return the lenght of the data array for each block of the sequence
        """
        return self.length_data_block_s
    
    def get_data_blocks(self):
        """
        Get the list  data_blocks from the method sequence_to_FPGA. 
        This is very useful for investigating the FPGA instruction for each 
        block. 
        """
        return self.data_blocks
    
    def binary(self, n):
        """
        Iterative function to get the binary representation of a number. 
        
        n:
            Int for which we want the binary. 
        """
        return n>0 and [n&1]+self.binary(n>>1) or []
        
    def int32_to_ticks_and_DIOs(self, n):
        """
        Invert the data int32 for extracting the corresponding DIOs and number 
        of ticks. 
        
        n: 
            Int32 that we want to convert. 
        """
        _debug('Converter: int32_to_ticks_and_DIOs')
        
        # Get the 0's and 1's in the form of an array. 
        self.binary_array = self.binary(n)
        
        # Take the first 16 bits for the number of ticks
        ticks = 0
        tick_bits = self.binary_array[:16] # Those are the bits corresponding to the ticks
        for index in range(len(tick_bits)):
            bit = tick_bits[index]
            ticks += bit*2**index
            
        # Take the last 16 bits for the states of the DIOs
        dios_states = np.zeros(16)
        state_bits = self.binary_array[16:] # Those are the bits coresponding to the DIOs
        for index in range(len(state_bits)):
            state = state_bits[index]
            dios_states[index] = state
            
        return (ticks, dios_states)
            
        
        
    
        

# =============================================================================
# Plotting function for the pulse pattern.
# =============================================================================       
class GUIFPGAInstruction():
    """
    GUI to show the fpga instruction, block by block
    The GUI permits to double click to show the times 
    
    """
    def __init__(self, data_array, rep, length_data_block_s, 
                 list_DIO_to_show = [],
                 tickDuration=1/120, nbChannel=16): 
        """
        Initialize by sending the pulse pattern to plot
        
        Input:
            data_array
            The whole data array of the fpga
            
            rep
            Number of repetition of the sequence
            
            length_data_block_s
            Array containt the length of each block in the sequence
            
            list_DIO_to_show
            (list of int) If not empty, only the DIO in the list will be shown. 
            If empty, all the DIO will be shown.
            
        For example, if you want to show the whole data array instruction, you 
        can initiate the GUI like this:
            GUIFPGAInstruction(d, 1, [len(d)])
            
        """    
        
        self.data_array = data_array
        self.length_data_block_s = length_data_block_s
        self.list_DIO_to_show = list_DIO_to_show
        self.rep = rep 
        self.tickDuration = tickDuration
        self.nbChannel = nbChannel
        
        # Split the data_array 
        # This gonna be the total data array for one sequence
        self.data_each_seq = np.split( self.data_array, self.rep)[0]
        # Get the data_array for each block in the sequence
        self.indices_block = np.cumsum(length_data_block_s)
        self.data_each_block_s = np.split(self.data_each_seq, self.indices_block)
        
        # Some usefull variables
        self.nb_block =  len(self.data_each_block_s)-1
        self.ind_block = 0 # Index of the block to see
        self.nbLines = 0 #Number of lines for the times
        
        # Initialize the figure and axis
        self.fig, self.ax = plt.subplots(tight_layout=True)
        
        # Connect "scrolling the wheel" to its task
        self.fig.canvas.mpl_connect('scroll_event', self) # Connecting it to just "self" will go inside the method __call__
        # Connect "Clicking in the figure" to its task
        self.cid = self.fig.canvas.mpl_connect('button_press_event', self) # Connecting it to just "self" will go inside the method __call__
        
        # Show the masterpiece
        self.update()
        self.fig.show()
        
        return 
    
    def __call__(self,event):
        """
        event generated by mouse clicks or anything else. 
        """     
        self.event = event
        if (event.name=='button_press_event') and event.dblclick:
            """
            When the user double click, show the times with a vertical bar
            Only do it for double click. Otherwise it's hard to distinguish with other
            manipulation of the plot            
            """
            _debug('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
                  ('double' if event.dblclick else 'single', event.button,
                   event.x, event.y, event.xdata, event.ydata))            
            #Increment the number of line shown
            self.nbLines += 1 
            #get the positions for plotting the line
            xpos = event.xdata
            ymin = 0
            ymax = self.ax.dataLim.height
            #Plot the line and the label
            self.ax.plot([xpos, xpos], [ymin, ymax], 'k--', label='x%d=%f'%(self.nbLines, xpos))
            self.ax.text(xpos, ymax, 'x%d'%self.nbLines)
            self.ax.legend()
            #The following update the plot. 
            self.fig.canvas.draw_idle()  
            
        if event.name=='scroll_event':
            self.onscroll(event)
            
    def onscroll(self, event):
        """
        What to do when the mouse-wheel is scrolled
        """
        _debug("%s %s" % (event.button, event.step))
        
        if event.button == 'up':
            self.ind_block = (self.ind_block + 1) % self.nb_block
        else:
            self.ind_block = (self.ind_block - 1) % self.nb_block
        self.update()     
        
    def update(self):
        """
        Update the plot
        
        """
        # Clean the graph before reputting the stuffs
        self.ax.cla() 
        self.plot_FPGA_instruction(self.data_each_block_s[self.ind_block])
          
        # Set the title
        self.ax.set_title('FPGA data'+' Block %d'%self.ind_block
                          +'\nDouble click for getting time'
                          +'\nScroll to change block')
        #The following update the plot. 
        self.fig.canvas.draw_idle()  
        
            
            
    def plot_FPGA_instruction(self, data_array):
        """
        Extract the instruction of the FPGA, for each time interval. 
        Then plot what is happening at each time interval for each DIO
        
        Input:
            data_array
            array of int32 instruction sent to the FPGA
            
            nbChannel
            Total number of channel on the FPGA
            
            tickDuration
            Duration of a ticks (us) on the FPGA        
            
        """
        # get the converter
        self.conv = Converter()
        
        t0 = 0
        
        for int32 in data_array:
            #Plot a line for the state of each DIO
            
            #Get the ticks and state of each DIOs
            ticks, DIOstates = self.conv.int32_to_ticks_and_DIOs(int(int32))
            
            t1 = t0 + ticks
        
            #Now plot the resulting instruction, only for the DIO that we want to show
            for i, DIOstate in enumerate(DIOstates):
                if len(self.list_DIO_to_show)>0:
                    if i in self.list_DIO_to_show:
                        y = DIOstate+2*i
                        plt.plot([self.tickDuration*t0, self.tickDuration*t1], [y, y ],'.-', color='C%d'%i)                        
                else:
                    y = DIOstate+2*i
                    plt.plot([self.tickDuration*t0, self.tickDuration*t1], [y, y ],'.-', color='C%d'%i)
            #Shift the next initial time for the plots
            t0 = t1
            
        #Plot the DIO with text
        for i, DIOstate in enumerate(DIOstates):
            if len(self.list_DIO_to_show)>0:
                if i in self.list_DIO_to_show:
                    y = 2*i
                    plt.text(0, y, 'DIO %d'%i)                       
            else:
                y = 2*i
                plt.text(0, y, 'DIO %d'%i)
            
        plt.xlabel('Time (us)')
        plt.yticks([])
        
        #Remove some line of the frame in the plot
        frame = plt.gca()
        frame.axes.spines['left'].set_visible(False)
        frame.axes.spines['right'].set_visible(False)
        frame.axes.spines['top'].set_visible(False)  
        
        return

        

if __name__=="__main__":
    _debug_enabled = True
    # Convert something
    # Create a sequence
#    from pulses import CoolSequence, GUIPulsePattern
#    seq = CoolSequence(model='read2').get_sequence()
#    GUIPulsePattern(seq)
    # Test a pulse sequence
    import pulses as pls
    laser = pls.ChannelPulses(channel=1, name='Laser cool')
    laser.add_pulses([0, 10])
    laser.add_pulses([20, 30])
    laser.add_pulses([35, 38])

    trigger = pls.ChannelPulses(channel=5, name='Trigger')
    trigger.add_pulses([5, 7])
    trigger.add_pulses([40, 46.5])
    
    block = pls.PulsePatternBlock('Blocky')
    block.add_channelEvents([laser, trigger])
    
    seq = pls.Sequence('Cool seq')
    seq.add_block(block)
    
    pls.GUIPulsePattern(seq)
    
    
    
    rep = 7
    # Convert it
    self = Converter()
    data_array = self.sequence_to_FPGA(seq, rep)
    
    # Get the data array
    length_data_block_s = self.get_length_data_block_s()
    repetition = self.get_repetition()
    gui = GUIFPGAInstruction(data_array, repetition, length_data_block_s)


















