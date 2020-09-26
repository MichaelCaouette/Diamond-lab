import numpy       as _n
import spinmob     as _s
import spinmob.egg as _egg
import mcphysics   as _mp
import time        as _t

_g = _egg.gui

import traceback as _traceback
_p = _traceback.print_last

# Debug stuff.
_mp.visa_tools._debug_enabled = False
_debug_enabled                = False

def _debug(*a):
    if _debug_enabled: 
        s = []
        for x in a: s.append(str(x))
        print(', '.join(s))
x = []


class signal_generator_api(_mp.visa_tools.visa_api_base):
    """
    General signal generator API base. This will connect and then, based on
    the model number, inherit all the commands from one of the specific model
    classes.
    """
    def __init__(self, name='SMA100B', pyvisa_py=False, simulation=False, timeout=100e3, write_sleep=0.1, **kwargs):
        """
        Visa-based connection to the Anapico signal generator.
        """
        _debug('signal_generator_api.__init__()', pyvisa_py, simulation, timeout, write_sleep)
        
        # Run the core setup.
        _mp.visa_tools.visa_api_base.__init__(self, name, pyvisa_py, simulation, timeout=timeout, write_sleep=write_sleep)
        
        # Inherit the functionality based on the idn
        if self.idn.split(',')[0] in ['AnaPico AG']: 
            _debug('signal_generator_api.__init__() I choose you anapico')
            self._api = anapico_api()
        elif 'SMA100B' in self.idn:
            _debug('signal_generator_api.__init__() I choose you sma100b')
            self._api = sma100b_api()
        elif 'SMB100A' in self.idn:
            _debug('signal_generator_api.__init__() I choose you smb100a')
            self._api = smb100a_api()  
        elif 'SMIQ03B' in self.idn:
            _debug('signal_generator_api.__init__() I choose you simq03b')
            self._api = simq03b_api()
            
        else:
            print("Unknown Signal Generator: "+str(self.idn))
            self._api = sma100b_api() # Just use SMA100B as the default

        # Make sure the class has everything it needs.
        self._api.instrument       = self.instrument
        self._api.idn              = self.idn
        self._api.resource_manager = self.resource_manager
        self._api._write_sleep     = self._write_sleep


    def reset(self):
        """
        Resets the device to factory defaults (RF off).
        """
        return self._api.reset()
    
    def send_list(self, frequencies=[1e9,2e9,3e9,4e9], powers=[-10,-5,-2,0], dwell=0, delay=0):
        """
        Sends the specified list values.
        
        Parameters
        ----------
        frequencies=[1e9,2e9,3e9,4e9]
            List of frequency values (Hz) to touch.
        
        powers=[0,0,0,0]
            List of power values (dBm) to touch.
        
        dwell=0
            In immediate mode for the list sweep, this is how long the generator
            will dwell on a given step.
        
        delay=0
            How long to delay after triggering the next step.
        """
        return self._api.send_list(frequencies, powers, dwell, delay)

    def set_mode(self, mode='List'):
        """
        Sets the generator to be in list or fixed mode.
        
        Paramters
        ---------
        mode='List'
            Set to 'Fixed' for fixed mode.
        """
        return self._api.set_mode(mode)
    
    def get_mode(self):
        """
        Returns 'Fixed' or 'List' depending on the device mode.
        """
        return self._api.get_mode()
    
    def set_list_index(self, n=0):
        """
        Sets the list index, changing the appropriate frequency and power on the 
        output.
        
        Parameters
        ----------
        n=0
            0-referenced index.
        """
        return self._api.set_list_index(n)
        
    def get_list_index(self):
        """
        Gets the current list index.
        """
        return self._api.get_list_index()
    
    def set_output(self, on=False):
        """
        Turns the output on or off.
        """
        return self._api.set_output(on)

    def get_output(self):
        """
        Returns 0 or 1 based on the RF output state.
        """
        return self._api.get_output()

    def set_frequency(self, f=1e9):
        """
        Sets the frequency to f (Hz).
        
        Parameters
        ----------
        f=1e9
            Frequency (Hz)
        """
        return self._api.set_frequency(f)
        
    def get_frequency(self):
        """ 
        Returns the current frequency (Hz).
        """
        return self._api.get_frequency()
    
    def set_power(self, dbm=-30):
        """
        Sets the output power to the specified value (dBm).
        """
        return self._api.set_power(dbm)
    
    def get_power(self):
        """
        Returns the current power level (dBm).
        """
        return self._api.get_power()
    
    def get_list_powers(self):
        """
        Gets the list of powers.
        """
        return self._api.get_list_powers()
        
    def get_list_frequencies(self):
        """
        Gets the list of frequencies. In Hz !
        """
        return self._api.get_list_frequencies()
        
    def get_list_length(self):
        """
        Returns the size of the list sweep.
        """
        return self._api.get_list_length()

    def prepare_for_ESR(self):
        """
        Prepare the instrument for ESR measurement.
        Set the trigger to be external, pulse modulation, etc. 
        """    
        return self._api.prepare_for_ESR()

    def prepare_for_Rabi(self):
        """
        Prepare the signal generator for Rabi:
            Put in fixed mode, modulate the frequency, etc. 
        """
        return self._api.prepare_for_Rabi()
    

