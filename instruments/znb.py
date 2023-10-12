from instruments import instr
import numpy as np
# from time import sleep

class Znb(instr.Instr):

    def __init__(self, visa_name, visa_library=''): # '' is recognized as default visa DLL by pyvisa
        super(Znb, self).__init__(visa_name, visa_library)
        self.cls()
        # self.current_channel = 0
        # self.current_measurement_name = None
        self.visa_instr.read_termination = '\n'
        self.visa_instr.timeout = 50000
        self.write("ROSCillator INTernal")
        channel = self.list_channels()
        if channel:
            self.current_channel = channel[0]
            trace = self.list_traces(self.current_channel)
            if trace:
                self.current_measurement_name = trace[0]
            else:
                return False
        else:
            return False
        self.set_current_channel_and_trace(self.current_channel, self.current_measurement_name)
        self.set_data_format("ASCII")




    # sets in chich format the data is sent from VNA to the computer when reading data
    # ASCII or binary 32 or 64 bit
    def set_data_format(self, data_format):
        if not(data_format.upper() in ["ASCII", "REAL,32", "REAL,64", "REAL, 32", "REAL, 64"]):
            print("ERROR: data_format must be 'ASCII', 'REAL, 32' or 'REAL, 64'")
            return None
        else:
            self.write("FORMat {1}".format(self.current_channel, data_format))


    # changes source power
    def set_power(self, power_dBm):
        self.write("SOURce{0}:POWer {1}".format(self.current_channel, power_dBm))
        # self.write("SOURce{0}:POWer:MODE ON".format(self.current_channel))

    ##Leo did this
    def get_power(self):
        return self.query("SOURce{0}:POWer?".format(self.current_channel))


    def set_power_off(self):
        self.write("SOURce{0}:POWer:STATe OFF".format(self.current_channel))

    def set_power_on(self):
        self.write("SOURce{0}:POWer:STATe ON".format(self.current_channel))


    # get nb of sweep points
    def get_nb_points(self):
        bla = self.query("SENSe{0}:SWEep:POINts?".format(self.current_channel))
        try:
            n = int(bla)
        except:
            print("ERROR in get_nb_points(). Not an integer.")
            n = -1
        return n

    # change number of points
    def set_nb_points(self, nb_points):
        self.write("SENSe{0}:SWEep:POINts {1}".format(self.current_channel, nb_points))


    def set_average(self, nb_averages):
        if nb_averages >= 1:
            self.write("SENSe{0}:AVERage:MODE REDuce".format(self.current_channel))
            self.write("SENSe{0}:AVERage:COUNt {1}".format(self.current_channel, nb_averages))
            self.write("SENSe{0}:SWEep:COUNt {1}".format(self.current_channel, nb_averages))
            self.write("SENSe{0}:AVERage:STATe ON".format(self.current_channel))
        elif nb_averages == 1:
            self.average_off()
        else:
            print("ERROR in set_average: nb_averages should be >1 or =1 to turn off averaging.")

    def average_restart(self):
        self.write("SENSe{0}:AVERage:CLEar".format(self.current_channel))

    def average_off(self):
        self.write("SENSe{0}:AVERage:STATe OFF".format(self.current_channel))
        self.write("SENSe{0}:AVERage:COUNt 1".format(self.current_channel))
        self.write("SENSe{0}:SWEep:COUNt 1".format(self.current_channel))

    # sets spatial smoothing (along freq axis)
    def smoothing(self, aperture):
        if (aperture >= 0.05) and (aperture <=100.00):
            self.write("CALCulate{0}:SMOothing:APERture {1}".format(self.current_channel, aperture))
            self.write("CALCulate{0}:SMOothing ON".format(self.current_channel))
        elif (aperture == 0) | (aperture == False):
            self.write("CALCulate{0}:SMOothing OFF".format(self.current_channel))
        # elif aperture == None:
        #     return self.query("CALCulate{0}:SMOothing?".format(self.current_channel))
        else:
            print("ERROR: error in function smoothing(). Accepted parameters: 0.05<=aperture<=100 or 0 or False to turn off")


    def set_if_bw(self, if_bw):
        self.write("SENSe{0}:BANDwidth {1}".format(self.current_channel, if_bw))
        bla = self.query("SENSe{0}:BANDwidth?".format(self.current_channel))
        try:
            actual_bw = int(bla)
        except:
            print("ERROR in set_if_bw(): value returned by ZNB is not an integer.")
            actual_bw = -1
        return actual_bw


    def get_frequencies(self):
        freqtext = self.query("CALCulate{0}:DATA:STIMulus?".format(self.current_channel))
        return np.array([float(txt) for txt in freqtext.split(',')])

    def get_sdata(self):
        text = self.query("CALCulate{0}:DATA? SDATA".format(self.current_channel))
        values_interlaced = np.array([float(txt) for txt in text.split(',')])
        return values_interlaced[0::2] + 1j*values_interlaced[1::2]

    ### BETA 20190807 JLS -- SEEMS OK
    def get_trace_sdata(self, trace_name):
        self.write("FORMAT REAL,32")
        self.write(f"CALC{self.current_channel}:PAR:SEL '{trace_name}'")
        f = self.visa_instr.query_binary_values(f":CALC{self.current_channel}:DATA:STIM?")
        values_interlaced = np.array(self.visa_instr.query_binary_values(f":CALC{self.current_channel}:DATA? SDAT"))
        # values_interlaced = np.array([float(txt) for txt in text.split(',')])
        z = values_interlaced[0::2] + 1j*values_interlaced[1::2]
        return np.array(f),np.array(z)

    def get_fdata(self):
        text = self.query("CALCulate{0}:DATA? FDATA".format(self.current_channel))
        return np.array([float(txt) for txt in text.split(',')])


    def set_format(self, format):
        accepted = ["MLINear", "MLIN", "MLOGarithmic", "MLOG", "PHASe", "PHAS", "UPHase", "UPH", "IMAGinary", "IMAG", "REAL", "POLar", "POL", "SMITh", "SMIT", "ISMith", "ISM", "SWR", "GDELay", "GDEL", "COMPlex", "COMP", "MAGNitude", "MAGN"]
        accepted_lower_case = [x.lower() for x in accepted]
        if format.lower() in accepted_lower_case:
            self.write("CALCulate{0}:FORMat {1}".format(self.current_channel, format))
        else:
            print("Error: format must be 'MLINear', 'MLOGarithmic', 'PHASe', 'UPHase', 'IMAGinary', 'REAL', 'POLar', 'SMITh', 'ISMith', 'SWR', 'GDELay', 'COMPlex' or'MAGNitude'.")

    # def memorize(self):
    #     self.write("CALCulate{0}:MATH:MEMorize".format(self.current_channel))


    def delete_trace(self, channel_number, measurement_name):
        trace_list = self.list_traces(channel_number)
        if measurement_name in trace_list:
            self.write("CALCulate{0}:PARameter:DELete '{1}'".format(channel_number, measurement_name))
        else:
            print("Cannot delete trace: non-existent trace")

    def delete_all_traces(self, channel_number):
        if channel_number in self.list_channels():
            self.write("CALCulate{0}:PARameter:DELete:CALL".format(channel_number))
        else:
            print("Cannot delete traces: non-existent channel")

    def delete_all_memory(self, channel_number):
        if channel_number in self.list_channels():
            self.write("CALCulate{0}:PARameter:DELete:CMEMory".format(channel_number))
        else:
            print("Cannot delete traces: non-existent channel")

    def delete_really_all_traces(self):
        self.write("CALCulate:PARameter:DELete:ALL")

    def delete_really_all_memory(self):
        self.write("CALCulate:PARameter:DELete:MEMory")



    def set_freq_start_stop(self, fstart, fstop):
        self.write("SENSe{0}:SWEep:TYPE LINear".format(self.current_channel))
        self.write("SENSe{0}:FREQuency:STARt {1}".format(self.current_channel, int(fstart)))
        self.write("SENSe{0}:FREQuency:STOP {1}".format(self.current_channel, int(fstop)))

    def set_freq_center_span(self, fcenter, fspan):
        self.write("SENSe{0}:SWEep:TYPE LINear".format(self.current_channel))
        self.write("SENSe{0}:FREQuency:CENTer {1}".format(self.current_channel, int(fcenter)))
        self.write("SENSe{0}:FREQuency:SPAN {1}".format(self.current_channel, int(fspan)))


    @property
    def sweep_type(self):
        return self.query(f"SENS{self.current_channel}:SWE:TYPE?")

