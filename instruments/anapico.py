# Library for controling Anapico APMS signal generators
# Author: Jean-Loup SMIRR, jean-loup.smirr|at|college-de-france dot fr
# 2019-08, Collège de France

from instruments import instr
import importlib

importlib.reload(instr)

import numpy as np

import inspect
from datetime import datetime
from time import sleep

_DEBUG_ = True
_WARN_ = True
_INFO_ = True

global LAST_ERROR_MESSAGE, IS_ERROR
LAST_ERROR_MESSAGE = ""
IS_ERROR = False



def ERR(*args, **kwarg):
    global LAST_ERROR_MESSAGE, IS_ERROR
    IS_ERROR |= True
    LAST_ERROR_MESSAGE = args
    if _DEBUG_:
        print("ERROR in {0}(): ".format(inspect.stack()[1][3]), end='')
        print(*args, **kwarg)


def WARN(*args, **kwarg):
    if _DEBUG_ or _WARN_:
        print("WARNING in {0}(): ".format(inspect.stack()[1][3]), end='')
        print(*args, **kwarg)


def INFO(*args, **kwarg):
    if _DEBUG_ or _INFO_:
        print("INFO in {0}(): ".format(inspect.stack()[1][3]), end='')
        print(*args, **kwarg)


class AnaPico(instr.Instr):
    def __init__(self, visa_name, visa_library=''):
        super(AnaPico, self).__init__(visa_name, visa_library)
        self.visa_instr.timeout = 5000  # in ms.
        self.visa_instr.read_termination = '\n'
        self.visa_instr.write_termination = '\n'
        self.visa_instr.send_end = True
        self.visa_instr.query_delay = 0.0

        # chunk_size = max data block of response data
        self.visa_instr.chunk_size = 1024

        self.idn = self.get_idn()
        if not self.idn.startswith("AnaPico AG,APMS"):
            ERR("Cannot communicate with AnaPico APMS\n")

        self.available_channels = [1, 2]

        self._current_channel = 1
        self.current_channel = 1


    def write(self, command, debug=False):
        if debug is True:
            print(f"Writing {command}")
            print(f'Before:\n {self.debug_status()}')
        self.visa_instr.write(command)
        if debug is True:
            print(f'After:\n {self.debug_status()}')


    def query(self, command, debug=False):
        if debug is True:
            print(f"Querying {command}")
            print(f'Before:\n {self.debug_status()}')
        self.visa_instr.query(command)
        if debug is True:
            print(f'After:\n {self.debug_status()}')
        return self.visa_instr.query(command)


    @property
    def current_channel(self):
        ch = int(self.query(':SEL?'))
        self._current_channel = ch
        return self._current_channel

    @current_channel.setter
    def current_channel(self, channel):
        if channel in self.available_channels:
            self.write(f':SEL {channel}')
            self._current_channel = channel
            INFO(f'Current channel: {self.current_channel}.')
        else:

            WARN(
                f'Channel {channel} is not available. Choose a integer in {self.available_channels}. Current channel: {self.current_channel}.'
            )

    def clean(self):
        self.cls()
        super(AnaPico, self).clean()

    def debug_status(self):
        stb = self.query('*STB?')  # status byte
        ese = self.query('*ESE?')  # standard event status enable
        esr = self.query('*ESR?')  # standard event status register
        sre = self.query('*SRE?')  # service request enable
        operation_status_condition_register = self.query(':STATUS:OPER:COND?')
        operation_status_event_register = self.query(':STATUS:OPER?')
        questionable_status_condition_register = self.query(':STATUS:QUES:COND?')
        questionable_status_event_register = self.query(':STATUS:QUES?')
        errors = self.query(':SYST:ERR:ALL?')
        out = f'\nstb: {stb} | ese: {ese} | esr: {esr} | sre: {sre}\n'
        out += f'operation status: ( condition: {operation_status_condition_register} | event: {operation_status_event_register} )\n'
        out += f'questionable status: ( condition: {questionable_status_condition_register} | event: {questionable_status_event_register} )\n'
        out += f'errors: {errors}\n'
        return out

    def __del__(self):
        super(AnaPico, self).__del__()

    def __str__(self):
        return self.idn

    def __repr__(self):
        return self.idn

    def reset(self):
        """The Reset (RST) command resets most signal generator functions to factory-defined conditions.
        Each command shows the *RST value if the setting is affected."""
        self.write("*RST")

    def clear_status(self):
        """The Clear Status (CLS) command clears the Status Byte Register, the Data Questionable Event Register, the Standard Event Status Register, the Standard Operation Status Register and any other registers that are summarized in the status byte."""
        self.write("*CLS")

    def is_OPC(self):
        """The Operation Complete (OPC) query returns the ASCII character 1 in the Standard Event Status Register when all pending operations have finished."""
        return self.query("*OPC?")

    def set_OPC(self):
        """The Operation Complete (OPC) command sets bit 0 in the Standard Event Status Register when all pending operations have finished."""
        self.write("*OPC")

    # OK
    def errors_get_last(self):
        return self.query("STAT:ERR?")

    def errors_get_all(self):
        errors = [self.errors_get_last()]
        while errors[-1] != '0,"No error"':
            errors += self.errors_get_last()
            return errors

    # dummy function for errors_get_all()
    def errors_clear(self):
        return self.errors_get_all()

    def output_on(self):
        self.write(f":OUTP{self.current_channel} 1")

    def output_off(self):
        self.write(f":OUTP{self.current_channel} 0")

    def output(self, val=None):
        if val is None:
            out = self.query(f":OUTP{self.current_channel}?")
            if out == "1":
                return True
            if out == "0":
                return False
            else:
                ERR("Response to OUTP? is neither 0 nor 1 !")
        elif val is True:
            self.output_on()
        elif val is False:
            self.output_off()
        else:
            ERR("parameter for output() must be None (query), True or False (set)")

    def unit_power(self, unit=None):
        possible_units = ["W", "V", "DBM", "DB"]
        if unit is None:
            return self.query(":UNIT:POW?")
        elif unit.upper() in possible_units:
            self.write(f":UNIT:POW {unit}".format(unit=unit.upper()))
        else:
            ERR(f'unit must be {possible_units} or None for query')

    def power(self, power=None, unit=None):
        possible_units = ["W", "V", "DBM", "DB"]
        # powmaxdBm = 15
        # powmindBm = -50
        if power is None:
            return float(self.query(":POW?"))
        elif isinstance(power, float) or isinstance(power, int):
            if unit is None:
                u = self.unit_power()
                WARN(f"Using default unit for power: {u}")
                self.write(f":POW {power}")
            elif unit.upper() in possible_units:
                self.write(f":POW {power}{unit.upper()}")
            else:
                ERR(f'Unit must be None or {possible_units}')
        else:
            ERR('Power must be None, a float or an int')

    def freq_mode(self, mode=None):
        possible_freq_modes = [
            "FIX",
            "FIXED",
            "CW",
            "SWE",
            "SWEEP",
            "LIST",
            "CHIR",
            "CHIRP",
        ]
        if mode is None:
            return self.query(":FREQ:MODE?")
        elif mode in possible_freq_modes:
            self.write(f":FREQ:MODE {mode}")
        else:
            ERR(f'mode must be None, or {possible_freq_modes}')

    def power_mode(self, mode=None):
        possible_power_modes = ["FIX", "FIXED", "SWE", "SWEEP", "LIST"]
        if mode is None:
            return self.query(":POW:MODE?")
        elif mode in possible_power_modes:
            self.write(f":POW:MODE {mode}")
        else:
            ERR(f'mode must be None, or {possible_power_modes}')

    def freq(self, freq=None):
        fmin = 300.0e3
        fmax = 42.0e9
        if freq is None:
            return float(self.query(":FREQ:FIX?"))
        elif isinstance(freq, float) or isinstance(freq, int):
            if fmin <= freq <= fmax:
                self.write(f":FREQ:FIX {freq}")
            else:
                ERR(f"Freq must be <={fmax} and >={fmin}")
        else:
            ERR('Freq must be None, a float or an int')

    def modulation_on(self):
        self.write(":MOD 1")

    def modulation_off(self):
        self.write(":MOD 0")

    def modulation(self, val=None):
        if val is None:
            out = self.query(":MOD?")
            if out == "1":
                return True
            if out == "0":
                return False
            else:
                ERR("Response to MOD? is neither ON nor OFF !")
        elif val is True:
            self.modulation_on()
        elif val is False:
            self.modulation_off()
        else:
            ERR("parameter for modulation() must be None, True or False")

    def alc_level(self, level=None):
        if level is None:
            return float(self.query(":POW:ALC:LEV?"))
        elif isinstance(level, float) or isinstance(level, int):
            if (level >= -20) & (level <= 14):
                self.write(f":POW:ALC:LEV {level}DB")
            else:
                ERR("ALC level must be <=14dBm and >=-20dBm")
        else:
            ERR('ALC level must be None, a float or an int')

    def alc(self, val=None):
        if val is None:
            out = self.query(":POW:ALC?")
            if out == "1":
                return True
            if out == "0":
                return False
            else:
                ERR("Response to :POW:ALC? is neither 1 nor 0 !")
        elif val is True:
            self.write(":POW:ALC 1")
        elif val is False:
            self.write(":POW:ALC 0")
        else:
            ERR("Parameter for alc() must be None, True or False")

    def attenuator(self, level=None):
        if level is None:
            return float(self.query(":POW:ATT?"))
        elif isinstance(level, float) or isinstance(level, int):
            if level in [0, 5, 15, 25, 35, 45, 55, 65, 75, 85, 95, 105, 115]:
                self.write(f":POW:ATT {level}DB")
            else:
                ERR("Attenuator level must be 0,5,15,25,...,115")
        else:
            ERR('ALC level must be None, a float or an int')
        if not self.att_hold():
            WARN(
                'Attenuator level changed but not effective because ATT_HOLD is not active.'
            )

    def att_hold(self, val=None):
        if val is None:
            out = self.query(":POW:ATT:AUTO?")
            if out == "0":
                return True
            if out == "1":
                return False
            else:
                ERR("Response to :POW:ATT::AUTO? is neither 0 nor 1 !")
        elif val is True:
            self.write(":POW:ATT:AUTO 0")
        elif val is False:
            self.write(":POW:ATT:AUTO 1")
        else:
            ERR("Parameter for att_hold() must be None, True or False")

    def flatness_correction(self, val=None):
        ''' Enables, disables, or queries the state of the flatness correction
            Uses the current data in memory: change with flatness_correction_upload() function
        '''
        if val is None:
            out = self.query(f":CORR?")
            if out == "1":
                return True
            if out == "0":
                return False
            else:
                ERR("Response to :CORR? is neither 0 nor 1 !")
        elif val is True:
            self.write(':CORR 1')
        elif val is False:
            self.write(':CORR 0')
        else:
            ERR(
                "parameter for flatness_correction() must be None (query), True or False (set)"
            )

    def flatness_correction_load(self, preset_name):
        self.write(f':CORR:FLAT:LOAD "{preset_name}"')

    def flatness_correction_upload(self, freq_list, amplitude_list, preset_name):
        ''' uploads and stores a flatness correction profile
            freq: 1D array of frequency values in Hz
            amplitude: 1D array of relative amplitudes (e.g. 1=0dB, 0.5=-6.02dB)
            /!\ accuracy : 1 MHz, 0.01 dB to reduce string length hence upload time
        '''

        # save a backup of the previous data to be erased
        self.write(f':CORR:FLAT:STOR "backup_flatcorr"')
        # erase the flatness correction
        self.write(':CORR:FLAT:PRES')

        # upload the flatness corretion data
        sleep_time = 0.01
        for (f, a) in zip(freq_list, amplitude_list):
            freq_MHz = int(np.round(f / 1e6))
            power_dB = 10 * np.log10(a ** 2)
            self.write(":CORR:FLAT:PAIR {:d}E6,{:+2.2f}DB".format(freq_MHz, power_dB))
            INFO("{:5d} MHz - {:+2.2f} dB... ".format(freq_MHz, power_dB), end="")
            t0 = datetime.now()
            ready = False
            while not ready:
                sleep(sleep_time)
                ready = bool(self.query("*OPC?"))
            dt = datetime.now() - t0
            INFO("OK ({:4d}ms)".format(int(dt.microseconds / 1000)))

        self.write(f':CORR:FLAT:STOR "{preset_name}"')
        self.write(f':CORR:FLAT:LOAD "{preset_name}"')

    def trigger(self):
        self.write('*TRG')