class sma100b_api(_mp.visa_tools.visa_api_base):    
    """
    API for SMA100B. This object just defines the functions to be used by the
    base class signal_generator_api.
    """
    def __init__(self): return
        
    def reset(self):
        """
        Resets the device to factory defaults (RF off).
        """
        _debug('api.reset()')
        self.write('*RST')
        self.query('*IDN?') # Pauses operation until fully reset?
    
    def send_list(self, frequencies=[1e9,2e9,3e9,4e9], powers=[-10,-5,-2,0], dwell=1000, delay=0):
        """
        Sends the specified list values.
        
        Parameters
        ----------
        frequencies=[1e9,2e9,3e9,4e9]
            List of frequency values (Hz) to touch.
        
        powers=[0,0,0,0]
            List of power values (dBm) to touch.
        
        dwell=0
            In immediate mode for the list sweep, this is how long the generator
            will dwell on a given step.
        
        delay=0
            How long to delay after triggering the next step.
        """
        _debug('api.send_list()')
        
        # Handle integers or lists for either frequencies or powers
        if not _s.fun.is_iterable(frequencies): frequencies = [frequencies]
        if not _s.fun.is_iterable(powers):      powers      = [powers]
        
        # Handle numpy arrays
        if not type(frequencies) == 'list': frequencies = list(frequencies)
        if not type(powers)      == 'list': powers      = list(powers)
        
        # Handle length-1 arrays:
        if len(frequencies) == 1: frequencies = frequencies*len(powers)
        if len(powers)      == 1: powers      = powers     *len(frequencies)
        
        # Poop if the lengths don't match
        if not len(frequencies) == len(powers): 
            print("ERROR: Lengths must match!")
            return
        
        #The mode switch to Fixed  when we write a power and dwell list. 
        #So I track the initial mode to put it back at the end. 
        initial_mode = self.get_mode()
        
        #First choose a list, otherwise SMA100B is mad
        #To know the available list, the query is 'SOUR1:LIST:CAT?'
        self.write('SOUR1:LIST:SEL "/var/user/list1.lsw"') 
         
        #Prepare the strings for the list command
        str_freq = 'SOUR1:LIST:FREQ ' + str(frequencies[0]) #String for the frequency list command
        str_pow = 'SOUR1:LIST:POW ' + str(powers[0]) #String for the power list command
        str_dwell = 'SOUR1:LIST:DWEL:LIST '+str(dwell) #String for the dwell list command
        for i in range(1,len(frequencies)):
            str_freq += ', ' + str(frequencies[i])
            str_pow += ', ' + str(powers[i])
            str_dwell += ', '+str(dwell)
        
        self.write(str_freq)
        self.write(str_pow)
        self.write(str_dwell)
        
        #Apparently the SMA change to Fixed mode after the power and the Dwell list is send... 
        #So I just switch back to the initial mode to make sure we end up in the same state. 
        self.set_mode(initial_mode)


    def set_mode(self, mode='List'):
        """
        Sets the generator to be in list or fixed mode.
        
        Paramters
        ---------
        mode='List'
            Set to 'Fixed' for fixed mode.
        """
    
        #If we choose list mode    
        if mode.lower() == 'list':
            #First choose a list if there was no, otherwise SMA100B is mad
            #To know the available list, the query is 'SOUR1:LIST:CAT?'
            self.write('SOUR1:LIST:SEL "/var/user/list1.lsw"') 
            
            self.write('OUTP1:STAT ON') #Somehow the SMA100B wants the RF to be ON for switching into list mode.
            self.write('SOUR1:LIST:MODE STEP') #Make Step mode in order to not automatically sweep all the frequencies
            self.write('SOURce1:FREQuency:MODE LIST')
        else:
            #CW and FIXed are synonyms for SMA100B
            self.write('SOURce1:FREQuency:MODE CW')
    
    def get_mode(self):
        """
        Returns 'Fixed' or 'List' depending on the device mode.
        """
        s = self.query('FREQ:MODE?')
        if s == None: return None
        
        s = s.strip()
        if   s == 'CW':  return 'Fixed'
        elif s == 'LIST': return 'List'
        else:
            print('ERROR: Unknown mode '+str(s))
            return
    
    def set_list_index(self, n=0):
        """
        Sets the list index, changing the appropriate frequency and power on the 
        output.
        
        Parameters
        ----------
        n=0
            0-referenced index.
        """
        #We have to be in step mode for being able to set the list index
        self.write('SOUR1:LIST:MODE STEP') #Have to be in STEP mode in order to select the index
        self.write('SOUR1:LIST:IND '+ str(int(n)) ) 
    
    def get_list_index(self):
        """
        Gets the current list index.
        """
        s = self.query('LIST:IND?')
        return int(s)
    
    def set_output(self, on=False):
        """
        Turns the output on or off.
        """
        #Note that, for SMA, switiching off the output set the automatically the mode to Fixed.... !!
        if on: self.write("OUTP1:STAT ON")
        else:  self.write("OUTP1:STAT OFF")
        

    def get_output(self):
        """
        Returns 0 or 1 based on the RF output state.
        """
        x = self.query('OUTP1:STAT?')
        if x == None: return None
        return int(x)

    def set_frequency(self, f=1e9):
        """
        Sets the frequency to f (Hz).
        
        Parameters
        ----------
        f=1e9
            Frequency (Hz)
        """
        self.write('SOUR:FREQ:CW '+str(f))
        
    def get_frequency(self):
        """ 
        Returns the current frequency (Hz).
        """
        x = self.query('SOUR:FREQ:CW?')
        if x == None: return None
        return float(x)
    
    def set_power(self, dbm=-30):
        """
        Sets the output power to the specified value (dBm).
        """
        self.write("SOURce1:POWer:POWer "+str(dbm))
    
    def get_power(self):
        """
        Returns the current power level (dBm).
        """
        x = self.query('SOURce1:POWer:POWer?')
        if x == None: return None
        return float(x)
    
    def get_list_powers(self):
        """
        Gets the list of powers.
        """
        s = self.query('SOUR1:LIST:POW?')
        if s == None: return None
        a = []
        n = 0
        for x in s.split(','):
            try:
                a.append(float(x.strip()))
            except:
                print('ERROR get_list_powers(): non-float in list ', n, x)
            n += 1
        return a
        
    def get_list_frequencies(self):
        """
        Gets the list of frequencies.
        """
        s = self.query('SOUR1:LIST:FREQ?')
        if s == None: return None
        a = []
        n = 0
        for x in s.split(','):
            try:
                a.append(float(x.strip()))
            except:
                print('ERROR get_list_frequencies(): non-float in list ', n, x)
            n += 1
        return a
        
    def get_list_length(self):
        """
        Returns the size of the list sweep.
        """
        s = self.query('SOUR1:LIST:FREQ:POIN?')
        if s == None: return None
        return int(s)

    def prepare_for_ESR(self):
        """
        Prepare the instrument for ESR measurement.
        Set the trigger to be external, pulse modulation, etc. 
        """    
        # Not implemented yet
        return 

    def prepare_for_Rabi(self):
        """
        Prepare the signal generator for Rabi:
            Put in fixed mode, modulate the frequency, etc. 
        """
        # Not implemented yet
        return 
    

