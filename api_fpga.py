# -*- coding: utf-8 -*-
"""
Created on Mon Apr 13 10:19:28 2020

API for controlling the fpga


@author: Michael
"""

from nifpga.session import Session
import numpy as np

import traceback
_p = traceback.print_last #Very usefull command to use for getting the last-not-printed error


_debug_enabled                = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))

        
class FPGA_api():
    """
    Api for the fpga. 
    
    Typical step for running the fpga:
        Open session, than calle the relevant method. 
        TODO:
            Explain Wrtie ouptut anfd run_pulse. Which is the best ? 
        
    """
    
    def __init__(self,bitfile_path, resource_num):
        """
        Input:
            bitfile_path
            Bitfile path (absolute) on which we work
            
            resource_num
            Ressourve numberMust be a string
            Example: 'RIO0'
            
        """
        _debug('FPGA_api:__init__')
        _debug('We can see through others only when we can see through ourselves. – Bruce Lee')
        
        self.bitfile_path = bitfile_path
        self.resource_num = resource_num
        
        self.list_DIO_states = np.zeros(16) # List of the steady state of the DIOs
        self.list_AO_values_set  = np.zeros(8) # List of the volateg set on the AO
        self.data = np.array([1], dtype='int32') # Initial data array
        
        # Magic number for converting voltage into bits for the AOs
        self.bit_per_volt = 3276.8 
        
        
    def open_session(self):
        """
        Open a session nifpga
        """
        _debug('FPGA_api:open_session')
        
        self._fpga = Session(bitfile=self.bitfile_path, resource=self.resource_num)
        
        # Reset running fpga
        self._fpga.registers
        self._fpga.reset()
        
        # Print status
        _debug("Status %s" % self._fpga.fpga_vi_state)
        # Name References to registers and fifos
        self.start   = self._fpga.registers['Start FPGA 1']
        self.wait    = self._fpga.registers['Wait after AO set (us)']
        self.counting_mode   = self._fpga.registers['Counting Mode']
        self.h_to_t  = self._fpga.registers['H toT Size']
        self.th_fifo = self._fpga.fifos['Target to Host DMA']
        self.ht_fifo = self._fpga.fifos['Host to Target DMA']   
    
        # Start the fpga vi
        self._fpga.run()
        
        # Prepare dummy AOs. DIOs and wait_time
        self.prepare_AOs([0], [0])
        self.prepare_DIOs([1], [0])
        self.prepare_wait_time(1)
        
        _debug(self._fpga.registers.keys())
        
       
    def close_session(self):
        """
        Close a session nifpga
        """
        _debug('FPGA_api:close_session')
        
        try:
            self._fpga.reset()
            self._fpga.close()
        except:
            print("Could not close fpga device")
#            raise
            return -1
        return 0
    
    def print_registers(self):
        """
        Print the list of registers. 
        That should be useful for investigating what is available. 
        """
        print(self._fpga.registers.keys())
    
    def v_to_bits(self,voltage):
        """
        COpy the previous function for now. 
        """
        _debug('FPGA_api: v_to_bits')
        
        assert np.abs(voltage) <= 10, "Voltage amplitude too high."
        #TODO: I think there's an off by one error here for negative values or
        # something like that, due to two's compliments bit representation.
        return int(round(voltage * self.bit_per_volt))   
    
    def prepare_AOs(self, AO_list, voltage_list):
        """
        Prepare the AOs for a specific voltage. 
        Note that the will be set after that the fpga get start. 
        
        AO_list:
            List of int for specifying which AOs to prepare. 
        voltage_list:
            List of voltages corresponding the AOs_list. 
        """
        _debug('FPGA_api: prepare_AOs')
        
        if not(len( AO_list) == len(voltage_list)):
            print('ERROR: The list of AOs do not match the list of voltage')
            return -1

        # The following magic line record the AO to the corresponding state
        self.list_AO_values_set[AO_list] = voltage_list
        #TODO remove the following. It is equivalent to the previous command. 
