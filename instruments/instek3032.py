from instruments import instr
import numpy as np
# from time import sleep

class Instek3032(instr.Instr):

    def __init__(self, visa_name, visa_library=''): # '' is recognized as default visa DLL by pyvisa
        super(Instek3032, self).__init__(visa_name, visa_library)
        self.current_channel = 1
        self.load = "INF"
        self.visa_instr.read_termination = '\n'
        self.visa_instr.timeout = 50000

    def __del__(self):
        self.write("SYSTem:LOCal")
        if not self._clean:
            self.clean()
        del self.visa_instr
        # del self.visa_resource_manager


    def busy(self):
        """returns whether or not the device is busy with anything, like another command."""
        return not(bool(self.query("*OPC?")))

    def get_channel_waveform(self):
        """Returns the characteristics of the current channel's waveform as [name, freq, amplitude, DC offset]"""
        self.__waveform_raw = self.query(f"SOURCE{self.current_channel}:APPLY?").split(' ')
        name = self.__waveform_raw[0]
        freq, amp, offset = self.__waveform_raw[1].split(',')
        self.__waveform = [name, float(freq), float(amp), float(offset)]
        return self.__waveform
    
    def apply_waveform(self, waveform, **kwargs):
        """Changes waveform (and, optionnaly, characteristics) and **turns output on** (!!!)"""
        if set(kwargs.keys()) == {"freq", "amp", "offset"}:
            freq = kwargs["freq"]
            amp = kwargs["amp"]
            offset = kwargs["offset"]
            
            self.write(f"SOURCE{self.current_channel}:APPLy:{waveform} {freq},{amp},{offset}")
        elif not kwargs : #if we have no kwargs, kwargs is empty so not(kwargs) is true
            self.write(f"SOURCE{self.current_channel}:APPLy:{waveform}")
        else : 
            raise ValueError("either give no kwargs or all of 'freq', 'amp' and 'offset'")



# ----------- getting / setting current channel
    @property
    def current_channel(self):
        return self.__current_channel
    
    @current_channel.setter
    def current_channel(self, n):
        if n in [1, 2]:
            self.__current_channel = n
        else :
            raise ValueError("Instrument only has two channels : 1 and 2")

# ----------- getting / setting current channel output state

    @property
    def output(self):
        self.__output = bool(self.query(f"OUTPut{self.current_channel}?"))
        return self.__output

    @output.setter
    def output(self, state):
        if type(state) is str :
            if state.lower == "on":
                self.write(f"OUTPut{self.current_channel} ON")
            elif state.lower == "off" :
                self.write(f"OUTPut{self.current_channel} OFF")
            else : 
                raise ValueError("State must be True, False, 0, 1, 'on' or 'off' (not case sensitive)")
        elif state in [0, 1, True, False]:
            if bool(state):
                self.write(f"OUTPut{self.current_channel} ON")
            else :
                self.write(f"OUTPut{self.current_channel} OFF")
        else: 
            raise ValueError("State must be True, False, 0, 1, 'on' or 'off' (not case sensitive)")

# ----------- getting / setting output impedance mode

    @property
    def load(self):
        self.__load = self.query(f"OUTPut{self.current_channel}:LOAD?")
        return self.__load
    
    @load.setter
    def load(self, load_value):
        if load_value.lower() in ["inf", "def"]:
            self.write(f"OUTPut{self.current_channel}:LOAD {load_value}")
        else : 
            raise ValueError("load value must be 'INF' (high Z) or 'DEF' (50ohm) (case insensitive)")
    
# ----------- getting / setting output frequency

    @property
    def freq(self):
        self.__freq = float(self.query(f"SOURce{self.current_channel}:FREQuency?"))
        return self.__freq
    
    @freq.setter
    def freq(self, frequency):
        self.write(f"SOURce{self.current_channel}:FREQuency {frequency}")

# ----------- getting / setting output amplitude

    @property
    def ampl(self):
        self.__ampl = float(self.query(f"SOURce{self.current_channel}:AMPLitude?"))
        return self.__ampl
    
    @ampl.setter
    def ampl(self, amplitude):
        self.write(f"SOURce{self.current_channel}:AMPLitude {amplitude}")

# ----------- getting / setting output DC Offset

    @property
    def dc_offset(self):
        self.__dc_offset = float(self.query(f"SOURce{self.current_channel}:DCOffset?"))
        return self.__dc_offset
    
    @dc_offset.setter
    def dc_offset(self, offset):
        self.write(f"SOURce{self.current_channel}:DCOffset {offset}")

# ----------- getting / setting output phase (IN DEGREES !)

    @property
    def phase(self):
        self.__phase = float(self.query(f"SOURce{self.current_channel}:PHASe?"))
        return self.__phase
    
    @phase.setter
    def phase(self, offset):
        self.write(f"SOURce{self.current_channel}:PHASe {offset}")

# ----------- getting / setting output voltage unit

    @property
    def unit(self):
        self.__unit = self.query(f"SOURce{self.current_channel}:VOLTage:UNIT?")
        return self.__unit
    
    @unit.setter
    def unit(self, voltage_unit):
        if voltage_unit.lower() in ["vpp", "vrms", "dbm"]:
            self.write(f"SOURce{self.current_channel}:VOLTage:UNIT {voltage_unit}")
        else : 
            raise ValueError("Unit must be 'Vpp', 'Vrms' or 'dBm' (case insensitive)")