class smb100a_api(_mp.visa_tools.visa_api_base):    
    """
    API for SMB100A. This object just defines the functions to be used by the
    base class signal_generator_api.
    """
    def __init__(self): return
        
    def reset(self):
        """
        Resets the device to factory defaults (RF off).
        """
        _debug('api.reset()')
        self.write('*RST')
        self.query('*IDN?') # Pauses operation until fully reset?
    
    def send_list(self, frequencies=[1e9,2e9,3e9,4e9], powers=[-10,-5,-2,0], dwell=1000, delay=0):
        """
        Sends the specified list values.
        
        Parameters
        ----------
        frequencies=[1e9,2e9,3e9,4e9]
            List of frequency values (Hz) to touch.
        
        powers=[0,0,0,0]
            List of power values (dBm) to touch.
        
        dwell=0
            In immediate mode for the list sweep, this is how long the generator
            will dwell on a given step.
        
        delay=0
            How long to delay after triggering the next step.
        """
        _debug('api.send_list()')
        
        # Handle integers or lists for either frequencies or powers
        if not _s.fun.is_iterable(frequencies): frequencies = [frequencies]
        if not _s.fun.is_iterable(powers):      powers      = [powers]
        
        # Handle numpy arrays
        if not type(frequencies) == 'list': frequencies = list(frequencies)
        if not type(powers)      == 'list': powers      = list(powers)
        
        # Handle length-1 arrays:
        if len(frequencies) == 1: frequencies = frequencies*len(powers)
        if len(powers)      == 1: powers      = powers     *len(frequencies)
        
        # Poop if the lengths don't match
        if not len(frequencies) == len(powers): 
            print("ERROR: Lengths must match!")
            return
        
        #The mode switch to Fixed  when we write a power and dwell list. 
        #So I track the initial mode to put it back at the end. 
        initial_mode = self.get_mode()
        
        #First choose a list, otherwise SMA100B is mad
        #To know the available list, the query is 'SOUR1:LIST:CAT?'
        self.write('SOUR1:LIST:SEL "/var/user/list1.lsw"') 
         
        #Prepare the strings for the list command
        str_freq = 'SOUR1:LIST:FREQ ' + str(frequencies[0]) #String for the frequency list command
        str_pow = 'SOUR1:LIST:POW ' + str(powers[0]) #String for the power list command
        str_dwell = 'SOUR1:LIST:DWEL:LIST '+str(dwell) #String for the dwell list command
        for i in range(1,len(frequencies)):
            str_freq += ', ' + str(frequencies[i])
            str_pow += ', ' + str(powers[i])
            str_dwell += ', '+str(dwell)
        
        self.write(str_freq)
        self.write(str_pow)
        self.write(str_dwell)
        
        #Apparently the SMA change to Fixed mode after the power and the Dwell list is send... 
        #So I just switch back to the initial mode to make sure we end up in the same state. 
        self.set_mode(initial_mode)


    def set_mode(self, mode='List'):
        """
        Sets the generator to be in list or fixed mode.
        
        Paramters
        ---------
        mode='List'
            Set to 'Fixed' for fixed mode.
        """
    
        #If we choose list mode    
        if mode.lower() == 'list':
            #First choose a list if there was no, otherwise SMA100B is mad
            #To know the available list, the query is 'SOUR1:LIST:CAT?'
            self.write('SOUR1:LIST:SEL "/var/user/list1.lsw"') 
            
            self.write('OUTP1:STAT ON') #Somehow the SMA100B wants the RF to be ON for switching into list mode.
            self.write('SOUR1:LIST:MODE STEP') #Make Step mode in order to not automatically sweep all the frequencies
            self.write('SOURce1:FREQuency:MODE LIST')
        else:
            #CW and FIXed are synonyms for SMA100B
            self.write('SOURce1:FREQuency:MODE CW')
    
    def get_mode(self):
        """
        Returns 'Fixed' or 'List' depending on the device mode.
        """
        s = self.query('FREQ:MODE?')
        if s == None: return None
        
        s = s.strip()
        if   s == 'CW':  return 'Fixed'
        elif s == 'LIST': return 'List'
        else:
            print('ERROR: Unknown mode '+str(s))
            return
    
    def set_list_index(self, n=0):
        """
        Sets the list index, changing the appropriate frequency and power on the 
        output.
        
        Parameters
        ----------
        n=0
            0-referenced index.
        """
        #We have to be in step mode for being able to set the list index
        self.write('SOUR1:LIST:MODE STEP') #Have to be in STEP mode in order to select the index
        self.write('SOUR1:LIST:IND '+ str(int(n)) ) 
    
    def get_list_index(self):
        """
        Gets the current list index.
        """
        s = self.query('LIST:IND?')
        return int(s)
    
    def set_output(self, on=False):
        """
        Turns the output on or off.
        """
        #Note that, for SMA, switiching off the output set the automatically the mode to Fixed.... !!
        if on: self.write("OUTP1:STAT ON")
        else:  self.write("OUTP1:STAT OFF")
        

    def get_output(self):
        """
        Returns 0 or 1 based on the RF output state.
        """
        x = self.query('OUTP1:STAT?')
        if x == None: return None
        return int(x)

    def set_frequency(self, f=1e9):
        """
        Sets the frequency to f (Hz).
        
        Parameters
        ----------
        f=1e9
            Frequency (Hz)
        """
        self.write('SOUR:FREQ:CW '+str(f))
        
    def get_frequency(self):
        """ 
        Returns the current frequency (Hz).
        """
        x = self.query('SOUR:FREQ:CW?')
        if x == None: return None
        return float(x)
    
    def set_power(self, dbm=-30):
        """
        Sets the output power to the specified value (dBm).
        """
        self.write("SOURce1:POWer:POWer "+str(dbm))
    
    def get_power(self):
        """
        Returns the current power level (dBm).
        """
        x = self.query('SOURce1:POWer:POWer?')
        if x == None: return None
        return float(x)
    
    def get_list_powers(self):
        """
        Gets the list of powers.
        """
        s = self.query('SOUR1:LIST:POW?')
        if s == None: return None
        a = []
        n = 0
        for x in s.split(','):
            try:
                a.append(float(x.strip()))
            except:
                print('ERROR get_list_powers(): non-float in list ', n, x)
            n += 1
        return a
        
    def get_list_frequencies(self):
        """
        Gets the list of frequencies.
        """
        s = self.query('SOUR1:LIST:FREQ?')
        if s == None: return None
        a = []
        n = 0
        for x in s.split(','):
            try:
                a.append(float(x.strip()))
            except:
                print('ERROR get_list_frequencies(): non-float in list ', n, x)
            n += 1
        return a
        
    def get_list_length(self):
        """
        Returns the size of the list sweep.
        """
        s = self.query('SOUR1:LIST:FREQ:POIN?')
        if s == None: return None
        return int(s)
    
    