#        for i in range(AO_list):
#            self.list_AO_values[i] = voltage_list[i]
        
        for i in range(len(AO_list)):
            AO = AO_list[i]
            bits = self.v_to_bits(voltage_list[i])
            self._fpga.registers['AO%d'%AO].write(bits)

    def prepare_DIOs(self, DIO_list, state_list):
        """
        Prepare the DIOs to a specific state
        Note that they will be set after that the fpga get start. 
        Note also that DIOs which are not specified remain to the same state
        that they actuallly are (thanks to the magic of bits)
        
        DIO_list :
            List of DIOs (int) that we want to specify the state. 
        state_list:
            State of the corresponding DIOs (1--> ON; 0--> OFF)
            
        """
        _debug('FPGA_api: prepare_DIOs')
        
        # The following magic line sets the DIOs to the corresponding state
        self.list_DIO_states[DIO_list] = state_list
        
        # Get the corresponding data array
        data = 0
        for i in range(16, 32):
            #Each DIO state is either 0 or 1. So we write the next 16 bit in binary. 
            data += self.list_DIO_states[i-16]*2**i 
        
        self.data = np.array([data], dtype='int32') # Data to write to fpga
        
        # Configuring FIFO sizes
        ht_size = self.ht_fifo.configure(len(self.data)) # Attempt to set host->target size
        _debug('HT Size: %d' % ht_size) # Get returned, acutal size
        self.h_to_t.write(ht_size) # Let FPGA know the real size
        self.th_fifo.configure(ht_size) # Set target->host size with true size
        
        # Stop FIFOs
        self.ht_fifo.stop()
        self.th_fifo.stop()
        
        _debug('ht_fifo datatype: ', self.ht_fifo.datatype)    
                
    def prepare_wait_time(self, wait_time_us):
        """
        Set the wait time after the AOs are set. 
        
        wait_time_us:
            Wait time in us
        """
        _debug('FPGA_api: prepare_wait_time')
        
        # Convert into int the value if it is not already an int
        if not( type(wait_time_us) == int):
            self.wait.write( int(wait_time_us)) 
        else:
            self.wait.write(wait_time_us)
            
        
        
    def set_counting_mode(self, boolean):
        """
        Set the counting mode. 
        
        boolean: 
            True or False
            If True, the mode will count at each tick (CET = Count Each Tick)
            If False, it will count for the whole ON time of DIO1
        """
        _debug('FPGA_api: set_counting_mode')
        self.counting_mode.write(boolean)
        
        
    def write_output(self):
        """
        WARNING: 
            Never call this method alone if you are not certaint that the 
            pulse sequence willn not fill up the fifo. If you just want to set the
            DIO and AO value, you still need to run the whole pulse sequence. I put 
            this warning because I got serious issues with the fifo and the counts
            byt just writing the output !
        
        Write the AOs and the DIOs in the fpga. 
        The order of what gonna happend can be found in the Labview VI
        “FPGA FULL V2.vi”
        It first sets the AOs. Then it waits. Then it applies the pulse sequence. 
        Then it reads AI1. 
        
        """
        _debug('FPGA_api: write_output')
         # Set to false to halt counting/looping
        self.start.write(False)
        # Write data to FIFOs, automatically starts it
        self.ht_fifo.write(self.data, timeout_ms=5000)
        # Trigger fpga start
        self.start.write(True)        

    def read_register_AO(AO):
        """
        DANGEROUS METHOD which read the value of the AO on the register. 
        It is dangerous because I noticed that it changes the behavior of the 
        fifo. That was a source of important issue when I was optimizing during
        a pulse sequence. During the optimization, we were updating the value
        of the AO in the GUI. This was done by reading the register directly. 
        When we were coming back to the pulse sequence, there was element 
        remaingin in the fifo and the count array was not matching the 
        expectation from the pulse sequence. 
        
        """
        _debug('FPGA_api: read_register_AO')
        
        bits = self._fpga.registers['AO%d'%AO].read()
        return bits/self.bit_per_volt        

    def read_AI1(self):
        """
        Read the value of AI1. 
        The FPGA can only read AI1, this is why AI1 is already specified. 
        
        """    
        _debug('FPGA_api: read_AI1')
        self.ai = self._fpga.registers['AI1']
        return self.ai.read()

    def get_A1_voltage(self):
        """
        Read the A1 and return the corresponding voltage. 
        """
        _debug('FPGA_api: get_A1_voltage')
        
        reading = self.read_AI1()
        return reading/self.bit_per_volt
        
    
    def get_counts(self):
        """
        Return the whole count array, in the form of numpy array
        """
        _debug('FPGA_api: get_counts')
        return np.array(self.counts) 

    def get_DIO_states(self):
        """
        Return the DIO state 
        """
        _debug('FPGA_api: get_DIO_states')
        return self.list_DIO_states
    
    def get_AO_voltage(self, AO):
        """
        Get the voltage that a AO outputs.
        
        AO:
            (Int) Number for the AO to read. 
        """
        _debug('FPGA_api: get_AO_voltage')
