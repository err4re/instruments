# Library for controling Yokogawa DL750 Oscilloscope
# Author: Jean-Loup SMIRR, jean-loup.smirr|at|college-de-france dot fr
# 2016-07, Collège de France

import instruments.instr as instr
import importlib
importlib.reload(instr)
import visa
import time
import numpy as np
import matplotlib.pyplot as plt


RETURN_ERROR = False
RETURN_NO_ERROR = None
FORMAT_WORD = "16bit"
FORMAT_BYTE = "8bit"
FORMAT_ASCII = "text"
SMALL_DELAY = 0.1
# [1,2,3,4,5,6,7,8,9,10,11,12,13,14]

_DEBUG_ = True
_WARN_ = True
_INFO_ = True

global LAST_ERROR_MESSAGE, IS_ERROR
LAST_ERROR_MESSAGE = ""
IS_ERROR = False

import inspect

def ERR(arg):
    global LAST_ERROR_MESSAGE, IS_ERROR
    IS_ERROR |= True
    LAST_ERROR_MESSAGE = arg
    if _DEBUG_:
        print("ERROR in {0}(): ".format(inspect.stack()[1][3]) + arg)


def WARN(arg):
    if _DEBUG_ or _WARN_:
        print("WARNING in {0}(): ".format(inspect.stack()[1][3]) + arg)


def INFO(arg):
    if _DEBUG_ or _INFO_:
        print("INFO in {0}(): ".format(inspect.stack()[1][3]) + arg)