class anapico_api(_mp.visa_tools.visa_api_base):
    """
    API for Anapico. This object just defines the functions to be used by the
    base class signal_generator_api.
    """
    def __init__(self): return
        
    def reset(self):
        """
        Resets the device to factory defaults (RF off).
        """
        _debug('api.reset()')
        self.write('*RST')
        self.query('*IDN?') # Pauses operation until fully reset?
    
    def send_list(self, frequencies=[1e9,2e9,3e9,4e9], powers=[-10,-5,-2,0], dwell=0, delay=0):
        """
        Sends the specified list values.
        
        Parameters
        ----------
        frequencies=[1e9,2e9,3e9,4e9]
            List of frequency values (Hz) to touch.
        
        powers=[0,0,0,0]
            List of power values (dBm) to touch.
        
        dwell=0
            In immediate mode for the list sweep, this is how long the generator
            will dwell on a given step.
        
        delay=0
            How long to delay after triggering the next step.
        """
        _debug('api.send_list()')
        
        # Handle integers or lists for either frequencies or powers
        if not _s.fun.is_iterable(frequencies): frequencies = [frequencies]
        if not _s.fun.is_iterable(powers):      powers      = [powers]
        
        # Handle numpy arrays
        if not type(frequencies) == 'list': frequencies = list(frequencies)
        if not type(powers)      == 'list': powers      = list(powers)
        
        # Handle length-1 arrays:
        if len(frequencies) == 1: frequencies = frequencies*len(powers)
        if len(powers)      == 1: powers      = powers     *len(frequencies)
        
        # Poop if the lengths don't match
        if not len(frequencies) == len(powers): 
            print("ERROR: Lengths must match!")
            return
        
        # The anapico, annoyingly, will only send a list if it's not in list mode
        original_mode = self.get_mode()
        if original_mode=='List': self.set_mode('Fixed')
        
        # Assemble the long-ass command
        command = "LIST:POW "        
        for p in powers: command += str(p)+","
        self.write(command)
      
        # Do the same for the frequencies
        command = "LIST:FREQ "
        for f in frequencies: command += str(f)+","          
        self.write(command)
            
        # Set dwell and delay
        self.write("LIST:DWEL " + str(dwell))
        self.write("LIST:DEL " + str(delay))
        
        # Set it back if we're supposed to
        if original_mode == 'List': self.set_mode('List')

    def set_mode(self, mode='List'):
        """
        Sets the generator to be in list or fixed mode.
        
        Paramters
        ---------
        mode='List'
            Set to 'Fixed' for fixed mode.
        """
        
        if mode.lower() == 'list':
            
            # Set sweep to manual mode    
            self.write("FREQ:MODE LIST")
            self.write("POW:MODE LIST")
            self.write("LIST:MODE MAN")

        # Fixed Mode
        else:
            # Set power and frequency to either fixed or list mode
            self.write("FREQ:MODE FIX")
            self.write("POW:MODE FIX")
            
        # Hack
        # Try to interrupt
        print('Bug workaround (long wait!)...')
        
        # Wait until it works
        failed = True
        n      = 0
        while failed:
            _t.sleep(0.25)
            try:   
                print('   TIMER-OUTER', self.query('*IDN?'))
                failed = False
            except: 
                n += 1
                print('Bug workaround: time out #'+str(n))
        print('Bug workaround: all done!')
    
    def get_mode(self):
        """
        Returns 'Fixed' or 'List' depending on the device mode.
        """
        s = self.query('FREQ:MODE?')
        if s == None: return None
        
        s = s.strip()
        if   s == 'FIX':  return 'Fixed'
        elif s == 'LIST': return 'List'
        else:
            print('ERROR: Unknown mode '+str(s))
            return
    
    def set_list_index(self, n=0):
        """
        Sets the list index, changing the appropriate frequency and power on the 
        output.
        
        Parameters
        ----------
        n=0
            0-referenced index.
        """
        self.write("LIST:MAN " + str(int(n+1)))
    
    def get_list_index(self):
        """
        Gets the current list index.
        """
        s = self.query('LIST:MAN?')
        if s == None: return None
        return int(s)-1
    
    def set_output(self, on=False):
        """
        Turns the output on or off.
        """
        if on: self.write("OUTP ON")
        else:  self.write("OUTP OFF")

    def get_output(self):
        """
        Returns 0 or 1 based on the RF output state.
        """
        x = self.query('OUTP?')
        if x == None: return None
        return int(x)

    def set_frequency(self, f=1e9):
        """
        Sets the frequency to f (Hz).
        
        Parameters
        ----------
        f=1e9
            Frequency (Hz)
        """
        self.write('FREQ '+str(f))
        
    def get_frequency(self):
        """ 
        Returns the current frequency (Hz).
        """
        x = self.query('FREQ?')
        if x == None: return None
        return float(x)
    
    def set_power(self, dbm=-30):
        """
        Sets the output power to the specified value (dBm).
        """
        self.write("POW "+str(dbm))
    
    def get_power(self):
        """
        Returns the current power level (dBm).
        """
        x = self.query('POW?')
        if x == None: return None
        return float(x)
    
    def get_list_powers(self):
        """
        Gets the list of powers.
        """
        s = self.query('LIST:POW?')
        if s == None: return None
        a = []
        n = 0
        for x in s.split(','):
            try:
                a.append(float(x.strip()))
            except:
                print('ERROR get_list_powers(): non-float in list ', n, x)
            n += 1
        return a
        
    def get_list_frequencies(self):
        """
        Gets the list of frequencies.
        """
        s = self.query('LIST:FREQ?')
        if s == None: return None
        a = []
        n = 0
        for x in s.split(','):
            try:
                a.append(float(x.strip()))
            except:
                print('ERROR get_list_frequencies(): non-float in list ', n, x)
            n += 1
        return a
        
    def get_list_length(self):
        """
        Returns the size of the list sweep.
        """
        s = self.query('LIST:FREQ:POIN?')
        if s == None: return None
        return int(s)
    
    def prepare_for_ESR(self):
        """
        Prepare the instrument for ESR measurement.
        Set the trigger to be external, pulse modulation, etc. 
        """
        _debug('Anapico: prepare ESR')
        # This is all for the ANAPICO to use the external trigger. 
        # BONUS for preparing the list with the external trigger. 
        print('Testing query: ', self.query('*IDN?'))
        print('Source for Trigger?: ', self.query('TRIG:SEQ:SOUR?'))
        self.write('TRIG:SEQ:SOUR EXT') # Set the external trigger to ext
        print('Source for Trigger?: ', self.query('TRIG:SEQ:SOUR?'))
        print('First frequency?: ', self.query('SOUR:FREQ:STAR?'))
        print('Last  frequency?: ', self.query('SOUR:FREQ:STOP?'))
        
        # Prepare the list mode
        self.write('SOUR:FREQ:MODE LIST') # Set the frequency mode to list
        print('Frequency mode ?: ', self.query('SOUR:FREQ:MODE?'))
        self.write('SOUR:POW:MODE LIST') # Set the power mode to list
        print('Power mode ?: ', self.query('SOUR:POW:MODE?'))
        self.write('SOUR:LIST:MODE AUTO') # Set the list mode to auto
        print('List mode ?: ', self.query('SOUR:LIST:MODE?'))
#        self.api.write('TRIG:SEQ:TYPE GATE') # An external trigger signal repeatedly starts and stops the waveform’s playback.
        self.write('TRIG:SEQ:TYPE POIN')# Upon triggering, only a single point of the sweep (list) is played.
        print('Trig type?: ', self.query('TRIG:SEQ:TYPE?'))
        
        # Set stuff for the modulation
        self.write('SOUR:PULM:SOUR EXT')# Set the pulse modulation to be external
        print('Pulse modulation source?: ', self.query('SOUR:PULM:SOUR?'))
        self.write('SOUR:PULM:STAT ON') # Switch the pulse modulation ON
        print('State of pulse modulation? ', self.query('SOUR:PULM:STAT?'))
        self.write('SOUR:PULM:POL NORM') # Polarity NORMal, in case it was INVerted
        print('Polarity of modulation?: ', self.query('SOUR:PULM:POL?'))        
        # This is all for the ANAPICO to use the external trigger. 
        # BONUS for preparing the list with the external trigger. 
#        print('Testing query: ', self.api.query('*IDN?'))
#        print('Source for Trigger?: ', self.api.query('TRIG:SEQ:SOUR?'))
#        self.api.write('TRIG:SEQ:SOUR EXT') # Set the external trigger to ext
#        print('Source for Trigger?: ', self.api.query('TRIG:SEQ:SOUR?'))
#        print('First frequency?: ', self.api.query('SOUR:FREQ:STAR?'))
#        print('Last  frequency?: ', self.api.query('SOUR:FREQ:STOP?'))
#        
#        self.api.write('SOUR:FREQ:MODE LIST') # Set the frequency mode to list
#        print('Frequency mode ?: ', self.api.query('SOUR:FREQ:MODE?'))
#        self.api.write('SOUR:POW:MODE LIST') # Set the power mode to list
#        print('Power mode ?: ', self.api.query('SOUR:POW:MODE?'))
#        self.api.write('SOUR:LIST:MODE AUTO') # Set the list mode to auto
#        print('List mode ?: ', self.api.query('SOUR:LIST:MODE?'))
##        self.api.write('TRIG:SEQ:TYPE GATE') # An external trigger signal repeatedly starts and stops the waveform’s playback.
#        self.api.write('TRIG:SEQ:TYPE POIN')# Upon triggering, only a single point of the sweep (list) is played.
#        print('Trig type?: ', self.api.query('TRIG:SEQ:TYPE?'))
#        
#        # Set stuff for the modulation
#        self.api.write('SOUR:PULM:SOUR EXT')# Set the pulse modulation to be external
#        print('Pulse modulation source?: ', self.api.query('SOUR:PULM:SOUR?'))
#        self.api.write('SOUR:PULM:STAT ON') # Switch the pulse modulation ON
#        print('State of pulse modulation? ', self.api.query('SOUR:PULM:STAT?'))
#        self.api.write('SOUR:PULM:POL NORM') # Polarity NORMal, in case it was INVerted
#        print('Polarity of modulation?: ', self.api.query('SOUR:PULM:POL?'))

#        self.api.write('SOUR:AM:SOUR EXT')
#        print('Pulse modulation source?: ', self.api.query('SOUR:AM:SOUR?'))
#        self.api.write('SOUR:AM:STAT ON') # Switch the pulse modulation ON
#        print('Sate of pulse modulation? ', self.api.query('SOUR:AM:STAT?'))
        
        # Just copy Labview