#        self.AO_returned_value = self.list_AO_values[int(AO)]
#        return self.AO_returned_value
#        return float(self.list_AO_values[int(AO)])
#        return 2.5 # For testing
#        xs = np.linspace(-5, 8, 8)
#        return xs[int(AO)]
#        self.xs = np.linspace(-5, 8, 8)
#        return self.xs[int(AO)]   
        bits = self._fpga.registers['AO%d'%AO].read()
        volt = bits/self.bit_per_volt    
        return  volt
    
    def get_wait_time_us(self):
        """
        Return the waiting time
        """
        _debug('FPGA_api: get_wait_time_us')
        return self.wait.read()
    
    def get_data_array(self):
        """
        Return the data array that the fpga has. 
        """
        _debug('FPGA_api: get_data_array')
        return self.data
    
    def configure_fifo(self):
        """
        Configutre the fifo for the data array
        """
        _debug('FPGA_api: configure_fifo')
        
        ht_size = self.ht_fifo.configure(len(self.data)) # Attempt to set host->target size
        _debug('HT Size: %d' % ht_size) # Get returned, acutal size
        self.h_to_t.write(ht_size) # Let FPGA know the real size
        self.th_fifo.configure(ht_size) # Set target->host size with true size
        
        # Stop FIFOs
        self.ht_fifo.stop()
        self.th_fifo.stop()        
    
    def prepare_pulse(self, data_array, is_zero_ending=True, list_DIO_state=[] ):
        """
        Prepare the data array for the pulse pattern in the fpga. 
        
        Input:
            data_array
            list of FPGA instruction (list of int32)        
            
        is_zero_ending:
            If ture, append a ticks at the beggining and at the end where all
            DIOs are zeros. 
            
        list_DIO_state:
            If the lenght is 16, it's gonna record the DIO states to be this list. 
            That is useful for keeping track of which state are on and off when 
            the object is shared between other objects (like gui). 
            Otherwise it can be ignored.
        """
        _debug('FPGA_api: prepare_pulse')
        
        if is_zero_ending:
            # Need to add zeros at the beggining and at the end for the caprice of FPGA for pulse sequences
            d = np.concatenate(([1], data_array,[1])) 
            self.data = np.array(d, dtype='int32') # Data to write to fpga
        else:
            self.data = np.array(data_array, dtype='int32') # Data to write to fpga
            
        if len(list_DIO_state)==16:
            self.list_DIO_states = list_DIO_state
        
        # Configuring FIFO sizes
        self.configure_fifo()
        
        _debug('ht_fifo datatype: ', self.ht_fifo.datatype)      
        
      
    def lets_go_FPGA(self):
        """
        Ultimate function for running the FPGA. 
        It triggers the write output and read all fifo (ie counts) that the FPGA
        will produce. 
        
        For the write output, see the method "write_output. This is the 
        definition of write_output:
            Write the AOs and the DIOs in the fpga. 
            The order of what gonna happend can be found in the Labview VI
            “FPGA FULL V2.vi”
            It first sets the AOs. Then it waits. Then it applies the pulse sequence. 
            Then it reads AI1.          
            
        After that, very important, it reads all the element in the fifo that 
        the pulse sequence generates. This is the counts, when DIO1 is ON in 
        the pulse sequence. 
        
        You will notice that, for now, this function is just calling run_pulse()
        THis is because run_pulse() is doing everything. I decided to create 
        "lets_go_FPGA" in order to clarify some piece of code that as very simple 
        pulse sequence and the FPGA is called just for settings some DIOs and AOs 
        values.Since the name "run_pulse" is not well appropriate in these case,
        I create this redundant method for avoiding to rename all the other call
        to "run_pulse".
        
        """
        _debug('FPGA_api: lets_go_FPGA')
        # Yes. It's that simpler. 
        self.run_pulse()
        
        
    def run_pulse(self):
        """
        Start the FPGA for when there is a pulse sequence. 
        It gonna monitor the counts. 
        
        Mimic what is done in the vi "Host Writing to FPGA.vi"
        
        """
        _debug('FPGA_api: run_pulse')
        
        # Mimic what is done in the vi "Host Writing to FPGA.vi"
        
        self.th_fifo.stop()
        self.ht_fifo.stop()
        
        self.write_output()
        
        
        self.counts = [] #This gonna store the counts
