# Library for controling Mcdc 2805 motor controler from Faulhaber
# Author: Arthur MARGUERITE, arthur.marguerite|at|college-de-france |dot| fr
# 2020-12, Collège de France

from instruments import instr
import pyvisa as visa
import importlib

importlib.reload(instr)

import numpy as np

import inspect
from datetime import datetime
from time import sleep

_DEBUG_ = True
_WARN_ = True
_INFO_ = True
Max_Speed = 10000

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


class Mcdc2805(instr.Instr):
    def __init__(self, visa_name, visa_library=''):
        super(Mcdc2805, self).__init__(visa_name, visa_library)
        self.visa_instr.timeout = 5000  # in ms.
        self.visa_instr.read_termination = '\r\n'
        self.visa_instr.write_termination = '\r'
        self.visa_instr.send_end = True
        self.visa_instr.query_delay = 0.0

        # chunk_size = max data block of response data
        self.visa_instr.chunk_size = 1024

        # For RS232 (cf manual p. 11)
        self.visa_instr.baud_rate = 9600
        self.visa_instr.parity = (
            visa.constants.VI_ASRL_PAR_NONE
        )  # parity=none define in pyvisa as VI_ASRL_PAR_NONE which is defined = 0
        self.visa_instr.stop_bits = (
            visa.constants.VI_ASRL_STOP_ONE
        )  # 1 bit = value 10, 1.5bit=15, 2bit=20
        self.visa_instr.flow_control = visa.constants.VI_ASRL_FLOW_RTS_CTS
        self.visa_instr.data_bits = 8
        # END For RS232

        self.encoder_resolution(2048/4) #default resolution at start
        self.write("DIPROG") #disactivate any saved inner program


    def write(self, command, debug=False):   
        self.visa_instr.write(command)
       
    def query(self, command, debug=False):
        return self.visa_instr.query(command)

    def __del__(self):
        self.visa_instr.close()
        del self.visa_instr

    def save_config_at_start(self):
        "Saves the current configuration. When turned off, the motor will start with this configuration."
        self.write("EEPSAV")

    def encoder_resolution(self, value=None):
        ' Read or set the encoder resolution, see page 14 of manual.'
        ' Velocity is in rpm and acceleration in Rev/s^2'
        if value is None:
            res = self.query("GENCRES")
            return res
        elif value*4 <= 65535:
            self.write("ENCRES"+str(4*value))
        else:
            print("Encoder resolution multiplied by 4 must be below 65535")
    
    def source_type(self, type):
        ' Set how the velocity is controled, see pages 9-10. Note that the driver is only developed for type 0'
        if type == 0:
            self.write("SOR0")
        elif type ==1:
            self.write("SOR1")
        elif type == 2:
            self.write("SOR2")
        else:
            print("Type must be 0, 1 or 2, see manual page 9 or 10.")
    
    def status(self):
        return self.query("GST")

    def velocity(self, value=None):
        if value is None:
            res = self.query("GV")
            return res
        elif value <= Max_Speed:
            self.write("V"+str(value))
        else:
            print("Let's not go faster than"+str(Max_Speed))
    def acceleration(self, value=None):
        if value is None:
            res = self.query("GAC")
            return res
        else:
            self.write("AC"+str(value))
    
    def set_position_origin(self):
        self.write("H0")
        # self.write("M")

    def get_position(self):
        return self.query("POS")

    def motion_start(self):
        "the function starts a new motion sequence and must be used after new position, speed and"
        "acceleration parameters are set. Combined with set_relative_pos just before it also enables to"
        " initiate the position mode as oppoed to velocity mode"
        self.write("M")

    def max_vel(self, value=None):
        if value is None:
            res = self.query("GSP")
            return res
        else:
            self.write("SP"+str(value))
    
    def min_vel(self, value=None):
        if value is None:
            res = self.query("GMV")
            return res
        else:
            self.write("MV"+str(value))
    
    def rotate_to(self, value):
        self.write("LA"+str(value))
        self.motion_start()

    def rotate_of(self, value):
        self.write("LR"+str(value))
        self.motion_start()


    def notify_pos(self, value):
        "to finish (write or query?)"
        self.write("NP"+str(value))
    
    def notify_vel(self, value):
        "to finish (write or query?)"
        self.write("NV"+str(value))

    def hardstop(self):
        self.write("HL3")
        self.write("M")



    # def debug_status(self):
    #     stb = self.query('*STB?')  # status byte
    #     ese = self.query('*ESE?')  # standard event status enable
    #     esr = self.query('*ESR?')  # standard event status register
    #     sre = self.query('*SRE?')  # service request enable
    #     operation_status_condition_register = self.query(':STATUS:OPER:COND?')
    #     operation_status_event_register = self.query(':STATUS:OPER?')
    #     questionable_status_condition_register = self.query(':STATUS:QUES:COND?')
    #     questionable_status_event_register = self.query(':STATUS:QUES?')
    #     errors = self.query(':SYST:ERR:ALL?')
    #     out = f'\nstb: {stb} | ese: {ese} | esr: {esr} | sre: {sre}\n'
    #     out += f'operation status: ( condition: {operation_status_condition_register} | event: {operation_status_event_register} )\n'
    #     out += f'questionable status: ( condition: {questionable_status_condition_register} | event: {questionable_status_event_register} )\n'
    #     out += f'errors: {errors}\n'
    #     return out