#        self.api.write('OUTP ON') # Copy Labview
#        self.api.write('LIST:LEAR') # Copy Labview
#        self.api.write('FREQ:MODE LIST') # Copy Labview
#        self.api.write('LIST:MODE STEP') # Copy Labview
#        self.api.write('TRIG:LIST:SOUR EXT') # Copy Labview
#        self.api.write('SOUR:LIST:IND:START 0') # Copy Labview
#        self.api.write('SOUR:LIST:IND:STOP ') # Copy Labview

        
#        self.api.write('OUTP ON') # Copy Labview
#        self.api.write('LIST:LEAR') # Copy Labview
#        self.api.write('FREQ:MODE LIST') # Copy Labview
#        self.api.write('LIST:MODE STEP') # Copy Labview
#        self.api.write('TRIG:LIST:SOUR EXT') # Copy Labview
#        self.api.write('SOUR:LIST:IND:START 0') # Copy Labview
#        self.api.write('SOUR:LIST:IND:STOP ') # Copy Labview   
        
    def prepare_for_Rabi(self):
        """
        Prepare the signal generator for Rabi:
            Put in fixed mode, modulate the frequency, etc. 
        """
        _debug('Anapico: prepare for Rabi')

        self.write('SOUR:FREQ:MODE FIX') # Set the frequency mode to Fix
        print('Frequency mode ?: ', self.query('SOUR:FREQ:MODE?'))

        # Set stuff for the modulation
        self.write('SOUR:PULM:SOUR EXT')# Set the pulse modulation to be external
        print('Pulse modulation source?: ', self.query('SOUR:PULM:SOUR?'))
        self.write('SOUR:PULM:STAT ON') # Switch the pulse modulation ON
        print('State of pulse modulation? ', self.query('SOUR:PULM:STAT?'))
        self.write('SOUR:PULM:POL NORM') # Polarity NORMal, in case it was INVerted
        print('Polarity of modulation?: ', self.query('SOUR:PULM:POL?'))             
        
        
        

class simq03b_api(_mp.visa_tools.visa_api_base):    
    """
    API for SMIQ03B. This object just defines the functions to be used by the
    base class signal_generator_api.
    """
    def __init__(self): return
        
    def reset(self):
        """
        Resets the device to factory defaults (RF off).
        """
        _debug('simq03b_api.reset')
        self.write('*RST')
        self.query('*IDN?') # Pauses operation until fully reset?
    
    def send_list(self, frequencies=[1e9,2e9,3e9,4e9], powers=[-10,-5,-2,0], dwell=0.01, delay=0):
        """
        Sends the specified list values.
        
        Parameters
        ----------
        frequencies=[1e9,2e9,3e9,4e9]
            List of frequency values (Hz) to touch.
        
        powers=[0,0,0,0]
            List of power values (dBm) to touch.
        
        dwell=0 
            (IN second!) In immediate mode for the list sweep, this is how long the generator
            will dwell on a given step.
        
        delay=0
            How long to delay after triggering the next step.
        """
        _debug('simq03b_api.send_list')
        
        # Handle integers or lists for either frequencies or powers
        if not _s.fun.is_iterable(frequencies): frequencies = [frequencies]
        if not _s.fun.is_iterable(powers):      powers      = [powers]
        
        # Handle numpy arrays
        if not type(frequencies) == list: frequencies = list(frequencies)
        if not type(powers)      == list: powers      = list(powers)
        
        # Handle length-1 arrays:
        if len(frequencies) == 1: frequencies = frequencies*len(powers)
        if len(powers)      == 1: powers      = powers     *len(frequencies)
        
        # Poop if the lengths don't match
        if not len(frequencies) == len(powers): 
            print("ERROR: Lengths must match!")
            return
        
        #The mode switch to Fixed  when we write a power and dwell list. 
        #So I track the initial mode to put it back at the end. 
        initial_mode = self.get_mode()
        
        # Let's choose a list. 
        #To know the available list, the query is 'SOUR1:LIST:CAT?'
        self.write('SOUR:LIST:SEL /VAR/USE') 
         
        #Prepare the strings for the list command
        str_freq = 'SOUR:LIST:FREQ ' + str(frequencies[0]) #String for the frequency list command
        str_pow   = 'SOUR:LIST:POW ' + str(powers[0]) #String for the power list command
        str_dwell = 'SOUR:LIST:DWEL '+str(dwell) #String for the dwell list command
        for i in range(1,len(frequencies)):
            str_freq += ', ' + str(frequencies[i])
            str_pow += ', ' + str(powers[i])
        
        # For debugging
        print(str_freq)
        print(str_pow)
        print(str_dwell)
        
        self.write(str_freq)
        self.write(str_pow)
        self.write(str_dwell)
        
        # In SMIQ manual, it says:
        # Caution: This command has to be given after every creating and changing of a list.
        self.write('SOUR:LIST:LEARn')
        
        #Apparently the SMA change to Fixed mode after the power and the Dwell list is send... 
        #So I just switch back to the initial mode to make sure we end up in the same state. 
        self.set_mode(initial_mode)


    def set_mode(self, mode='List'):
        """
        Sets the generator to be in list or fixed mode.
        
        Paramters
        ---------
        mode='List'
            Set to 'Fixed' for fixed mode.
        """
        _debug('simq03b_api.set_mode')
        
        #If we choose list mode    
        if mode.lower() == 'list':
            #First choose a list if there was no, otherwise SMA100B is mad
            #To know the available list, the query is 'SOUR1:LIST:CAT?'
            self.write('SOUR1:LIST:SEL "/var/user/list1.lsw"') 
            
            self.write('OUTP1:STAT ON') #Somehow the SMA100B wants the RF to be ON for switching into list mode.
            self.write('SOUR1:LIST:MODE STEP') #Make Step mode in order to not automatically sweep all the frequencies
            self.write('SOURce:FREQuency:MODE LIST')
        else:
            #CW and FIXed are synonyms for SMA100B
            self.write('SOURce:FREQuency:MODE CW')
    
    def get_mode(self):
        """
        Returns 'Fixed' or 'List' depending on the device mode.
        """
        _debug('simq03b_api.get_mode')
        
        s = self.query('FREQ:MODE?')
        if s == None: return None
        
        s = s.strip()
        if   s == 'CW':  return 'Fixed'
        elif s == 'LIST': return 'List'
        else:
            print('ERROR: Unknown mode '+str(s))
            return
    
    def set_list_index(self, n=0):
        """
        Sets the list index, changing the appropriate frequency and power on the 
        output.
        
        Parameters
        ----------
        n=0
            0-referenced index.
        """
        _debug('simq03b_api.set_list_index')
        #We have to be in step mode for being able to set the list index
        self.write('SOUR1:LIST:MODE STEP') #Have to be in STEP mode in order to select the index
        self.write('SOUR1:LIST:IND '+ str(int(n)) ) 
    
    def get_list_index(self):
        """
        Gets the current list index.
        """
        _debug('simq03b_api.get_list_index')
        
        s = self.query('LIST:IND?')
        return int(s)
    
    def set_output(self, on=False):
        """
        Turns the output on or off.
        """
        _debug('simq03b_api.set_output')
        
        #Note that, for SMA, switiching off the output set the automatically the mode to Fixed.... !!
        if on: self.write("OUTP:STAT ON")
        else:  self.write("OUTP:STAT OFF")
        

    def get_output(self):
        """
        Returns 0 or 1 based on the RF output state.
        """
        _debug('simq03b_api.get_output')
        
        x = self.query('OUTP:STAT?')
        if x == None: return None
        print('Result is ', x) # For knowing the bug that we something have
        return int(x)

    def set_frequency(self, f=1e9):
        """
        Sets the frequency to f (Hz).
        
        Parameters
        ----------
        f=1e9
            Frequency (Hz)
        """
        _debug('simq03b_api.set_frequency')
        
        self.write('SOUR:FREQ:CW '+str(f))
        
    def get_frequency(self):
        """ 
        Returns the current frequency (Hz).
        """
        _debug('simq03b_api.get_frequency')
        
        x = self.query('SOUR:FREQ:CW?')
        if x == None: return None
        return float(x)
    
    def set_power(self, dbm=-30):
        """
        Sets the output power to the specified value (dBm).
        """
        _debug('simq03b_api.set_power')
        
        self.write("POWer "+str(dbm))
    
    def get_power(self):
        """
        Returns the current power level (dBm).
        """
        _debug('simq03b_api.get_power')
        
        x = self.query('POWer?')
        if x == None: return None
        return float(x)
    
    def get_list_powers(self):
        """
        Gets the list of powers.
        """
        _debug('simq03b_api.get_list_powers')
        
        s = self.query('SOUR:LIST:POW?')
        if s == None: return None
        a = []
        n = 0
        for x in s.split(','):
            try:
                a.append(float(x.strip()))
            except:
                print('ERROR get_list_powers(): non-float in list ', n, x)
            n += 1
        return a
        
    def get_list_frequencies(self):
        """
        Gets the list of frequencies.
        """
        _debug('simq03b_api.get_list_frequencies')
        
        s = self.query('SOUR:LIST:FREQ?')
        if s == None: return None
        a = []
        n = 0
        for x in s.split(','):
            try:
                a.append(float(x.strip()))
            except:
                print('ERROR get_list_frequencies(): non-float in list ', n, x)
            n += 1
        return a
        
    def get_list_length(self):
        """
        Returns the size of the list sweep.
        """
        _debug('simq03b_api.get_list_length')
        
        s = self.query('SOUR1:LIST:FREQ:POIN?')
        if s == None: return None
        return int(s)