#        # Note the number of elements in the fifo
#        num_elems = self.th_fifo.read(0).elements_remaining #The argument "0" ensures that nothing is read and erased
#        
        # Query until there is no more reading to do. 
        condition = True
        while condition==True:
            condition1 =  self.start.read()  # Check at the beggining if the 
            # Note the number of elements in the fifo
            num_elems = self.th_fifo.read(0).elements_remaining #The argument "0" ensures that nothing is read and erased            
#            _debug('start.read = ', self.start.read())
#            _debug("Element remaing: ", num_elems)
            # Read the elements remaining and store them into counts 
            count_array = self.th_fifo.read(num_elems).data # It output an array containing each count
            self.counts.extend( count_array ) # This adds each element of the input array
            # Update the while loop condition
            condition2 = num_elems>0
            condition = condition1 or condition2

#        print('start.read = ', self.start.read())
#        print("Counts = %s" % self.counts)
#        print("Element remaing: ", num_elems)        
        _debug('start.read = ', self.start.read())
        _debug("Counts = %s" % self.counts)
        _debug("Element remaing: ", num_elems)
        if len(self.counts)>0: 
            # Get the mean only if the array is not empty.
            _debug("Mean counts = ", np.mean(self.counts))
                     
    def run_pulse_loop(self, data_array, N_loopFPGA):
        """
        Loop over the fpga instructions. This is a example of what can be done 
        to perform measurement
        
        Input:
            data_array
            list of FPGA instruction (list of int32)
            
            N_loopFPGA
            Number of time to repeat the data_array        
        """
        _debug('FPGA_api: run_pulse_loop')
        
        self.prepare_pulse(data_array)
        
        for i in range(N_loopFPGA):
            _debug()
            _debug('FPGA loop ', i+1, ' over ', N_loopFPGA)
            self.run_instruction()
                