#### added by Leo. use at your own risk. ###

    # sweep type can be one of: LINear | LOGarithmic | POWer | CW | POINt | SEGMent
    def set_sweep_type(self, sweep_type):
        self.write(f'SENS{self.current_channel}:SWE:TYPE {sweep_type}')

    #print current state of VNA
    def get_state(self):
        meta = {
            'center': float(self.query(f'SENS{self.current_channel}:FREQ:CENT?')),
            'span': float(self.query(f'SENS{self.current_channel}:FREQ:SPAN?')),
            'start': float(self.query(f'SENS{self.current_channel}:FREQ:STAR?')),
            'stop': float(self.query(f'SENS{self.current_channel}:FREQ:STOP?')),
            'nb_points': int(self.query(f'SENS{self.current_channel}:SWE:POIN?')),
            'VBW': int(self.query(f'SENS{self.current_channel}:BAND?')),
            'trace_param': self.get_trace_param(),
            'sweep_type': self.query(f'SENS{self.current_channel}:SWE:TYPE?'),
            'power': self.get_power()
            }
        print('\n Current state of VNA is : \n')
        print(f'center is at {meta["center"]*1e-9} GHz')
        print(f'span is of {meta["span"]*1e-6} MHz')
        print(f'start is {meta["start"]*1e-9} GHz')
        print(f'stop is {meta["stop"]*1e-9} GHz')
        print(f'Number of points: {meta["nb_points"]}')
        print(f'Bandwidth of {meta["VBW"]}')
        print(f'Power is: {meta["power"]} dBm')
        print(f'Sweep type is {meta["sweep_type"]}')
        print(f'Trace and channel parameters: {meta["trace_param"]}')
        print()

    def get_trace_param(self):
        return self.query(f'CALC{self.current_channel}:PAR:CAT?')

    #store state of VNA in desired file
    def store_state(self, file):
        #check that file is .ztx
        if file[-4:] == '.znx':
            self.write(f"MMEM:STOR:STATe 1, '{file}'")
            print(f"Saving state to '{file}'")
        else:
            print("Error: file extension should be .znx")

    def load_state(self,file):
        self.write(f"MMEM:LOAD:STATe 1, '{file}'")