class fake_api():
    """
    API for Anapico. This object just defines the functions to be used by the
    base class signal_generator_api.
    
    This is a fake API. Meant for testing code without access to an instrument. 
    
    Note: it is not completed yet. 
    """
    def __init__(self):
        
        # Fake attributes
        self.instrument = 'Houla'
        self.close = 'Yo'
        
    def reset(self):
        """
        Resets the device to factory defaults (RF off).
        """
        _debug('api.reset()')
        self.write('*RST')
        self.query('*IDN?') # Pauses operation until fully reset?
    
    def write(self, string='Yo'):
        """
        Fake wrtting function
        """
        return
    def query(self, string='Whats up?'):
        """
        Fake query function
        """
        return 'Knock Knock'
    
        return
        
    
    def send_list(self, frequencies=[1e9,2e9,3e9,4e9], powers=[-10,-5,-2,0], dwell=0, delay=0):
        """
        Sends the specified list values.
        
        Parameters
        ----------
        frequencies=[1e9,2e9,3e9,4e9]
            List of frequency values (Hz) to touch.
        
        powers=[0,0,0,0]
            List of power values (dBm) to touch.
        
        dwell=0
            In immediate mode for the list sweep, this is how long the generator
            will dwell on a given step.
        
        delay=0
            How long to delay after triggering the next step.
        """
        _debug('api.send_list()')
        
        # Handle integers or lists for either frequencies or powers
        if not _s.fun.is_iterable(frequencies): frequencies = [frequencies]
        if not _s.fun.is_iterable(powers):      powers      = [powers]
        
        # Handle numpy arrays
        if not type(frequencies) == 'list': frequencies = list(frequencies)
        if not type(powers)      == 'list': powers      = list(powers)
        
        # Handle length-1 arrays:
        if len(frequencies) == 1: frequencies = frequencies*len(powers)
        if len(powers)      == 1: powers      = powers     *len(frequencies)
        
        # Poop if the lengths don't match
        if not len(frequencies) == len(powers): 
            print("ERROR: Lengths must match!")
            return
        
        # Copy the input
        self.fs = frequencies
        self.ps = powers
        self.dwell = dwell
        self.delay = delay

    def set_mode(self, mode='List'):
        """
        Sets the generator to be in list or fixed mode.
        
        Paramters
        ---------
        mode='List'
            Set to 'Fixed' for fixed mode.
        """
        
        self.mode = mode
    
    def get_mode(self):
        """
        Returns 'Fixed' or 'List' depending on the device mode.
        """
        return self.mode
    
    def set_list_index(self, n=0):
        """
        Sets the list index, changing the appropriate frequency and power on the 
        output.
        
        Parameters
        ----------
        n=0
            0-referenced index.
        """
        self.n = n
    
    def get_list_index(self):
        """
        Gets the current list index.
        """
        return self.n
    
    def set_output(self, on=False):
        """
        Turns the output on or off.
        """
        self.on = on

    def get_output(self):
        """
        Returns 0 or 1 based on the RF output state.
        """
        return self.on

    def set_frequency(self, f=1e9):
        """
        Sets the frequency to f (Hz).
        
        Parameters
        ----------
        f=1e9
            Frequency (Hz)
        """
        self.f = f
        
    def get_frequency(self):
        """ 
        Returns the current frequency (Hz).
        """
        return self.f
    
    def set_power(self, dbm=-30):
        """
        Sets the output power to the specified value (dBm).
        """
        self.p = dbm
    
    def get_power(self):
        """
        Returns the current power level (dBm).
        """
        return self.p
    
    def get_list_powers(self):
        """
        Gets the list of powers.
        """
        return self.ps
        
    def get_list_frequencies(self):
        """
        Gets the list of frequencies.
        """
        return self.fs
        
    def get_list_length(self):
        """
        Returns the size of the list sweep.
        """
        return len(self.ps)


    