class FPGA_fake_api():
    """
    Fake api for the fpga. 
    
    It has the same method has FPGA_api, but without connecting to a real FPGA. 
    This is for testing codes without a real fpga ;) 
    
    """
    
    def __init__(self,bitfile_path, resource_num):
        """
        Input:
            bitfile_path
            Bitfile path (absolute) on which we work
            
            resource_num
            Ressourve numberMust be a string
            Example: 'RIO0'
            
        """
        _debug('FPGA_fake_api:__init__')
        _debug('The secret of getting ahead is getting started. – Mark Twain.')
        
        self.bitfile_path = bitfile_path
        self.resource_num = resource_num
        
        self.list_DIO_states = np.zeros(16) # List of the steady state of the DIOs
        self.list_AO_states = np.zeros(8) # List of AOs for faking the AOs
        self.data = np.array([1], dtype='int32') # Initial data array
        
        # Magic number for converting voltage into bits for the AOs
        self.bit_per_volt = 3276.8 
        
        
    def open_session(self):
        """
        Open a session nifpga
        """
        _debug('FPGA_fake_api:open_session')
        
        
        # Prepare dummy AOs. DIOs and wait_time
        
        self.prepare_AOs([0], [0])
        self.prepare_DIOs([1], [0])
        self.prepare_wait_time(1)
        
       
    def close_session(self):
        """
        Close a session nifpga
        """
        _debug('FPGA_fake_api:close_session')
        
        return
    
    def v_to_bits(self,voltage):
        """
        COpy the previous function for now. 
        """
        _debug('FPGA_fake_api: v_to_bits')
        
        assert np.abs(voltage) <= 10, "Voltage amplitude too high."
        #TODO: I think there's an off by one error here for negative values or
        # something like that, due to two's compliments bit representation.
        return int(round(voltage * self.bit_per_volt))   
    
    def prepare_AOs(self, AO_list, voltage_list):
        """
        Prepare the AOs for a specific voltage. 
        Note that the will be set after that the fpga get start. 
        
        AO_list:
            List of int for specifying which AOs to prepare. 
        voltage_list:
            List of voltages corresponding the AOs_list. 
        """
        _debug('FPGA_api: prepare_AOs')
        
        if not(len( AO_list) == len(voltage_list)):
            print('ERROR: The list of AOs do not match the list of voltage')
            return -1
        self.list_AO_states[AO_list] = voltage_list
        
        
    def prepare_DIOs(self, DIO_list, state_list):
        """
        Prepare the DIOs to a specific state
        Note that they will be set after that the fpga get start. 
        Note also that DIOs which are not specified remain to the same state
        that they actuallly are (thanks to the magic of bits)
        
        DIO_list :
            List of DIOs (int) that we want to specify the state. 
        state_list:
            State of the corresponding DIOs (1--> ON; 0--> OFF)
            
        """
        _debug('FPGA_fake_api: prepare_DIOs')
        
        # The following magic line sets the DIOs to the corresponding state
        self.list_DIO_states[DIO_list] = state_list
        
        # Get the corresponding data array
        data = 0
        for i in range(16, 32):
            #Each DIO state is either 0 or 1. So we write the next 16 bit in binary. 
            data += self.list_DIO_states[i-16]*2**i 
        
        self.data = np.array([data], dtype='int32') # Data to write to fpga
        
           
                
    def prepare_wait_time(self, wait_time_us):
        """
        Set the wait time after the AOs are set. 
        
        wait_time_us:
            Wait time in us
        """
        _debug('FPGA_fake_api: prepare_wait_time')
        self.wait_time_us = wait_time_us

    def set_counting_mode(self, boolean):
        """
        Set the counting mode. 
        
        boolean: 
            True or False
            If True, the mode will count at each tick (CET = Count Each Tick)
            If False, it will count for the whole ON time of DIO1
        """
        _debug('FPGA_api: set_counting_mode')
        self.counting_mode = boolean
        
    def write_output(self):
        """
        Write the AOs and the DIOs in the fpga. 
        The order of what gonna happend can be found in the Labview VI
        “FPGA FULL V2.vi”
        It first set the AOs. Then it waits. Then it apply the pulse sequence. 
        Then it reads AI1. 
        
        """
        _debug('FPGA_fake_api: write_output')
        return 

    def read_AI1(self):
        """
        Read the value of AI1. 
        The FPGA can only read AI1, this is why AI1 is already specified. 
        
        """    
        _debug('FPGA_fake_api: read_AI1')
        
        return np.random.poisson(100)/100

    def get_A1_voltage(self):
        """
        Read the A1 and return the corresponding voltage. 
        """
        _debug('FPGA_fake_api: get_A1_voltage')
        
        return np.random.poisson(2000)/1000
        
    
    def get_counts(self):
        """
        Return the whole count array, in the form of numpy array
        """
        _debug('FPGA_fake_api: get_counts')
        return np.array(self.counts) 

    def get_DIO_states(self):
        """
        Return the DIO state 
        """
        _debug('FPGA_fake_api: get_DIO_states')
        return self.list_DIO_states
    
    def get_AO_voltage(self, AO):
        """
        Get the voltage that a AO outputs.
        
        AO:
            (Int) Number for the AO to read. 
        """
        _debug('FPGA_fake_api: get_AO_voltage')
        
        return AO*np.random(1000)/1000
    
    def get_wait_time_us(self):
        """
        Return the waiting time
        """
        _debug('FPGA_fake_api: get_wait_time_us')
        
        return self.wait_time_us
    
    def get_data_array(self):
        """
        Return the data array that the fpga has. 
        """
        _debug('FPGA_fake_api: get_data_array')
        return self.data
    
    def prepare_pulse(self, data_array, is_zero_ending=True, list_DIO_state=[] ):
        """
        Prepare the data array for the pulse pattern in the fpga. 
        
        Input:
            data_array
            list of FPGA instruction (list of int32)        
            
        is_zero_ending:
            If ture, append a ticks at the beggining and at the end where all
            DIOs are zeros. 
            
        list_DIO_state:
            If the lenght is 16, it's gonna record the DIO states to be this list. 
            That is useful for keeping track of which state are on and off when 
            the object is shared between other objects (like gui)
        """
        _debug('FPGA_fake_api: prepare_pulse')
        
        if is_zero_ending:
            # Need to add zeros at the beggining and at the end for the caprice of FPGA for pulse sequences
            d = np.concatenate(([1], data_array,[1])) 
            self.data = np.array(d, dtype='int32') # Data to write to fpga
        else:
            self.data = np.array(data_array, dtype='int32') # Data to write to fpga
            
        if len(list_DIO_state)==16:
            self.list_DIO_states = list_DIO_state 
        
      
    def run_pulse(self):
        """
        Start the FPGA for when there is a pulse sequence. 
        It gonna monitor the counts. 
        
        Mimic what is done in the vi "Host Writing to FPGA.vi"
        
        """
        _debug('FPGA_fake_api: run_pulse')
        
        
        self.counts = [[np.random.poisson(50)/50]] 
        if len(self.counts)>0: 
            # Get the mean only if the array is not empty.
            _debug("Mean counts = ", np.mean(self.counts))
                     
    def run_pulse_loop(self, data_array, N_loopFPGA):
        """
        Loop over the fpga instructions. This is a example of what can be done 
        to perform measurement
        
        Input:
            data_array
            list of FPGA instruction (list of int32)
            
            N_loopFPGA
            Number of time to repeat the data_array        
        """
        _debug('FPGA_fake_api: run_pulse_loop')
        
        self.prepare_pulse(data_array)
        
        for i in range(N_loopFPGA):
            _debug()
            _debug('FPGA loop ', i+1, ' over ', N_loopFPGA)
            self.run_instruction()        
                
 
