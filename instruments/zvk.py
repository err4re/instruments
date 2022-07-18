from instruments import instr
import numpy as np
# from time import sleep

class Zvk(instr.Instr):

    def __init__(self, visa_name, visa_library=''): # '' is recognized as default visa DLL by pyvisa
        super(Zvk, self).__init__(visa_name, visa_library)
        self.cls()
        # self.current_measurement_name = None
        #self.visa_instr.read_termination = '\n' # this is the problematic part, makes weird artifacts appear for some reason
        self.visa_instr.timeout = 5000
        #self.visa_instr.query_delay = 1e-3
        self.current_channel = 1
        self.write("ROSCillator INTernal")
        self.set_data_format("REAL, 32")
        self.f = dict()
        self.z = dict()



    # sets in which format the data is sent from VNA to the computer when reading data
    # ASCII or binary 32 or 64 bit
    def set_data_format(self, data_format):
        if not(data_format.upper() in ["ASCII", "REAL,32", "REAL,64", "REAL, 32", "REAL, 64"]):
            print("ERROR: data_format must be 'ASCII', 'REAL, 32' or 'REAL, 64'")
            return None
        else:
            self.write("FORMat {1}".format(self.current_channel, data_format))

    def set_current_channel(self, channel):
        if channel not in range(1, 5):
            raise ValueError("Invalid channel number (must be between 1 and 4)")
        else : 
            self.write(f'INSTRument:NSELECT {channel}')
            self.current_channel = channel

    # changes source power
    @property
    def power(self):
        self._power = self.query("SOURce{0}:POWer?".format(self.current_channel))
        return self._power
    
    @power.setter
    def power(self, power_dBm):
        self.write("SOURce{0}:POWer {1}".format(self.current_channel, power_dBm))
        # self.write("SOURce{0}:POWer:MODE ON".format(self.current_channel))


    @property
    def output(self):
        self.query("SOURce{0}:POWer:STATe?".format(self.current_channel))

    @output.setter
    def output(self, out):
        self.write("SOURce{0}:POWer:STATe {1}".format(self.current_channel, 'ON' if out else 'OFF'))


    #getting and setting center frequency of graph
    @property
    def center_freq(self):
        self.__center_freq = self.query_ascii_values(f"SENSE{self.current_channel}:FREQUENCY:CENTER?")[0]
        return self.__center_freq
    
    @center_freq.setter
    def center_freq(self, center_frequency):
        self.write(f"SENSE{self.current_channel}:FREQUENCY:CENTER {center_frequency}")
    
    #getting and setting frequency span of graph
    @property
    def freq_span(self):
        self.__freq_span = self.query_ascii_values(f"SENSE{self.current_channel}:FREQUENCY:SPAN?")[0]
        return self.__freq_span
    
    @freq_span.setter
    def freq_span(self, frequency_span):
        self.write(f"SENSE{self.current_channel}:FREQUENCY:SPAN {frequency_span}")

    # getting and setting start frequency of graph
    @property
    def start_freq(self):
        self.__start_freq = self.query_ascii_values(f"SENSE{self.current_channel}:FREQUENCY:START?")[0]
        return self.__start_freq
    
    @start_freq.setter
    def start_freq(self, start_frequency):
        self.write(f"SENSE{self.current_channel}:FREQUENCY:START {start_frequency}")

    #getting and setting stop frequency of graph
    @property
    def stop_freq(self):
        self.__stop_freq = self.query_ascii_values(f"SENSE{self.current_channel}:FREQUENCY:STOP?")[0]
        return self.__stop_freq
    
    @stop_freq.setter
    def stop_freq(self, stop_frequency):
        self.write(f"SENSE{self.current_channel}:FREQUENCY:STOP {stop_frequency}")

    #getting and setting frequency window as a center + span pair
    @property
    def freq_center_span(self):
        self.__freq_center_span = np.array([self.center_freq, self.freq_span])
        return self.__freq_center_span
    
    @freq_center_span.setter
    def freq_center_span(self, input_list):
        if len(input_list) == 2:
            center_frequency, frequency_span = input_list
            self.write(f"SENSe{self.current_channel}:SWEep:SPACing LINear")
            self.center_freq = center_frequency 
            self.freq_span = frequency_span
        else : 
            raise ValueError("Frequency args must be a an array of 2 numbers : center freq, then span")
    
    #getting and setting a frequency window as a start + stop pair
    @property
    def freq_start_stop(self):
        self.__freq_start_stop = np.array([self.start_freq, self.stop_freq])
        return self.__freq_start_stop
    
    @freq_start_stop.setter
    def freq_start_stop(self, input_list):
        if len(input_list) == 2:
            start_frequency, stop_frequency = input_list
            self.write(f"SENSe{self.current_channel}:SWEep:SPACing LINear")
            self.start_freq = start_frequency 
            self.stop_freq = stop_frequency
        else : 
            raise ValueError("Frequency args must be a an array of 2 numbers : start freq, then stop freq")

    #getting and setting sweep duration
    @property
    def sweep_duration(self):
        self.__sweep_duration = self.query_ascii_values(f"SENSE{self.current_channel}:SWEEP:TIME?")[0]
        return self.__sweep_duration
    
    @sweep_duration.setter
    def sweep_duration(self, duration):
        self.write(f"SENSE{self.current_channel}:SWEEP:TIME {duration}")
    
    #Getting and setting the number of points in a sweep
    @property
    def sweep_points(self):
        self.__sweep_points = int(self.query_ascii_values(f"SENSE{self.current_channel}:SWEEP:POINTS?")[0])
        return self.__sweep_points
    
    @sweep_points.setter
    def sweep_points(self, num_points):
        self.write(f"SENSE{self.current_channel}:SWEEP:POINTS {int(num_points)}")
    
    #getting and setting the frequency step in a sweep
    @property
    def sweep_step(self):
        self.__sweep_step = int(self.query_ascii_values(f"SENSE{self.current_channel}:SWEEP:STEP?")[0])
        return self.__sweep_step
    
    @sweep_step.setter
    def sweep_step(self, freq_step):
        self.write(f"SENSE{self.current_channel}:SWEEP:STEP {freq_step}")
    
    #getting and turning averaging on and off
    @property
    def averaging(self):
        self.__averaging = bool(self.query_ascii_values(f"SENSE{self.current_channel}:AVERAGE?")[0])
        return self.__averaging
    
    @averaging.setter
    def averaging(self, state):
        self.write(f"SENSE{self.current_channel}:AVERAGE {int(state)}")

    #getting and setting averaging of sweeps  
    @property
    def average_count(self):
        self.__average_count = self.query_ascii_values(f"SENSE{self.current_channel}:AVERage:COUNT?")[0]
        return self.__average_count

    @average_count.setter
    def average_count(self, count):
        if count not in range(0, 257):
            raise ValueError("Averaging count must be between 0 and 256")
        else : 
            self.write(f"SENSE{self.current_channel}:AVERage:COUNt {count}")

    #getting and setting bandwidth
    @property
    def bandwidth(self):
        try :
            self.__bandwidth = self.query_ascii_values(f"SENSE{self.current_channel}:BANDwidth?")[0]
        except ValueError :
            self.__bandwidth = self.query(f"SENSE{self.current_channel}:BANDwidth?")
        return self.__bandwidth
    
    @bandwidth.setter
    def bandwidth(self, bandwidth):
        self.write(f"SENSE{self.current_channel}:BANDwidth {bandwidth}")

    #getting and setting sweep direction
    @property
    def sweep_direction(self):
        self.__sweep_direction = self.query(f'SENSE{self.current_channel}:SWEEP:DIR?')
        if "UP" in self.__sweep_direction :
            self.__sweep_direction = "UP"
        elif "DOWN" in self.__sweep_direction:
            self.__sweep_direction = "DOWN"
        else :
            raise IOError("Instrument returned invalid value that is neither UP nor DOWN")
        return self.__sweep_direction
    
    @sweep_direction.setter
    def sweep_direction(self, direction):
        if direction.casefold() in ["up", "down"]:
            self.write(f'SENSE{self.current_channel}:SWEEP:DIR {direction}')
        else : 
            raise ValueError("Direction must be 'up' or 'down'.")
    
    #getting and setting sweep trig modes, two ways
    @property
    def continuous_sweep(self):
        self.__continuous_sweep = bool(self.query_ascii_values("INIT:CONT?")[0])
        return self.__continuous_sweep
    
    @continuous_sweep.setter
    def continuous_sweep(self, mode):
        self.write(f"INIT:CONT {'ON' if mode else 'OFF'}")
    
    @property
    def single_sweep(self):
        self.__single_sweep = not self.continuous_sweep
        return self.__single_sweep
    
    @single_sweep.setter
    def single_sweep(self, mode):
        self.continuous_sweep = not mode

    #getting and setting the number of sweeps a single trig triggers (in frequency mode)
    @property
    def sweep_count(self):
        self.__sweep_count = self.query_ascii_values(f"SENSE{self.current_channel}:SWEEP:COUNT?")[0]
        return self.__sweep_count
    
    @sweep_count.setter
    def sweep_count(self, N):
        self.write(f"SENSE{self.current_channel}:SWEEP:COUNT {N}")


    
    #A method that triggers sweeps
    def trigger(self):
        self.write("INIT")

    # cheching whether the VNA is busy
    def busy(self):
        """returns whether or not the device is busy with anything, like another command."""
        return not(bool(self.query("*OPC?")))
    
    #A method for getting trace data
    def get_data(self, trace='CH1DATA'):
        tr_names = [ 'CH1DATA','CH2DATA','CH3DATA','CH4DATA', 'MDATA1', 'MDATA2', 'MDATA3', 'MDATA4', 'MDATA5', 'MDATA6', 'MDATA7', 'MDATA8' ]
        if trace in tr_names:
            traces = [ trace ]
        elif trace == 'all':
            traces = tr_names
        else:
            print("ERROR : invalid trace name")
            traces = []
            f = None
            z = None

        for t in traces:
            f = np.array(self.visa_instr.query_binary_values(f'trace:stimulus? {t}', is_big_endian=False))
            tmp = self.visa_instr.query_binary_values(f'trace? {t}', is_big_endian=False)
            z = np.array(tmp[::2]) + 1j*np.array(tmp[1::2])
            self.f[t] = f
            self.z[t] = z

        return f, z