class Yoko750(instr.Instr):
    def __init__(
        self, visa_name, visa_library='', installed_channels=[1, 2, 3, 4, 9, 10, 11, 12]
    ):
        super(Yoko750, self).__init__(visa_name, visa_library)
        self.visa_instr.timeout = (
            1000  # in ms (tested with 100 ms, works with chunk size of 2*10010+9+2)
        )
        self.visa_instr.read_termination = '\n'
        self.visa_instr.write_termination = '\n'
        self.visa_instr.send_end = True
        self.visa_instr.query_delay = (
            1.0e-6  # in s (tested with 1.e-9 (1ns) and it works)
        )

        # chunk_size = max data block of response data: 1 to 2004000 bytes cf. yoko User Manual page App-4
        # don't go below 2*10010+9+2 for arecord length of 1e4 (=10010) plus 11 bytes of headers
        # 2004000 is good for record length 1e6 in one read (50s in binary)
        self.visa_instr.chunk_size = 2 * 10010 + 9 + 2  # 2004000

        # For RS232
        self.visa_instr.baud_rate = 19200
        self.visa_instr.parity = (
            visa.constants.VI_ASRL_PAR_NONE
        )  # parity=none define in pyvisa as VI_ASRL_PAR_NONE which is defined = 0
        self.visa_instr.stop_bits = (
            visa.constants.VI_ASRL_STOP_ONE
        )  # 1 bit = value 10, 1.5bit=15, 2bit=20
        self.visa_instr.flow_control = visa.constants.VI_ASRL_FLOW_RTS_CTS
        # END For RS232

        # self.write("COMM:REM 1")

        self.idn = self.get_idn()
        if not self.idn.startswith("YOKOGAWA"):
            ERR(f"Cannot communicate with Yokogawa DL750 : *IDN?={self.idn}\n")
        else:
            INFO("Communication OK")
            INFO("Disabling headers")
            self.write("COMM:HEAD 0")

        # Yoko750 general configuration
        self.hardware_channels = installed_channels
        INFO(
            "Installed channels: {}. Use optional parameter installed_channels=[1,2,...] to change.".format(
                installed_channels
            )
        )
        self.possible_timebases = [
            5,
            10,
            20,
            50,
            100,
            200,
            500,
            1e3,
            2e3,
            5e3,
            10e3,
            20e3,
            50e3,
            100e3,
            200e3,
            500e3,
            1e6,
            2e6,
            5e6,
            10e6,
        ]  # Unit: Samples/s
        self.possible_record_lengths = [
            1e3,
            2.5e3,
            5e3,
            10e3,
            25e3,
            50e3,
            100e3,
            250e3,
            500e3,
            1e6,
            2.5e6,
            5e6,
            10e6,
            25e6,
            50e6,
            100e6,
            250e6,
            500e6,
            1e9,
        ]  # Unit : Total Samples

        class Trace(object):
            def __init__(self):
                self.number = 0
                self.label = "CH{0}".format(self.number)
                self.unit = "V"
                self.gain = 1.0
                self.active = False
                self.offset = 0
                self.bandwidth = 0  # full bandwidth = 0
                self.invert = False
                self.ac_coupled = False
                self.x = np.array([])
                self.y = np.array([])
                self.yrange = 0  # Volt/div
                self.N = 0
                self.module = "unknown"
                self.probe = 1
                self.averaging = 1
                self.series = ""

            def __repr__(self):
                return "<Trace({0})>".format(self.__dict__)

            def __str__(self):
                return self.label

            def __del__(self):
                pass

        self.errors_clear()

        self.calibration_auto = False
        # self.calibration_execute()

        self._waveformat = 'TEXT'

        self.traces = [Trace() for i in range(max(self.hardware_channels))]
        for i in range(len(self.traces)):
            self.traces[i].number = i + 1
            self.traces[i].label = "CH{0}".format(self.traces[i].number)

        self.active_traces = []
        self.get_trace_list()

        self.trace_current = None
        self.current_trace()

    def clean(self):
        # self.write("COMMUNICATE:HEADER ON")
        INFO("NOT Reactivating headers")
        self.remote_mode = False
        super(Yoko750, self).clean()

    def __del__(self):
        super(Yoko750, self).__del__()

    def __str__(self):
        return self.idn

    def __repr__(self):
        return self.idn

    @property
    def calibration_auto(self):
        out = self.query("CAL?")
        if out == "AUTO":
            return True
        elif out == "OFF":
            return False
        else:
            ERR('"CAL?" did not return "AUTO" nor "OFF". This should not happen.')
            return None

    @calibration_auto.setter
    def calibration_auto(self, mode):
        if mode is True:
            self.write("CAL:MODE AUTO")
        elif mode is False:
            self.write("CAL:MODE OFF")
        else:
            ERR("Parameter must be True or False")

    def calibration_execute(self):
        self.write("CAL:EXEC")

    @property
    def remote_mode(self):
        if self.visa_instr.interface_type == visa.constants.InterfaceType.gpib:
            return self.visa_instr.remote_enabled == visa.constants.LineState.asserted
        else:
            return self.query("COMM:REM?")

    @remote_mode.setter
    def remote_mode(self, mode):
        if self.visa_instr.interface_type == visa.constants.InterfaceType.gpib:
            if mode is True:
                self.visa_instr.control_ren(visa.constants.LineState.asserted)
            elif mode is False:
                self.visa_instr.control_ren(visa.constants.LineState.unasserted)
            else:
                ERR("Parameter must be True or False")
        else:
            if mode is True:
                self.write("COMM:REM 1")
            elif mode is False:
                self.write("COMM:REM 0")
            else:
                ERR("Parameter must be True or False")

    # STATUS BITS OF THE STANDARD EVENT REGISTER
    SER_OPERATION_COMPLETE = 1
    SER_REQUEST_CONTROL = 2  # NOT USED BY YOKO DL750
    SER_QUERY_ERROR = 4
    SER_DEVICE_DEPENDENT_ERROR = 8  # NOT USED BY YOKO DL750
    SER_EXECUTION_ERROR = 16
    SER_COMMAND_ERROR = 32
    SER_USER_REQUEST = 64  # NOT USED BY YOKO DL750
    SER_POWER_ON = 128

    def _standard_event_register(self):
        return self.query_ascii_values("STAT:COND?")[0]

    def operation_complete(self):
        """Returns the truthness of the OPC bit in the Standard Event Register
        """
        bit = 0  # OPC bit
        return 2 ** bit & self._standard_event_register()

    def query_error(self):
        """Returns the truthness of the QYE bit in the Standard Event Register
        """
        bit = 2  # QYE bit
        return 2 ** bit & self._standard_event_register()

    def execution_error(self):
        """Returns the truthness of the EXE bit in the Standard Event Register
        """
        bit = 4  # EXE bit
        return 2 ** bit & self._standard_event_register()

    def command_error(self):
        """Returns the truthness of the CME bit in the Standard Event Register
        """
        bit = 5  # CME bit
        return 2 ** bit & self._standard_event_register()

    def reset(self):
        """Collectively initializes the current settings of the following command groups. ACCumulate, ACQuire, CHANnel<x>, TIMebase, TRIGger
        """
        self.write("*RST")

    def clear_status(self):
        """Clears the standard event register, extended event register, and error queue.
        """
        self.write("*CLS")

    def is_OPC(self):
        """If *OPC? is transmitted and the specified overlap command is completed, ASCII code "1" is returned.
        """
        return self.query("*OPC?")

    def set_OPC(self):
        """Sets a “1” to bit 0 (OPC bit) of the standard event register bit upon the completion of the specified overlap command.
        """
        self.write("*OPC")

    def running(self, yes=None):
        """ Queries/changes the acquisition status:
            - with no argument: returns True if acquisition is in process, returns False otherwise
            - with argument True: starts acquisition. Equivalent to calling function start()
            - with argument False: stops acquisition. Equivalent to calling function stop()
        """
        if yes is None:
            try:
                if 1 & int(self.query("STAT:COND?")):
                    return True
                else:
                    return False
            except:  ###!!!!!!!!!!!!!!!!!!!!!!!! TEMPORARY !!!!!!!!!!!!!!!!!!!!
                return True
        elif yes:
            return self.start()
        elif not yes:
            return self.stop()
        else:
            ERR("Argument must be None (for query), True or False.")
            return RETURN_ERROR

    # --------------
    # MISC
    # --------------
    # draft
    # --------------

    # NOT WORKING
    def snapshot(self, filename=None):
        import io

        self.write('IMAG:FORM PNG')
        self.write('IMAG:SEND?')
        termination = self.visa_instr.read_termination
        self.visa_instr.read_termination = None
        bindata = self.visa_instr.read_raw()
        self.visa_instr.read_termination = termination
        data = io.BytesIO()
        with data as tmp:
            tmp.write(bindata[8:])
            tmp.flush()
            img = plt.imread(tmp)
        if filename is not None:
            with open(filename, 'bw+') as f:
                f.write(bindata[8:])
        return img

    # TODO
    def press_esc(self):
        pass

    # --------------
    # END - MISC
    # --------------

    # --------------
    # ACQUIRE group
    # --------------
    # fully implemented except BoxAverage and Envelope modes
    # --------------

    def record_length(self, value=None):
        """ Query or set the number of points of an acquisition.
        * if argument is ``None`` (default), query the current setting
        * if argument is a valid integer, changes the number of points. Possible values are listed in class parameter ``possible_record_lengths``
        """
        if value is None:
            return self.query_ascii_values("ACQ:RLEN?")[0]
        elif value in self.possible_record_lengths:
            self.write("ACQ:RLEN {0}".format(value))
            return RETURN_NO_ERROR
        else:
            ERR("Possible record lengths are {0}".format(self.possible_record_lengths))
            return RETURN_ERROR

    def clock_external(self, yes=None):
        """ Query (without argument) or set the clock type: True for ``EXTernal``, False for ``INTernal``.
        """
        if yes is None:
            if self.query("ACQ:CLOC?").upper().startswith("EXT"):
                return True
            else:
                return False
        elif yes:
            self.write("ACQ:CLOC EXT")
            return RETURN_NO_ERROR
        elif not yes:
            self.write("ACQ:CLOC INT")
            return RETURN_NO_ERROR
        else:
            ERR(
                "Error in timebase_source_is_internal(): argument must be None, True or False."
            )
            return RETURN_ERROR

    # TODO check if BAV and ENV also use averaging count
    # TODO 2: with average 0 (infinite), set the weight too !
    def averaging(self, number=None):
        """ Query or set the averaging status.
        * if argument is ``None`` (default), query the current setting. Return values: 0 for 'INFinity', 1 for no averaging, 2 to 65537 for finite averaging.
        * if argument is an integer, change the averaging type. See line above for allowed values. Finite averaging is rounded to the lower power of 2.
        """
        if number is None:
            if self.acq_mode() == "AVER":
                out = self.query("ACQ:AVER:COUN?")
                if out in [str(n) for n in range(2, 65537)]:
                    return int(out)
                else:
                    return 0  # COUNt? is either 2 to 65536 or 'INF', which is represented by 0 in this module (for averaging at least!)
            elif self.acq_mode() == "NORM":
                return 1
            else:
                ERR(
                    "Box averaging and Envelope acquisition modes not implemented yet."
                )  # TODO
                return RETURN_ERROR
        elif number == 1:
            self.acq_mode("NORM")
            return RETURN_NO_ERROR
        elif number == 0:
            if self.trigger_mode() in ["SING", "NSIN", "LOG"]:
                ERR(
                    "Cannot use averaging when trigger is set to 'SINGle', 'NSINgle' or 'LOG'. Call trigger_mode() with argument 'AUTO', 'ALEVel' or 'NORMal' first."
                )
                return RETURN_ERROR
            else:
                self.acq_mode("AVER")
                self.write("ACQ:AVER:COUN INF")
                return RETURN_NO_ERROR
        elif number >= 2 and number <= 65536:
            if self.trigger_mode() in ["SING", "NSIN", "LOG"]:
                ERR(
                    "Cannot use averaging when trigger is set to 'SINGle', 'NSINgle' or 'LOG'. Call trigger_mode() with argument 'AUTO', 'ALEVel' or 'NORMal' first."
                )
                return RETURN_ERROR
            else:
                self.acq_mode("AVER")
                rounded_number = 2 ** int(np.log2(number))
                if rounded_number != number:
                    WARN(
                        "Number of averages requested ({0}) rounded to the lower power of 2: {1}".format(
                            number, rounded_number
                        )
                    )
                self.write("ACQ:AVER:COUN {0}".format(rounded_number))
                return RETURN_NO_ERROR
        else:
            ERR(
                "Error in averaging(): argument is None for query, 1 for no averaging, 0 for infinity, or 2 to 65536 (rounded to the lower power of 2)"
            )
            return RETURN_ERROR

    # Use averaging() instead
    # def set_acq_mode_normal(self):
    #   self.write("ACQ:MODE NORM")
    #   return RETURN_NO_ERROR

    # Use averaging() instead (for AVER mode at least)
    def acq_mode(self, mode=None):
        """ Query or set the acquisition mode.
        RECOMMENDATION: Use ``averaging()`` function instead if ``BAV`` or ``ENV`` modes are not used.
        * if argument is ``None`` (default), query the current setting. Return values: ``NORM``, ``AVER``, ``BAV``, ``ENV``.
        * if argument is ``NORM``, ``AVER``, ``BAV`` or ``ENV``, change the averaging type accordingly.
        """
        if mode is None:
            return self.query("ACQ:MODE?")
        elif mode.upper().startswith("NORM"):
            self.write("ACQ:MODE NORM")
            return RETURN_NO_ERROR
        elif mode.upper().startswith("AVER"):
            self.write("ACQ:MODE AVER")
            return RETURN_NO_ERROR
        elif mode.upper().startswith("BAV"):
            self.write("ACQ:MODE BAV")
            return RETURN_NO_ERROR
        elif mode.upper().startswith("ENV"):
            self.write("ACQ:MODE ENV")
            return RETURN_NO_ERROR
        else:
            ERR(
                "Acquisistion mode must be 'NORMal', 'AVERage', 'BAVerage' or 'ENVelope' (short or long form, case-insensitive)."
            )
            return RETURN_ERROR

    # --------------
    # END - ACQUIRE group
    # --------------

    # --------------
    # TIMEBASE group
    # --------------
    # fully implemented
    # --------------

    def timebase(self, value=None):
        """ Query (without argument) or set the timebase in Hz. Possible values are listed in property ``possible_timebases``
        """
        if value is None:
            return self.query_ascii_values("TIM:SRAT?")[0]
        elif value in self.possible_timebases:
            self.write("TIM:SRAT {0}".format(value))
            return RETURN_NO_ERROR
        else:
            ERR("Possible sample rate values are {0}".format(self.possible_timebases))
            return RETURN_ERROR

    def timebase_source_is_internal(self, yes=None):
        """ Query (without argument) or set the source of the timebase. Possible values are ``True`` for internal and ``False`` for external.
        """
        if yes is None:
            if self.query("TIM:SOUR?").upper().startswith("INT"):
                return True
            else:
                return False
        elif yes:
            self.write("TIM:SOUR INT")
            return RETURN_NO_ERROR
        elif not yes:
            self.write("TIM:SOUR EXT")
            return RETURN_NO_ERROR
        else:
            ERR(
                "Error in timebase_source_is_internal(): argument must be None, True or False."
            )
            return RETURN_ERROR

    # TODO : check allowed values
    def time_per_div(self, value=None):
        """ Query (without argument) or set the time per division. Possible values are from 500e-9 to 1800.
        """
        if value is None:
            return self.query_ascii_values("TIM:TDIV?")[0]
        elif value >= 500e-9 and value <= 1800:
            self.write("TIM:TDIV {0}".format(value))
            return RETURN_NO_ERROR
        else:
            ERR("Possible time per division is from 500e-9 to 1800.")
            return RETURN_ERROR

    # --------------
    # END - TIMEBASE group
    # --------------

    # TODO : check allowed values
    def volt_per_div(self, numtrace=None, value=None):
        """ Query (without argument) or set the time per division. Possible values are from 500e-9 to 1800.
        """
        if numtrace is None:
            tr = self.current_trace()
        elif isinstance(numtrace, int) and numtrace in self.hardware_channels:
            tr = numtrace
        else:
            ERR(
                "numtrace argument must be None for current trace or a number in {0}".format(
                    self.hardware_channels
                )
            )
            return RETURN_ERROR

        if value is None:
            return self.query_ascii_values("CHAN{0}:VDIV?".format(tr))[0]
        elif value >= 0.1e-3 and value <= 200:
            self.write("CHAN{0}:VDIV {1}".format(tr, value))
            return RETURN_NO_ERROR
        else:
            ERR("Possible volt per division from 0.1e-3 to 200")
            return RETURN_ERROR

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

    @property
    def waveformat(self):
        out = self.query('WAV:FORM?')
        if out.upper().startswith(FORMAT_WORD.upper()):
            self._waveformat = FORMAT_WORD
        elif out.upper().startswith(FORMAT_BYTE.upper()):
            self._waveformat = FORMAT_BYTE
        elif out.upper().startswith(FORMAT_ASCII.upper()):
            self._waveformat = FORMAT_ASCII
        return self._waveformat

    @waveformat.setter
    def waveformat(self, formattype):
        if (
            formattype.upper() == FORMAT_ASCII.upper()
            and self._waveformat != FORMAT_ASCII
        ):
            self.write('WAV:FORM ASC')
            self._waveformat == FORMAT_ASCII
        elif (
            formattype.upper() == FORMAT_BYTE.upper()
            and self._waveformat != FORMAT_BYTE
        ):
            self.write('WAV:FORM BYTE')
            assert self.query("WAV:BITS?") == '8'
            self.write("WAV:BYTE LSBFIRST")
            self._waveformat == FORMAT_BYTE
        elif (
            formattype.upper() == FORMAT_WORD.upper()
            and self._waveformat != FORMAT_WORD
        ):
            self.write('WAV:FORM WORD')
            assert self.query("WAV:BITS?") == '16'
            self.write("WAV:BYTE LSBFIRST")
            self._waveformat == FORMAT_WORD
        else:
            ERR(
                f"Parameter must be '{FORMAT_ASCII}' (ASCII), '{FORMAT_BYTE}' (binary 8 bit) or '{FORMAT_WORD}' (binary 16 bit, LSB)"
            )

    # OK but should do a waveformat(self,formattype=None)
    # def get_format(self):
    #   return self.waveformat

    # # OK
    # def set_format_ascii(self):
    #   self.write('WAV:FORM ASC')
    #   #self._waveformat = FORMAT_ASCII

    # # OK
    # def set_format_binary8bit(self):
    #   self.write('WAV:FORM BYTE')
    #   assert self.query("WAV:BITS?") == '8'
    #   #self._waveformat = FORMAT_BYTE
    #   self.write("WAV:BYTE LSBFIRST")

    # # OK
    # def set_format_binary16bit(self):
    #   self.write('WAV:FORM WORD')
    #   assert self.query("WAV:BITS?") == '16'
    #   #self._waveformat = FORMAT_WORD
    #   self.write("WAV:BYTE LSBFIRST")

    # OK
    def start(self):
        if len(self.active_traces) != 0:
            self.write("STAR")
        else:
            WARN("Couldn't start acquisition: no active trace")
            return RETURN_ERROR

    # OK
    def stop(self):
        self.write("STOP")

    # OK
    def trig(self):
        self.write("MTR")

    # OK
    def trigger_position(self, position=None):
        if position is None:
            return float(self.query("TRIG:POS?"))
        elif position >= 0.0 and position <= 100.0:
            self.write(f"TRIG:POS {position:.3f}")
        else:
            ERR("position must be between 0 and 100 (in %).")

    def trigger_source(self, source=None):
        if source is None:
            tmp = self.query("TRIG:SIMP:SOUR?")
            if tmp in [str(x) for x in self.hardware_channels]:
                return int(tmp)
            else:
                return tmp.upper()
        elif isinstance(source, str) and len(source) == 3:
            if source.upper().startswith("EXT"):
                self.write("TRIG:SIMP:SOUR EXT")
                return RETURN_NO_ERROR
        elif isinstance(source, str) and len(source) >= 4:
            if source.upper().startswith("EXT"):
                self.write("TRIG:SIMP:SOUR EXT")
                return RETURN_NO_ERROR
            if source.upper().startswith("LINE"):
                self.write("TRIG:SIMP:SOUR LINE")
                return RETURN_NO_ERROR
            elif source.upper().startswith("TIME"):
                self.write("TRIG:SIMP:SOUR TIME")
                return RETURN_NO_ERROR
            elif source.upper().startswith("PODA"):
                self.write("TRIG:SIMP:SOUR PODA")
                return RETURN_NO_ERROR
            elif source.upper().startswith("PODB"):
                self.write("TRIG:SIMP:SOUR PODB")
                return RETURN_NO_ERROR
        elif isinstance(source, int):
            if source in self.hardware_channels:
                self.write("TRIG:SIMP:SOUR {0}".format(source))
                return RETURN_NO_ERROR
            else:
                ERR(
                    "Trigger source must be a valid hardware channel or 'EXTernal', 'LINE', 'TIME', 'PODA' or PODB' (short or long form, case-insensitive)."
                )
                return RETURN_ERROR
        else:
            ERR(
                "Trigger source must be a valid hardware channel or 'EXTernal', 'LINE', 'TIME', 'PODA' or PODB' (short or long form, case-insensitive)."
            )
            return RETURN_ERROR

    def trigger_mode(self, mode=None):
        if mode is None:
            return self.query("TRIG:MODE?").upper()
        elif isinstance(mode, str):
            if mode.upper().startswith("REP"):
                self.write("TRIG:MODE REP")
                return RETURN_NO_ERROR
            if mode.upper().startswith("AUTO"):
                self.write("TRIG:MODE AUTO")
                return RETURN_NO_ERROR
            elif mode.upper().startswith("ALEV"):
                self.write("TRIG:MODE ALEV")
                return RETURN_NO_ERROR
            elif mode.upper().startswith("NORM"):
                self.write("TRIG:MODE NORM")
                return RETURN_NO_ERROR
            elif mode.upper().startswith("SING"):
                self.write("TRIG:MODE SING")
                return RETURN_NO_ERROR
            elif mode.upper().startswith("NSIN"):
                self.write("TRIG:MODE NSIN")
                return RETURN_NO_ERROR
        else:
            ERR(
                "Trigger mode must be 'AUTO', 'ALEVel', 'NORMal', 'SINGle' or 'NSINgle' (short or long form, case-insensitive)."
            )
            return RETURN_ERROR

    def trigger_level(self, level=None, slope_down=False):
        trig_source = self.trigger_source()
        if level is None:
            return self.query_ascii_values("TRIG:LEV?")[0]
        elif isinstance(trig_source, str):
            if not trig_source.upper().startswith(
                ('EXT', 'LINE', 'TIME', 'LOGICA', 'LOGICB')
            ):
                self.write("TRIG:POS {0}".format(level))
            else:
                ERR(
                    "level cannot be adjusted with trig mode 'EXTernal','LINE','TIME',LOGICA' or 'LOGICB'"
                )
        elif isinstance(trig_source, int):
            self.write("TRIG:POS {0}".format(level))
        else:
            ERR(
                "level cannot be adjusted with trig mode 'EXTernal','LINE','TIME',LOGICA' or 'LOGICB'"
            )
        if slope_down:
            self.write("TRIG:SLOP FALL")
        else:
            self.write("TRIG:SLOP RISE")

    def XY(self, XYmode=None, numdisplay=1, xaxis=11):
        if XYmode is None:
            return self.query(f"XY{numdisplay}?")
        elif XYmode:
            self.write(f"XY{numdisplay}:MODE XY")
            self.write(f"XY{numdisplay}:XAX SING")
            self.write(f"XY{numdisplay}:XTR {xaxis}")
            return RETURN_NO_ERROR
        elif not XYmode:
            self.write(f"XY{numdisplay}:MODE TY")
            return RETURN_NO_ERROR
        else:
            ERR(
                "Argument must be None (for query), True or False. Parameters: numdisplay=1,2,3 or 4. xaxis=? where ? is channel number"
            )
            return RETURN_ERROR

    def traces_off(self, traces=None):
        """Disable the traces in argument:
        - if argument is None: disable all traces
        - if argument is an integer, disable that trace number
        - if argument is a list (ex: [1,3,4]), disable these traces
        """
        out = RETURN_NO_ERROR
        if traces is None:
            self.traces_off(self.active_traces)
        else:
            if not isinstance(traces, list):
                if isinstance(traces, int):
                    traces = [traces]
                else:
                    ERR(
                        "Example of possible arguments: None, 1, or [1,2,...] (None, int, or list of int)"
                    )
                    out = RETURN_ERROR
            for tr in list(traces):
                if isinstance(tr, int):
                    if tr in self.hardware_channels:
                        if tr in self.active_traces:
                            self.write("CHAN{0}:DISP OFF".format(tr))
                            self.active_traces.remove(tr)
                            self.traces[tr - 1].active = False
                            INFO("Trace {0} disabled.".format(tr))
                        else:
                            WARN("Trace {0} already OFF.".format(tr))
                    else:
                        ERR(
                            "Trace {0} is not in the list of harware channels.".format(
                                tr
                            )
                        )
                        out = RETURN_ERROR
                else:
                    ERR(
                        "Example of possible arguments: None, 1, or [1,2,...] (None, int, or list of int)"
                    )
                    out = RETURN_ERROR
        return out

    def traces_on(self, traces=None):
        """Enable the traces in argument:
        - if argument is None: enable all traces
        - if argument is an integer, enable that trace number
        - if argument is a list (ex: [1,3,4]), enable these traces
        """
        out = RETURN_NO_ERROR
        if traces is None:
            self.traces_on(
                [t for t in self.hardware_channels if t not in self.active_traces]
            )
        else:
            if not isinstance(traces, list):
                if isinstance(traces, int):
                    traces = [traces]
                else:
                    ERR(
                        "Example of possible arguments: None, 1, or [1,2,...] (None, int, or list of int)"
                    )
                    out = RETURN_ERROR
            for tr in list(traces):
                if isinstance(tr, int):
                    if tr in self.hardware_channels:
                        if tr in self.active_traces:
                            WARN("Trace {0} already ON.".format(tr))
                        else:
                            self.write("CHAN{0}:DISP ON".format(tr))
                            self.active_traces += [tr]
                            # self.active_traces.sort()
                            self.traces[tr - 1].active = True
                            INFO("Trace {0} enabled.".format(tr))
                    else:
                        ERR(
                            "Trace {0} is not in the list of harware channels.".format(
                                tr
                            )
                        )
                        out = RETURN_ERROR
                else:
                    ERR(
                        "Example of possible arguments: None, 1, or [1,2,...] (None, int, or list of int)"
                    )
                    out = RETURN_ERROR
        return out

    def current_trace(self, numtrace=None):
        """ Query or set current trace (for ``start()``, ``stop()`` or setting parameters)
        - if argument is None: query current trace
        - if argument is an integer: set this trace as current trace
        """
        if numtrace is None:
            buff = self.query('WAV:TRAC?')
            try:
                self.trace_current = int(buff)
                out = self.trace_current
            except:
                tr = self.hardware_channels[0]
                self.write("WAV:TRAC {0}".format(tr))
                self.trace_current = tr
                INFO("Trace {0} selected as current trace.".format(tr))
                WARN(
                    "Current trace in Yoko750 was a special channel: '{0}'. Changing it to Ch{1}.".format(
                        buff, tr
                    )
                )
                out = self.trace_current
        elif isinstance(numtrace, int):
            if numtrace in self.hardware_channels:
                self.write("WAV:TRAC {0}".format(numtrace))
                self.trace_current = numtrace
                out = self.trace_current
                # INFO("Trace {0} selected as current trace.".format(numtrace))
            else:
                ERR(
                    "Trace {0} is not in the list of harware channels.".format(numtrace)
                )
                out = RETURN_ERROR
        else:
            ERR(
                "Trace number must be an integer or None for query. (DSP, MATH, etc. not implemented)"
            )
            out = RETURN_ERROR
        return out

    def get_trace_list(self):
        """ Returns a integer list of active traces.
        """
        self.active_traces = []
        for i in self.hardware_channels:
            if self.query("CHAN{0}:DISP?".format(i)) == "1":
                self.active_traces += [i]
                self.traces[i - 1].active = True
            else:
                self.traces[i - 1].active = False
        return self.active_traces

    def get_current_trace(self):
        """ Returns the number of the current trace, on which settings will be applied.
        """
        return self.query_ascii_values(':WAV:TRAC?')[0]

    # def record_length(self,value=None):
    #   if value is None:
    #       return self.query_ascii_values("WAV:LENG?")[0]
    #   elif value in self.possible_record_lengths:
    #       self.write("WAV:LENG {0}".format(value))
    #   else:
    #       ERR("Possible sample rate values are {0}".format(possible_record_lengths))

    # def nb_points(self,value=None):
    #   if value is None:
    #       return self.query_ascii_values("WAV:LENG?")[0]
    #   elif value in self.possible_record_lengths+1:
    #       self.write("WAV:LENG {0}".format(value))
    #   else:
    #       ERR("Possible sample rate values are {0}".format(possible_record_lengths+1))

    # TODO: create a complete ``trace`` that contains all the Igor Wave information
    def get_ascii(self, tracenum=None):
        """ Returns the data acquired in trace number given in argument (default: current trace) using ASCII transfer
        """
        # if self.waveformat is not FORMAT_ASCII:
        #   self.set_format_ascii()
        self.waveformat = FORMAT_ASCII
        if tracenum is None:
            trace_to_get = int(self.trace_current)
        elif tracenum in self.active_traces:
            trace_to_get = int(tracenum)
            self.current_trace(trace_to_get)
        else:
            ERR("Trace {0} not enabled, cannot read data.".format(tracenum))
            return RETURN_ERROR
        N = self.query_ascii_values("WAV:LENG?")[0]
        self.write("WAV:END {0}".format(N + 1))
        self.traces[trace_to_get - 1].N = N
        data = self.query_ascii_values("WAV:SEND?")
        self.traces[trace_to_get - 1].y = np.array(data)
        rang = self.query_ascii_values("WAV:RANG?")[0]
        offs = self.query_ascii_values("WAV:OFFS?")[0]
        self.traces[trace_to_get - 1].yrange = rang
        self.traces[trace_to_get - 1].offset = offs
        self.traces[trace_to_get - 1].bandwidth = self.bandwidth(trace_to_get)
        self.traces[trace_to_get - 1].invert = self.invert(trace_to_get)
        self.traces[trace_to_get - 1].ac_coupled = self.ac_coupled(trace_to_get)
        self.traces[trace_to_get - 1].module = self.query("WAV:MOD?")
        self.traces[trace_to_get - 1].srate = float(self.query("WAV:SRAT?"))
        self.traces[trace_to_get - 1].x = (
            np.arange(N) / self.traces[trace_to_get - 1].srate
        )
        self.traces[trace_to_get - 1].probe = self.query_ascii_values(
            "CHAN{0}:PROB?".format(trace_to_get)
        )[0]
        self.traces[trace_to_get - 1].averaging = self.averaging()
        return np.array(data)

    @staticmethod
    def _to_str(strbuf):
        return

    @staticmethod
    def _to_int(strbuf):
        try:
            out = int(strbuf)
        except ValueError:
            out = None
        return out

    @staticmethod
    def _to_float(strbuf):
        try:
            out = float(strbuf)
        except ValueError:
            out = None
        return out

    def get_binary(self, tracenum=None):
        """ Returns the data acquired in trace number given in argument (default: current trace) using binary transfer
        """
        self.waveformat = FORMAT_WORD

        if tracenum is None:
            trace_to_get = int(self.trace_current)
        elif tracenum in self.active_traces:
            trace_to_get = int(tracenum)
            self.current_trace(trace_to_get)
        else:
            ERR("Trace {0} not enabled, cannot read data.".format(tracenum))
            return RETURN_ERROR

        self.write("WAV:REC 0")

        tmp = self.query("WAV:LENG?")
        N = self._to_int(tmp)

        divis = 24000.0

        tmp = self.query("WAV:RANG?")
        rang = self._to_float(tmp)

        tmp = self.query("WAV:OFFS?")
        offs = self._to_float(tmp)

        self.traces[trace_to_get - 1].yrange = rang
        self.traces[trace_to_get - 1].offset = offs
        self.traces[trace_to_get - 1].bandwidth = self.bandwidth(trace_to_get)
        self.traces[trace_to_get - 1].invert = self.invert(trace_to_get)
        self.traces[trace_to_get - 1].ac_coupled = self.ac_coupled(trace_to_get)
        self.traces[trace_to_get - 1].module = self.query("WAV:MOD?")
        self.traces[trace_to_get - 1].srate = self._to_float(self.query("WAV:SRAT?"))
        self.traces[trace_to_get - 1].x = (
            np.arange(N) / self.traces[trace_to_get - 1].srate
        )
        self.traces[trace_to_get - 1].probe = self._to_int(
            self.query("CHAN{0}:PROB?".format(trace_to_get))
        )
        self.traces[trace_to_get - 1].averaging = self.averaging()

        self.traces[trace_to_get - 1].N = N
        self.write("WAV:STAR 0")
        self.write("WAV:END {0}".format(N - 1))
        # function query_binary_values() from pyvisa module with parameter header_fmt='ieee' removes the IEEE header #<id><data_length><data>
        dataraw = np.array(
            self.visa_instr.query_binary_values(
                "WAV:SEND?",
                header_fmt='ieee',
                datatype='h',
                is_big_endian=False,
                delay=None,
            )
        )  # , expect_termination=False)) # datatype 'h' is for short = 2 bytes
        data = rang * dataraw * 10.0 / divis + offs
        self.traces[trace_to_get - 1].y = data

        return np.array(data)

    def get_binary_old(self, tracenum=None):
        """ Returns the data acquired in trace number given in argument (default: current trace) using binary transfer
        """
        self.waveformat = FORMAT_WORD

        if tracenum is None:
            trace_to_get = int(self.trace_current)
        elif tracenum in self.active_traces:
            trace_to_get = int(tracenum)
            self.current_trace(trace_to_get)
        else:
            ERR("Trace {0} not enabled, cannot read data.".format(tracenum))
            return RETURN_ERROR

        N = self.query_ascii_values("WAV:LENG?")[0]

        if 2 * N + 8 > self.visa_instr.chunk_size:
            INFO(
                "You may want to increase visa_instr.chunk_size to 2*{}+8 to accelerate transfer a little".format(
                    N
                )
            )

        old_timeout = self.visa_instr.timeout
        if N >= 10e3:
            if N >= 100e3:
                if N >= 1e6:
                    WARN(
                        "{0} : Getting {1} points from Yoko DL750. May take a while (typ. 1 min for 1e6 pts).".format(
                            time.ctime(), N
                        )
                    )
                    if N >= 10e6:
                        if N >= 100e6:
                            if N >= 250e6:
                                self.visa_instr.timeout = 12500e3
                            else:
                                self.visa_instr.timeout = 5000e3
                        else:
                            self.visa_instr.timeout = 500e3
                    else:
                        self.visa_instr.timeout = 60e3
                else:
                    self.visa_instr.timeout = 10e3
            else:
                self.visa_instr.timeout = 1.2e3
        else:
            self.visa_instr.timeout = 250

        divis = 24000.0
        rang = self.query_ascii_values("WAV:RANG?")[0]
        offs = self.query_ascii_values("WAV:OFFS?")[0]
        # self.write("*CLS")        # BIDOUILLAGE.  JUST TO CLEAN BUFFER. TODO: UNDERSTAND
        # self.query("WAV:RANG?")
        self.traces[trace_to_get - 1].yrange = rang
        self.traces[trace_to_get - 1].offset = offs
        self.traces[trace_to_get - 1].bandwidth = self.bandwidth(trace_to_get)
        self.traces[trace_to_get - 1].invert = self.invert(trace_to_get)
        self.traces[trace_to_get - 1].ac_coupled = self.ac_coupled(trace_to_get)
        self.traces[trace_to_get - 1].module = self.query("WAV:MOD?")
        self.traces[trace_to_get - 1].srate = float(self.query("WAV:SRAT?"))
        self.traces[trace_to_get - 1].x = (
            np.arange(N) / self.traces[trace_to_get - 1].srate
        )
        self.traces[trace_to_get - 1].probe = self.query_ascii_values(
            "CHAN{0}:PROB?".format(trace_to_get)
        )[0]
        self.traces[trace_to_get - 1].averaging = self.averaging()

        self.traces[trace_to_get - 1].N = N
        self.write(
            "WAV:STAR 0"
        )  # changement Joël et JD -> Définition du premier point de l'acquisition 17Oct16
        self.write("WAV:END {0}".format(N - 1))
        # function query_binary_values() from pyvisa module with parameter header_fmt='ieee' removes the IEEE header #<id><data_length><data>
        dataraw = np.array(
            self.visa_instr.query_binary_values(
                "WAV:SEND?",
                header_fmt='ieee',
                datatype='h',
                is_big_endian=True,
                delay=None,
            )
        )  # datatype 'h' is for short = 2 bytes
        data = rang * dataraw * 10 / divis + offs
        self.traces[trace_to_get - 1].y = data

        self.visa_instr.timeout = old_timeout

        return np.array(data)

    def get_binary_quick(self, tracenum):
        """ Quick version of get_binary
        """
        if tracenum is None:
            trace_to_get = int(self.trace_current)
        elif tracenum in self.active_traces:
            trace_to_get = int(tracenum)
            self.current_trace(trace_to_get)
        else:
            ERR("Trace {0} not enabled, cannot read data.".format(tracenum))
            return RETURN_ERROR

        N = self.traces[trace_to_get - 1].N

        if 2 * N + 8 > self.visa_instr.chunk_size:
            INFO(
                "You may want to increase visa_instr.chunk_size to 2*{}+8 to accelerate transfer a little".format(
                    N
                )
            )

        old_timeout = self.visa_instr.timeout
        if N >= 10e3:
            if N >= 100e3:
                if N >= 1e6:
                    WARN(
                        "{0} : Getting {1} points from Yoko DL750. May take a while (typ. 1 min for 1e6 pts).".format(
                            time.ctime(), N
                        )
                    )
                    if N >= 10e6:
                        if N >= 100e6:
                            if N >= 250e6:
                                self.visa_instr.timeout = 12500e3
                            else:
                                self.visa_instr.timeout = 5000e3
                        else:
                            self.visa_instr.timeout = 500e3
                    else:
                        self.visa_instr.timeout = 60e3
                else:
                    self.visa_instr.timeout = 10e3
            else:
                self.visa_instr.timeout = 1.2e3
        else:
            self.visa_instr.timeout = 250

        # function query_binary_values() from pyvisa module with parameter header_fmt='ieee' removes the IEEE header #<id><data_length><data>
        # dataraw = np.array(self.visa_instr.query_binary_values("WAV:SEND?", header_fmt='ieee', datatype='h', is_big_endian=False, delay=None)) # datatype 'h' is for short = 2 bytes
        ## changement par léo : test de is_big_endian=True plutot que is_big_endian=False comme au dessus (original inchangé)
        dataraw = np.array(
            self.visa_instr.query_binary_values(
                "WAV:SEND?",
                header_fmt='ieee',
                datatype='h',
                is_big_endian=True,
                delay=None,
            )
        )  # datatype 'h' is for short = 2 bytes
        divis = 24000.0
        data = (
            self.traces[trace_to_get - 1].yrange * dataraw * 10 / divis
            + self.traces[trace_to_get - 1].offset
        )
        self.traces[trace_to_get - 1].y = data

        self.visa_instr.timeout = old_timeout

        return np.array(data)

    def bandwidth(self, numtrace=None, bandwidth=None):
        """ Query or set the bandwidth of trace ``numtrace`` (current trace for None).
        * if ``bandwidth`` = None : query bandwith. Returns 0 for full bandwidth
        * if ``bandwidth`` = frequency in Hz : sets the bandwidth. (rounded by Yoko DL750 to the nearest possible value
        """
        if numtrace is None:
            tr = self.current_trace()
        elif isinstance(numtrace, int) and numtrace in self.hardware_channels:
            tr = numtrace
        else:
            ERR(
                "numtrace argument must be None for current trace or a number in {0}".format(
                    self.hardware_channels
                )
            )
            return RETURN_ERROR

        if bandwidth is None:
            tmp = self.query("CHAN{0}:BWID?".format(tr))
            if tmp == "FULL":
                return 0
            else:
                return float(tmp)
        elif bandwidth == 0:
            self.write("CHAN{0}:BWID FULL".format(tr))
        elif isinstance(bandwidth, float):
            self.write("CHAN{0}:BWID {1}".format(tr, bandwidth))
        else:
            ERR("bandwidth must be 0 (for FULL) or a frequency as a float value.")
            return RETURN_ERROR

        tmp = self.query("CHAN{0}:BWID?".format(tr))
        if tmp == "FULL":
            bw_check = 0
        else:
            bw_check = float(tmp)

        if bw_check != bandwidth:
            WARN(
                "Actual bandwidth of channel {0} is {1} Hz instead of requested {2} (rounded by Yoko DL750 to the nearest possible value).".format(
                    tr, bw_check, bandwidth
                )
            )
            return bw_check
        else:
            return RETURN_NO_ERROR

    def invert(self, numtrace=None, invert=None):
        """ Query or set the invert status of trace ``numtrace`` (current trace for None).
        * if ``invert`` = None : query inversion status (True or False)
        * if ``invert`` = True, invert the waveform on the module
        * if ``invert`` = False, do not invert the waveform on the module
        """
        if numtrace is None:
            tr = self.current_trace()
        elif isinstance(numtrace, int) and numtrace in self.hardware_channels:
            tr = numtrace
        else:
            ERR(
                "numtrace argument must be None for current trace or a number in {0}".format(
                    self.hardware_channels
                )
            )
            return RETURN_ERROR

        if invert is None:
            tmp = self.query_ascii_values("CHAN{0}:INV?".format(numtrace))[0]
            if tmp == 0:
                return False
            if tmp == 1:
                return True
            else:
                ERR(
                    "Value returned by 'CHAN{0}:INV?' is neither '0' or '1' !!!".format(
                        numtrace
                    )
                )
                return RETURN_ERROR
        elif invert is True:
            self.write("CHAN{0}:INV 1".format(numtrace))
        elif invert is False:
            self.write("CHAN{0}:INV 0".format(numtrace))
        else:
            ERR("2nd parameter must be True or False, or None for query.")
            return RETURN_ERROR

        return RETURN_NO_ERROR

    def ac_coupled(self, numtrace=None, ac_coupled=None):
        """ Query or set the coupling mode of trace ``numtrace`` (current trace for None).
        * if ``ac_coupled`` = None : query coupling status (True for AC or False for DC)
        * if ``ac_coupled`` = True, AC coupmling mode is selected
        * if ``ac_coupled`` = False, DC coupling mode is selected
        """
        if numtrace is None:
            tr = self.current_trace()
        elif isinstance(numtrace, int) and numtrace in self.hardware_channels:
            tr = numtrace
        else:
            ERR(
                "numtrace argument must be None for current trace or a number in {0}".format(
                    self.hardware_channels
                )
            )
            return RETURN_ERROR

        if ac_coupled is None:
            tmp = self.query("CHAN{0}:COUP?".format(numtrace))
            if tmp == "DC":
                return False
            if tmp == "AC":
                return True
            else:
                ERR(
                    "Value returned by 'CHAN{0}:COUP?' is neither 'AC' or 'DC. Other values ('GND', 'ACRMS', 'DCRMS', 'TC') are not supported.".format(
                        numtrace
                    )
                )
                return RETURN_ERROR
        elif ac_coupled is True:
            self.write("CHAN{0}:COUP AC".format(numtrace))
        elif ac_coupled is False:
            self.write("CHAN{0}:COUP DC".format(numtrace))
        else:
            ERR("2nd parameter must be True or False, or None for query.")
            return RETURN_ERROR

        return RETURN_NO_ERROR

    def probe(self, numtrace=None):
        """ Query the probe ratio """
        if numtrace is None:
            tr = self.current_trace()
        elif isinstance(numtrace, int) and numtrace in self.hardware_channels:
            tr = numtrace
        else:
            ERR(
                "numtrace argument must be None for current trace or a number in {0}".format(
                    self.hardware_channels
                )
            )
            return RETURN_ERROR

        return self.query_ascii_values("CHAN{0}:PROB?".format(numtrace))[0]

    def bandwidth_current_channel(self, bandwidth=None):
        self.bandwidth(None, bandwidth)

    def invert_current_channel(self, invert=None):
        self.invert(None, invert)

    def info_trace(self, numtrace=None, series="", label="", unit="V", gain=1.0):
        if numtrace is None:
            tr = self.current_trace()
        elif isinstance(numtrace, int) and numtrace in self.hardware_channels:
            tr = int(numtrace)
        else:
            ERR(
                "numtrace argument must be None for current trace or a number in {0}".format(
                    self.hardware_channels
                )
            )
            return RETURN_ERROR

        self.traces[tr - 1].series = series
        self.traces[tr - 1].label = label
        self.traces[tr - 1].unit = unit
        self.traces[tr - 1].gain = gain

        return RETURN_NO_ERROR

    def save_itx(self, filename, traces=None):

        from textwrap import dedent

        if traces is None:
            tr = self.current_trace()
        elif isinstance(traces, list):
            all_good = True
            for t in traces:
                if not isinstance(t, int) or t not in self.active_traces:
                    all_good = False
            if not all_good:
                ERR(
                    "``traces`` argument must be None for current trace, the number of an active trace (in {0}), or a list of active traces numbers.".format(
                        self.active_traces
                    )
                )
                return RETURN_ERROR
            tr = traces
        elif isinstance(traces, int) and traces in self.active_traces:
            tr = list(traces)
        else:
            ERR(
                "``traces`` argument must be None for current trace, the number of an active trace (in {0}), or a list of active traces numbers.".format(
                    self.active_traces
                )
            )
            return RETURN_ERROR

        # Colours based on Tableau20 palette
        DEFAULT_COLOR_LIST_ALL = [
            (31, 119, 180),
            (174, 199, 232),
            (255, 127, 14),
            (255, 187, 120),
            (44, 160, 44),
            (152, 223, 138),
            (214, 39, 40),
            (255, 152, 150),
            (148, 103, 189),
            (197, 176, 213),
            (140, 86, 75),
            (196, 156, 148),
            (227, 119, 194),
            (247, 182, 210),
            (127, 127, 127),
            (199, 199, 199),
            (188, 189, 34),
            (219, 219, 141),
            (23, 190, 207),
            (158, 218, 229),
        ]
        DEFAULT_COLOR_LIST = DEFAULT_COLOR_LIST_ALL[0::2]
        DEFAULT_COLOR_LIST_FADED = DEFAULT_COLOR_LIST[1::2]
        DEFAULT_COLOR_LIST_BLIND = [
            (0, 107, 164),
            (255, 128, 14),
            (171, 171, 171),
            (89, 89, 89),
            (95, 158, 209),
            (200, 82, 0),
            (137, 137, 137),
            (163, 200, 236),
            (255, 188, 121),
            (207, 207, 207),
        ]

        colour_list = DEFAULT_COLOR_LIST + DEFAULT_COLOR_LIST_FADED

        # TODO:  CHECK IF SERIES IS THE SAME (OR CREATE DIFFERENT FOLDERS : check for tr[0] in code) and CHECK THAT LABELS ARE ALL DIFFERENT otherwise bug
        header = "IGOR\nWAVES"
        igor_script = 'X NewDataFolder/O root:Data\n'
        igor_script += 'NewDataFolder/O root:Data:{series}\n'.format(
            series=self.traces[tr[0] - 1].series
        )
        # igor_script += 'SetDataFolder root:Data:\n'

        for t in tr:
            header += "\t{series}_{label}".format(
                series=self.traces[t - 1].series, label=self.traces[t - 1].label
            )
            igor_script += 'SetScale/P x,0,{dt},"s",{series}_{label}\nSetScale d,0,0,"{unit}",{series}_{label}\n'.format(
                dt=1 / self.traces[t - 1].srate,
                series=self.traces[t - 1].series,
                label=self.traces[t - 1].label,
                unit=self.traces[t - 1].unit,
            )
            igor_script += 'Note {series}_{label}, "Scaling: {gain}"\n'.format(
                series=self.traces[t - 1].series,
                label=self.traces[t - 1].label,
                gain=self.traces[t - 1].gain,
            )
            igor_script += 'MoveWave {series}_{label}, root:Data:{series}:\n'.format(
                series=self.traces[t - 1].series, label=self.traces[t - 1].label
            )
            igor_script += '// Line below is a Python dictionary containing measurement information'
            igor_script += '// {dic}'.format(
                dic={
                    key: value
                    for key, value in self.traces[t - 1].__dict__.items()
                    if not key.startswith('__')
                    and not callable(key)
                    and key != 'x'
                    and key != 'y'
                }
            )

        igor_script += 'String/G root:fldrSav0=GetDataFolder(1)\n'
        igor_script += 'SetDataFolder root:Data:{series}:\n'.format(
            series=self.traces[tr[0] - 1].series
        )
        igor_script += (
            'Display /W=(13.2,397.4,408.6,605) '
            + ','.join(
                [
                    '{series}_{label}'.format(
                        series=self.traces[t - 1].series, label=self.traces[t - 1].label
                    )
                    for t in tr
                ]
            )
            + ' as "{series}"\n'.format(series=self.traces[tr[0]].series)
        )
        igor_script += 'SetDataFolder root:fldrSav0\n'
        igor_script += (
            'ModifyGraph '
            + ','.join(
                [
                    '='.join(
                        [
                            'rgb({series}_{label})'.format(
                                series=self.traces[tr[i] - 1].series,
                                label=self.traces[tr[i] - 1].label,
                            ),
                            '{colour}'.format(
                                colour=tuple([c * 2 ** 8 for c in colour_list[i]])
                            ),
                        ]
                    )
                    for i in range(len(tr))
                ]
            )
            + '\n'
        )
        igor_script += 'ModifyGraph mode=2\n'
        igor_script += 'ModifyGraph gridRGB=(56576,56576,56576)\n'
        igor_script += 'ModifyGraph grid=2\n'
        igor_script += 'Label left "\\\\Z12\\\\f01\\\\U"\n'
        igor_script += 'Label bottom "\\\\Z12\\\\f01\\\\U"\n'
        igor_script += (
            'Legend/C/N={series}Legend/J/F=0/B=1 "'.format(
                series=self.traces[tr[0]].series
            )
            + '\\r'.join(
                [
                    '\\\\s({series}_{label}) {series}_{label}'.format(
                        series=self.traces[t - 1].series, label=self.traces[t - 1].label
                    )
                    for t in tr
                ]
            )
            + '"'
        )

        header += "\nBEGIN"
        footer = "END\n" + "X ".join(dedent(igor_script).splitlines(True))

        X = np.sum(
            np.array(
                [
                    np.array([np.eye(len(tr))[n]]).transpose()
                    * self.traces[tr[n] - 1].y
                    / self.traces[tr[n] - 1].gain
                    for n in range(len(tr))
                ]
            ),
            1,
        ).transpose()
        np.savetxt(
            filename,
            X,
            fmt="\t% .16e",
            delimiter='',
            newline='\n',
            comments='',
            header=header,
            footer=footer,
        )

        return RETURN_NO_ERROR