from converter import Converter               
class ProcessFPGACounts():
    """
    Various, convenient, methods for processing the array of counts that the fpga outputs
    """ 
    def __init__(self, counts):
        """
        Take the data array as input ?
        
        counts:
            Data structure for the counts that FPGA_api gives. 
            (The method FPGA_api.get_counts returns the right structure)
        """             
        self.counts = counts
        
    def unboundle_CET_int32(self, int32):
        """
        Unboundle the counts from a single int 32 created by count each tick 
        mode (CET).
        int32: 
            Number (a int32) that we will unboundle. 
        """
        #Each bit of the int32 correspond to one tick.
        # Get the count (0 or 1) from each bit
        array_binary = Converter().binary(int32) # Array of lenght 32. Each element correspond to the count for the corresponding tick
        # The lenght might be lower than 32. Therefore let's create the lenght 32 array
        counts = np.zeros(32)
        for i in range(32):
            if i < len(array_binary):
                counts[i] = array_binary[i]
            else:
                counts[i] = 0
            
        return counts

    def get_sum_count_per_repetition_CET_mode(self, repetition):
        """
        FOR CET (Count Each Tick) MODE
        Split the array of counts into arrays of counts for each repetition. 
        Interpretere (unbundle) the element of each array to get the counts
        for each ticks. 
        
        Return the sum of the resulting arrays. 
        
        repetition:
            Number of time that the sequence is repeated in the FPGA instruction. 
        """     
        
        # Get the arrays for each repetition
        self.counts_each_seq = np.split( self.counts, repetition)
        
        # Go trough each array
        for i, count_to_unbundle in enumerate(self.counts_each_seq):
            self.count_single_rep = [] # Array of count for a single repetition
            # Unbundle each element and append them
            for int32 in count_to_unbundle:
                # Get the count for the 32ticks
                array_counts_32ticks = self.unboundle_CET_int32(int32)
                self.count_single_rep = np.concatenate((self.count_single_rep, 
                                                       array_counts_32ticks))
            if not(i == 0):               
                # Add the counts of each repetition together
                self.counts_sum_over_rep = self.counts_sum_over_rep + self.count_single_rep
            else:
                # Initialise the total array with the first computed.
                self.counts_sum_over_rep = self.count_single_rep
                            
        # Return the sum over each repetition 
        return self.counts_sum_over_rep
                
                
        
        
    def get_sum_count_per_repetition(self, repetition):
        """
        Split the array of counts into arrays of counts for each repetition. 
        Return the sum of the resulting arrays. 
        
        repetition:
            Number of time that the sequence is repeated in the FPGA instruction. 
        """
        self.counts_each_seq = np.split( self.counts, repetition)
        return np.sum(self.counts_each_seq, axis=0)              
    
    def get_sum_count_per_block(self, repetition, nb_block):
        """
        Get the arrays for the total counts at each block
        
        Return: 
            An array of subarray. Each subarray is the counts for one block. 
        """
        # Get the total count array of all the repetition 
        self.sum_count_per_rep = self.get_sum_count_per_repetition(repetition)
        # Split counts of the sequence into blocks
        return np.split(self.sum_count_per_rep, nb_block) 
    
    def get_count_per_readout_vs_block(self, repetition, nb_block):
        """
        Restructure the array of counts, more convenient for plotting. 
        Get the count for each readout in each block. 
        
        counts_per_block:
            Same structure as the output of the method get_sum_count_per_block
            
        return:
            block_indices:
                array of iteger [0,1,2,...,N-1], where N is the number of block. 
            counts:
                counts[i] is an array conresponding to the i'th count VS blocks
                
        """
        # We want that the array i correspond to the i'th count VS blocks
        y = self.get_sum_count_per_block(repetition, nb_block)
        counts = np.zeros([len(y[0]), len(y)])
        block_indices = []
        
        for j, cs_block in enumerate(y):
            block_indices.append(j)
            for i, cs in enumerate(cs_block):
                counts[i][j] = cs        
                
        return block_indices, counts
    
    
    
              