#### after this, things are added by JLS again. You should be fine.

    # def get_mem(self, mem_name):
    #     text = self.query("CALCulate{0}:DATA? FMEM".format(self.current_channel))
    #     return np.array([float(txt) for txt in text.split(',')])

    # /!\ DOES NOT KEEP LAST AVERAGING !!! HOLDS WITH ONLY THE LAST SINGLE SWEEP
    def sweep_hold(self):
        # self.write("SENSe{0}:SWEep:MODE HOLD".format(self.current_channel))
        self.write("INITiate{0}:CONTinuous OFF".format(self.current_channel))

    # TO CHECK
    def sweep_single(self):
        # self.write("SENSe{0}:SWEep:MODE SINGle".format(self.current_channel))
        self.write("INITiate{0}:IMMediate".format(self.current_channel))

    def set_trigger_manual(self):
        self.write("TRIGger{0}:SOURce MANual".format(self.current_channel))
        self.write("INITiate{0}:CONTinuous OFF".format(self.current_channel))

    def send_trigger(self):
        # self.write("TRIGger:SCOPe CURRent")
        self.write("TRIGger:SOURce IMMediate")
        self.write("INITiate{0}:IMMediate".format(self.current_channel))
        # self.write("SENSe{0}:SWEep:MODE SINGle".format(channel))

    def free_run(self):
        self.write("INITiate{0}:CONTinuous ON".format(self.current_channel))
        # self.write("TRIGger{0}:SOURce IMMediate".format(self.current_channel))

    # SIMPLISTIC ! TO IMPROVE .. I expected better from mister Smirr du Collège de France
    def running(self):
        if '1' == self.query('*OPC?'):
            return False
        else:
            return True



    def create_channel_and_trace(self, channel_number, measurement_name, S_parameter, window_number):
        used_channels = self.list_channels()
        if not(S_parameter in ["S21", "S11"]):
            print("ERROR: S_parameter for new channel should be S11 or S21 (or udpate the program !)")
            return None
        elif channel_number in used_channels:
            print("Channel already exists. Create another one or delete it first.")
            return None
        else:
            for chan in used_channels:
                used_measurement_names = self.list_traces(chan)
                if measurement_name in used_measurement_names:
                    print("Measurement name already exists. Choose another name or delete the measurement first.")
                    return None
                else:
                    self.write("CALCulate{0}:PARameter:SDEFine '{1}', '{2}'".format(channel_number, measurement_name, S_parameter))
                    self.set_current_channel_and_trace(channel_number, measurement_name)
                    self.sweep_hold()
                    self.set_power(-60)
                    self.set_power_off()
                    self.write("SENSe{0}:SWEep:TIME:AUTO ON".format(self.current_channel))
                    self.set_average(1)
                    self.average_off()
                    self.set_if_bw(1000)
                    self.smoothing(False)
                    self.set_freq_start_stop(2e9, 12e9)
                    self.set_format("MLOGarithmic")
                    self.write("DISPlay:WINDow{0}:STATe ON".format(window_number))
                    self.write("DISPlay:WINDow{0}:TRACe{1}:FEED '{2}'".format(window_number, self.current_trace_number, self.current_measurement_name))
                    return True

    def set_current_channel_and_trace(self, channel_number, measurement_name):
        used_channels = self.list_channels()
        if channel_number not in used_channels:
            print("Channel doesn't exist. Create it first.")
            return None
        else:
            used_measurement_names = self.list_traces(channel_number)
            if measurement_name not in used_measurement_names:
                print("Trace doesn't exists. Create it first.")
                return None
            else:
                self.write("CALCulate{0}:PARameter:SELect '{1}'".format(channel_number, measurement_name))
                self.current_channel = channel_number
                self.current_measurement_name = measurement_name
                self.current_trace_number = self.get_trace_number_from_trace_name(self.current_measurement_name)
                return True

    def delete_channel(self, channel_number):
        self.write("CONFigure:CHANnel{0} OFF".format(channel_number))

    def delete_trace_by_window(self, window_number, measurement_name):
        trace_number = self.get_trace_number_from_trace_name(measurement_name)
        self.write("DISPlay:WINDow{0}:TRACE{1}:DELete".format(window_number, trace_number))

    def list_channels(self):
        bla = self.query("CONFigure:CHANnel:CATalog?")
        blabla = [int(X) for X in bla[1:-1].split(",")[0::2] if X != ""]
        # if blabla == []:
        #     return []
        # else:
        return blabla

    def list_traces(self, channel_number):
        bla = self.query("CONFigure:CHANnel{0}:TRACe:CATalog?".format(channel_number))
        blabla = bla[1:-1]
        if (blabla == "NO CATALOG") or (blabla == ""):
            return []
        else:
            # trace_numbers = [int(X) for X in blabla.split(",")[0::2] if X != ""]
            trace_names   = [X for X in blabla.split(",")[1::2] if X != ""]
            # return trace_numbers, trace_names
            return trace_names

    def get_trace_number_from_trace_name(self, trace_name):
        bla = self.query("CONFigure:TRACe:NAME:ID? '{0}'".format(trace_name))
        try:
            n = int(bla)
        except:
            print("ERROR in get_trace_number_from_trace_name(): not an integer.")
            n = None
        return n

    # TO CHECK
    def scale_auto(self, window_number, trace_number):
        self.write("DISPlay:WINDow{0}:TRACe{1}:Y:SCALe:AUTO ONCE".format(window_number, trace_number))

    def scale_auto_by_trace_name(self, trace_name):
        self.write("DISPlay:WINDow:TRACe:Y:SCALe:AUTO ONCE, '{0}'".format(trace_name))

    # DOESNT WORK
    def screenshot(self, base_filename, filetype):
        if filetype == None:
            filetype = "PNG"
        elif filetype.upper() not in ["BMP", "JPG", "PNG", "PDF", "SVG"]:
            print('ERROR: filetype should be "BMP", "JPG", PNG", "PDF" or "SVG".')
            return None
        self.write("MMEMory:NAME {0}.{1}".format(base_filename,filetype.lower()))
        self.write("HCOPy:DEVice:LANGuage {0}".format(filetype))
        self.write("HCOPy:ITEM:MLISt ON")
        self.write("HCOPy:ITEM:LOGO OFF")
        self.write("HCOPy:ITEM:TIME ON")
        self.write("HCOPy:PAGE:COLor ON")
        self.write("HCOPy:PAGE:WINDow ACTive")
        self.write("HCOPy:DESTination 'MMEMory'")
        self.write("HCOPy")
        print("Screenshot saved to {0}.{1}".format(base_filename,filetype.lower()))

    def get_errors(self):
        output = self.query("SYSTem:ERRor:ALL?")
        return output


    def set_electrical_delay(self, delay):
        self.write("SENSe{0}:CORRection:EDELay2:TIME {1}".format(self.current_channel, delay))


    # ---------- CODE WRITTEN BY LOU 2022/03/15

    @property
    def sweep_time(self):
        self._sweep_time = self.query_ascii_values(f"SENSE{self.current_channel}:SWEEP:TIME?")[0]
        return self._sweep_time

    @property
    def f_center(self):
        self._f_center = self.query_ascii_values(f"SENSE{self.current_channel}:FREQUENCY:CENTER?")[0]
        return self._f_center
    
    @property
    def f_span(self):
        self._f_span = self.query_ascii_values(f"SENSE{self.current_channel}:FREQUENCY:SPAN?")[0]
        return self._f_span

    @property
    def f_start(self):
        self._f_start = self.query_ascii_values(f"SENSE{self.current_channel}:FREQUENCY:START?")[0]
        return self._f_start

    @property
    def f_stop(self):
        self._f_stop = self.query_ascii_values(f"SENSE{self.current_channel}:FREQUENCY:STOP?")[0]
        return self._f_stop

    @property
    def VBW(self):
        self._VBW = self.query_ascii_values(f"SENSE{self.current_channel}:BANDwidth?")[0]
        return self._VBW
    
    @property
    def averaging(self):
        avg_state = bool(self.query_ascii_values(f"SENSE{self.current_channel}:AVERAGE?")[0])
        if avg_state:
                self._averaging = self.query_ascii_values(f"SENSE{self.current_channel}:AVERage:COUNT?")[0]
        else : 
            self._averaging = 1
        return self._averaging

    @property
    def source_freq(self):
        self._source_freq = self.query_ascii_values(f"SOURCE{self.current_channel}:FREQ?")
        return self._source_freq

    @source_freq.setter
    def source_freq(self, freq):
        self.write(f"SOURCE{self.current_channel}:FREQ:FIXED {freq}")

    #getting and setting the number of sweeps a single trig triggers (in frequency mode)
    @property
    def sweep_count(self):
        self.__sweep_count = self.query_ascii_values(f"SENSE{self.current_channel}:SWEEP:COUNT?")[0]
        return self.__sweep_count
    
    @sweep_count.setter
    def sweep_count(self, N):
        self.write(f"SENSE{self.current_channel}:SWEEP:COUNT {N}")

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


    def add_segment(self, n):
        self.write(f"SENSE{self.current_channel}:SEGMENT{n}:ADD")

    def set_segment_freqs(self, segment_number, f_start, f_stop):
        self.write(f"SENSE{self.current_channel}:SEGMENT{segment_number}:FREQUENCY:START {f_start}")
        self.write(f"SENSE{self.current_channel}:SEGMENT{segment_number}:FREQUENCY:STOP {f_stop}")

    def set_segment_points(self, segment_number, nb_points):
        self.write(f"SENSE{self.current_channel}:SEGMENT{segment_number}:SWEEP:POINTS {nb_points}")

    def set_segment_bandwidth(self, segment_number, bwidth):
        self.write(f"SENSE{self.current_channel}:SEGMENT{segment_number}:BWIDTH {bwidth}")

    def get_segment_duration(self, segment_number):
        return self.query(f"SENSE{self.current_channel}:SEGMENT{segment_number}:SWEEP:TIME?")

    def clear_all_segments(self):
        self.write(f'SENSE{self.current_channel}:SEGMENT:DELETE:ALL')

    def set_segment_power(self, segment_number, power):
        self.write(f"SENSE{self.current_channel}:SEGMENT{segment_number}:POWER {power}")