class GUISignalGenerator(_mp.visa_tools.visa_gui_base):
    """
    Graphical front-end for the Anapico signal generator.
    
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

    def __init__(self, name='Anapico', show=True, block=False, timeout=2e3, write_sleep=0.02, pyvisa_py=False):
        _debug('GUISignalGenerator: __init__()')
        
        # Run the basic stuff.
        _mp.visa_tools.visa_gui_base.__init__(self, name, show, block, signal_generator_api, timeout=timeout, write_sleep=write_sleep, pyvisa_py=pyvisa_py)
    
        # Add stuff to the GUI.
        self.button_reset     = self.grid_top.add(_g.Button('Reset')).set_width(60).disable()
        self.button_rf        = self.grid_top.add(_g.Button('RF', checkable=True)).set_width(25).disable()
        self.combo_mode       = self.grid_top.add(_g.ComboBox(['Fixed', 'List'])).disable()
        self.number_dbm       = self.grid_top.add(_g.NumberBox(bounds=(-30,25),  suffix=' dBm')).disable()
        self.number_frequency = self.grid_top.add(_g.NumberBox(bounds=(1, 20e9), suffix='Hz', siPrefix=True, dec=True)).disable()
        self.number_list_index= self.grid_top.add(_g.NumberBox(0, bounds=(0,None))).disable()
        self.button_sweep     = self.grid_top.add(_g.Button('Sweep', checkable=True)).disable()
        self.number_iteration = self.grid_top.add(_g.NumberBox(0))
        
        self.grid_bot.set_column_stretch(1)
        self.tabs_data = self.grid_bot.add(_g.TabArea(self.name+'_tabs_data'), alignment=0)
        self.tab_list  = self.tabs_data.add_tab('List')
        self.button_generate_list = self.tab_list.add(_g.Button('Generate List'))
        self.button_send_list     = self.tab_list.add(_g.Button('Send List', checkable=True)).disable()
        self.label_list_status    = self.tab_list.add(_g.Label(''))
        self.tab_list.set_column_stretch(3)
        self.tab_list.new_autorow()
        self.plot_list = self.tab_list.add(_g.DataboxPlot('*.list', self.name+'_plot_list'), alignment=0, column_span=10)
        
        self.settings.add_parameter('Generate-List/f1',    1.0e9, bounds=(1.0,20e9), siPrefix=True, suffix='Hz', dec=True)
        self.settings.add_parameter('Generate-List/f2',   10.0e9, bounds=(1.0,20e9), siPrefix=True, suffix='Hz', dec=True)
        self.settings.add_parameter('Generate-List/P1',      -30, bounds=(-30,25),   suffix='dBm', type='float')
        self.settings.add_parameter('Generate-List/P2',      -30, bounds=(-30,25),   suffix='dBm', type='float')
        self.settings.add_parameter('Generate-List/Steps',   100, bounds=(2, 10000))
        self.settings.add_parameter('Generate-List/Direction', 0, values=['1->2', '2->1'])
        self.settings.add_parameter('Generate-List/Mode',      0, values=['Linear', 'Log'])
        
        self.settings.add_parameter('Sweep/Iterations', 1, bounds=(0,None), tip='How many times to sweep.')
        self.settings.add_parameter('Sweep/n1',         0, bounds=(0,None), tip='Start index.')
        self.settings.add_parameter('Sweep/n2',  10000000, bounds=(0,None), tip='Stop index (will stop at list limits).')
        
        # Connect signals
        self.button_reset        .signal_clicked.connect(self._button_reset_clicked)
        self.button_generate_list.signal_clicked.connect(self._button_generate_list_clicked)
        self.button_send_list    .signal_toggled.connect(self._button_send_list_toggled)
        self.button_sweep        .signal_toggled.connect(self._button_sweep_toggled)
        self.button_rf           .signal_toggled.connect(self._button_rf_toggled)

        self.number_dbm       .signal_changed.connect(self._number_dbm_changed)
        self.number_frequency .signal_changed.connect(self._number_frequency_changed)
        self.number_list_index.signal_changed.connect(self._number_list_index_changed)
        
        self.combo_mode.signal_changed.connect(self._combo_mode_changed)
        

        # Overloaded functions
        self.plot_list.after_load_file = self._after_plot_list_load
        

    def _after_connect(self):
        """
        Called after a successful connect.
        """
        _debug('GUISignalGenerator: _after_connect()')
        # Update the controls
        self.button_sweep.enable()
        self.button_send_list.enable()
        self.button_reset.enable()
        
        # Update the RF button.
        rf_on = self.api.get_output()
        if rf_on == None: self.button_rf.set_checked(True,  block_events=True).enable()
        else:             self.button_rf.set_checked(rf_on, block_events=True).enable()
    
        # Update the combo; we block first just in case the value doesn't "change"
        if self.api == None: self.label_instrument_name.set_text('Simulation')
        else:
            if self.api.get_mode() == 'Fixed': self.combo_mode.set_value(0, block_events=True).enable()
            else:                              self.combo_mode.set_value(1, block_events=True).enable()
            self._combo_mode_changed()
            
            # Update the list plot
            self.query_list()

    def _update_gui(self):
        """
        Checks the status of the machine and updates the GUI.
        """
        
        # Update the RF button.
        rf_on = self.api.get_output()
        if rf_on == None: rf_on = True
        self.button_rf.set_checked(rf_on, block_events=True).enable()
    
        # Update the combo; we block first just in case the value doesn't "change"
        if self.api == None: self.label_instrument_name.set_text('Simulation')
        else:
            if self.api.get_mode() == 'Fixed': self.combo_mode.set_value(0, block_events=True).enable()
            else:                              self.combo_mode.set_value(1, block_events=True).enable()
            self._combo_mode_changed()
    
            # Update the list plot
            self.query_list()
                
    def _after_disconnect(self):
        """
        Called after a successful disconnect.
        """
        _debug('GUISignalGenerator: _after_disconnect()')
        self.button_sweep.disable()
        self.button_reset.disable()
        self.button_send_list.disable()
        self.button_rf.set_checked(False, block_events=True).disable()
        self.number_dbm.disable()
        self.number_frequency.disable()
        self.number_list_index.disable()
        self.combo_mode.disable()
    
    def _button_reset_clicked(self, *a):
        """
        Reset the device
        """
        self.api.reset()
        
        # Update the parameters
        self._update_gui()
    
    def _combo_mode_changed(self, *a):
        """
        Called when someone changes mode.
        """
        
        # Get the current mode.
        mode = self.api.get_mode()
        
        # Update the machine if the combo mode doesn't match
        if not mode == self.combo_mode.get_text():
            self.api.set_mode(self.combo_mode.get_text())
        
        # Get the mode again, to make sure it still matches.
        if self.api.get_mode() == 'List': 
            self.combo_mode.set_index(1, block_events=True).enable()
            self.number_list_index.set_value(self.api.get_list_index(), block_events=True).enable()
            self._number_list_index_changed()
            self.number_frequency.disable() #Disable the frequency button
            self.number_dbm.disable() #Disable the dbm button
        else:  
            #It is in fixed mode and we update the value of the button
            self.combo_mode.set_index(0, block_events=True).enable()
            self.number_frequency.set_value(self.api.get_frequency()).enable()
            self.number_dbm      .set_value(self.api.get_power()).enable()
            self.number_list_index.disable() #Change the list index. 

    def _number_dbm_changed(self, *a):
        """
        Called when someone changes the dbm.
        """
        self.api.set_power(self.number_dbm.get_value())
    
    def _number_frequency_changed(self, *a):
        """
        Called when someone changes the frequency.
        """
        self.api.set_frequency(self.number_frequency.get_value())

    def _number_list_index_changed(self, *a):
        """
        When someone changes the step number in LIST mode.
        """
        self.api.set_list_index(self.number_list_index.get_value())
        
        # Make sure.
        n = self.api.get_list_index()
        self.number_list_index.set_value(n, block_events=True)
        
        # Update the frequency and power in the safest possible way
#        fs = self.api.get_list_frequencies()
#        ps = self.api.get_list_powers()
#        self.number_dbm.set_value(ps[n])
#        self.number_frequency.set_value(fs[n])
        
        # Update the frequency and power using the graph if we have it.
        
        # If enabled, things are out of sync, get the list.
        if self.button_send_list._widget.isEnabled(): self.query_list()
        
        # Get the power and frequency from the plot
        self.number_dbm      .set_value(self.plot_list['P_dBm'][n])
        self.number_frequency.set_value(self.plot_list['f_Hz'][n])
        
            
            
    def query_list(self):
        """
        Asks the instrument for the list values and updates the plot_list.
        """
        self.plot_list.clear()
        self.settings.send_to_databox_header(self.plot_list)
        
        self.label_list_status.set_text('Getting frequencies and powers.')
        self.window.process_events()
        
        fs = self.api.get_list_frequencies()
        ps = self.api.get_list_powers()
        if fs == None or ps == None: return
        
        if not len(fs) == len(ps):
            print("ERROR query_list(): List lengths do not match. len(fs)="+str(len(fs))+' len(ps)='+str(len(ps)) )
        
        N  = len(fs)
        self.plot_list['n'] = _n.linspace(0, N-1, N)
        self.plot_list['f_Hz']  = fs
        self.plot_list['P_dBm'] = ps
        
        self.label_list_status.set_text(str(N) + ' points in list memory')
        self.plot_list.plot()
        self.button_send_list.disable()
        self.window.process_events()
            
    def _button_generate_list_clicked(self, *a):
        """
        Creates a ramp the frequency and power list.
        """
        _debug('GUISignalGenerator: _button_generate_list_clicked()', a)
        
        N = self.settings['Generate-List/Steps']
        
        # Generate a list in the direction we wish to step
        if self.settings['Generate-List/Direction'] == '1->2':
            f1 = self.settings['Generate-List/f1']
            f2 = self.settings['Generate-List/f2']
            d1 = self.settings['Generate-List/P1']
            d2 = self.settings['Generate-List/P2']
        else:
            f1 = self.settings['Generate-List/f2']
            f2 = self.settings['Generate-List/f1']
            d1 = self.settings['Generate-List/P2']
            d2 = self.settings['Generate-List/P1']
        
        # Get the powers in mW
        P1 = 10**(d1/10.0)
        P2 = 10**(d2/10.0)
        
        # Clear the plot
        self.plot_list.clear()
        self.settings.send_to_databox_header(self.plot_list)

        # Indices
        self.plot_list['n'] = _n.linspace(0, N-1, N)
        
        # Create the sweep in either linear or log space.
        if self.settings['Generate-List/Mode'] == 'Linear':
            self.plot_list['f_Hz']  = _n.linspace(f1, f2, N)
            self.plot_list['P_dBm'] = 10*_n.log10(_n.linspace(P1, P2, N))
        
        # Log steps
        else:
            self.plot_list['f_Hz']  = _s.fun.erange(f1, f2, N)
            self.plot_list['P_dBm'] = _n.linspace  (d1, d2, N)
        
        # Plot it
        self.plot_list.plot()
        self.window.process_events()
        
        # Enable send list
        self.button_send_list.enable()
        
        # Remove visible knowledge
        self.label_list_status.set_text('Shown list does not match device list.')
    
    def _after_plot_list_load(self):
        """
        Called when someone loads a plot_list.
        """
        self.button_send_list.enable()
        self.label_list_status.set_text('Shown list does not match device list.')
        
    def _button_send_list_toggled(self, *a):
        """
        Send the list to the anapico.
        """
        _debug('GUISignalGenerator: _button_send_list_toggled()', a)
        
        if not self.button_send_list.is_checked(): return
        
        # Clear the label
        self.label_list_status.set_text('')
        self.window.process_events()

        # If there is data to send
        if len(self.plot_list): 
            
            # Reset
#            self.label_list_status.set_text('Resetting...')
#            self.window.process_events()
#            self.api.reset()
        
            # Send it
            self.label_list_status.set_text('Sending...')
            self.window.process_events()
            self.api.send_list(self.plot_list['f_Hz'], self.plot_list['P_dBm'], 
                               dwell=1000, delay=0)
            
        # Check it
        self.label_list_status.set_text('Double-checking...')
        self.window.process_events()
        self.query_list()
    
        # Update the RF button
        self.button_rf.set_checked(self.api.get_output(), block_events=True)
        
        # Undo the button
        self.button_send_list.set_checked(False, block_events=True)
                        
    
    def _button_sweep_toggled(self, *a):
        """
        Dummy function to overload. Just waits 0.25 seconds on each step.
        """
        _debug('GUISignalGenerator: _button_sweep_toggled()', a)
        
        # Only run the sweep if we have enabled the button
        if self.button_sweep.is_checked():
            
            # Run the "before sweep" setup function for the user to overwrite 
            # (default is just a pause)
            self.before_sweep()
            
            # Set list mode
            self.combo_mode.set_index(1)
            self.api.set_mode('List') #Set the mode to list !!
            # Update the RF button
            self.button_rf.set_checked(self.api.get_output(), block_events=True)
            
            
            # Get list length from the generator
            ps = self.api.get_list_powers()
            fs = self.api.get_list_frequencies()
            
            # Make sure they match!
            if not len(ps) == len(fs): 
                print("ERROR: Lengths of power and frequency lists do not match!")
                return
            
            
            # Update the user
            self.label_list_status.set_text(str(len(fs)) + ' points in list memory')
            
            # Loop for the number of iterations
            self.number_iteration.set_value(0)
            while self.number_iteration.get_value() < self.settings['Sweep/Iterations'] \
               or self.settings['Sweep/Iterations'] <= 0:
            
                # Break out if canceled
                if not self.button_sweep.is_checked(): break
                
                # Loop
                for n in range(self.settings['Sweep/n1'], min(self.settings['Sweep/n2'], len(fs))):
                    
                    # Break out if canceled
                    if not self.button_sweep.is_checked(): break
                
                    # Set the list index, which updates the machine
                    self.api.set_list_index(n)
                    #I'm adding these lines to debug the fact that Api doesn't change the frequency of its output. 
                    _debug(self.api.get_list_index(), self.api.get_frequency(), self.api.get_power())
                    #print(self.api.get_list_frequencies())
                    
                    self.number_list_index.set_value(n,     block_events=True)
                    self.number_frequency .set_value(fs[n], block_events=True)
                    self.number_dbm       .set_value(ps[n], block_events=True)
                    self.window.process_events()
                    
                    # This is where you could insert some interesting code.
                    self.after_sweep_set_list_index()
            
                # Increase the iteration count
                self.number_iteration.increment()
                
                # Run user code
                self.after_single_sweep()
            
            # Run user code
            self.after_all_sweeps()
            
            # All done with the loop. Disable the sweep button!
            # We put this after the user functions so they can tell if
            # someone manually quit out of the loop.
            self.button_sweep.set_checked(False, block_events=True)
    
    def before_sweep(self):
        """
        Dummy function to overload with functionality to perform before the 
        sweep begins.
        """
        _debug('GUISignalGenerator: before_sweep()')
        self.window.sleep(0.05)
    
    def after_sweep_set_list_index(self):
        """
        Dummy function (just a 0.05 second pause) to overwrite for doing 
        stuff just after setting the list index in the list sweep.
        """
        _debug('GUISignalGenerator: after_sweep_set_list_index()')
        self.window.sleep(0.05)
    
    def after_single_sweep(self):
        """
        Dummy function to overwrite for doing something after the
        list sweep is complete.
        """
        _debug('GUISignalGenerator: .after_single_sweep()')
        self.window.sleep(0.05)
    
    def after_all_sweeps(self):
        """
        Dummy function to overwrite for doing something after all 
        the sweeps are done (iteration = iterations)
        """
        _debug('GUISignalGenerator: after_all_sweeps()')
        self.window.sleep(0.05)
        
    def _button_rf_toggled(self, *a):
        """
        Turns the output on or off.
        """
        _debug('GUISignalGenerator: _button_rf_toggled()', a)
        # Set
        self.api.set_output(self.button_rf.is_checked())
        
        # Verify
        self.button_rf.set_checked(self.api.get_output(), block_events=True)
        
#        #The mode of the SMA switch to Fixed when the RF are off
#        self._combo_mode_changed()
        


        
        
        
     

        
if __name__ == '__main__':
    
    _mp.visa_tools._debug_enabled = True
    _debug_enabled                = True
    
    #self = GUISignalGenerator()
    #self = signal_generator_api('SMA100B') #This will not pop-out the GUI
    self = GUISignalGenerator('Anana') #This will pop-out the GUI
    
    # Note the api for quickly make tests
    # For sending query, type a.query(YOUR_QUERY)
    # For writting thing, type a.write(YOUR_QUERY)
    a = self.api 
   
   
   
   
   