import matplotlib.pyplot as plt
def plot_counts_vs_block(counts, repetition, nb_block):
    """
    Input:
        counts: FPGA count array
    """
    process = ProcessFPGACounts(counts)
    block_indices, counts = process.get_count_per_readout_vs_block(repetition, nb_block)
    
    # Now we can plot the counts VS blocks
    fig, ax = plt.subplots(tight_layout=True)
    
    for i in range(len(counts)):
        plt.plot(block_indices, counts[i], '.-', label='Readout %d'%i)
    plt.legend()
    plt.xlabel('Block index')
    plt.ylabel('Counts')
    if len(counts)==0:
        plt.title('No counts !')
    else:
        plt.title('Counts VS blocks')
        
    return fig, ax
    
        
if __name__=="__main__":
    _debug_enabled                = True

    # Send that to the FPGA
    bitfile_path = ("X:\DiamondCloud\Magnetometry\Acquisition\FPGA\Magnetometry Control\FPGA Bitfiles"
                    "\Pulsepattern(bet_FPGATarget_FPGAFULLV2_WZPA4vla3fk.lvbitx")
    resource_num = "RIO0"     
    
    self = FPGA_api(bitfile_path, resource_num) # Create the api
    # Open it
    self.open_session()

    self.prepare_AOs([4,5,0, 2], [-2.4, 0.5, -6.3, 7.8])
    self.prepare_DIOs([2,3,5,6], [1,0,1,1])
    self.write_output()
    print('AI1 = %f V'%self.get_A1_voltage())
    print('AO5 = %f V'%self.get_AO_voltage(5))
    print('AO2 = %f V'%self.get_AO_voltage(2))
    
    import time
    time.sleep(2)
    self.prepare_AOs([2, 5], [-4.5, 8.5])
    self.prepare_DIOs([2,3,5,6], [1,1,1,1])
    self.write_output()    
    print('AO5 = %f V'%self.get_AO_voltage(5))
    print('AO2 = %f V'%self.get_AO_voltage(2))
    
    
    
    
    
    
    
    
    
    
    