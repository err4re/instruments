# Library for controling Keithley 2400 Source Meter Unit
# Author: Jean-Loup SMIRR, jlsmirr|at|gmail dot com
# 2016-07, Collège de France
# Dependency: instr module (contains standard VISA instruments functions), itself based on pyvisa module
# 
# 
# Pages and Sections mentions in the comments refer to Keithley 2400 User's manual Revision G (2400S-900-01)

RETURN_ERROR = False
RETURN_NO_ERROR = True

import instr
import importlib
importlib.reload(instr)
from time import sleep


class K2400(instr.Instr):
	def __init__(self, visa_name):
		super(K2400, self).__init__(visa_name)
		self.visa_instr.read_termination = '\n'
		self.visa_instr.write_termination = '\n'
		self.visa_instr.baud_rate = 9600
		self.visa_instr.chunk_size = 2048*8
		self.visa_instr.timeout = 5000	# ms

		self.current_range = 0   # TO READ FROM DEVICE AT INIT *********TODO**********
		self.min_current = -1.1e-6  # A
		self.max_current =  1.1e-6  # A
		self.min_voltage = -1.1e-3  # V
		self.max_voltage =  1.1e-3  # V
		self.min_request_delay = 0.01   # minium time between two requests in a loop with a sleep()
		self.sweep_rate = 1.e-3   # A/s
		self.sweep_min_delay = 0.001
		self.sweep_nb_points = 101
		self.last_sweep_current_init = None
		self.last_sweep_current_final = None
		self.last_sweep_time = None
		self.last_sweep_delay = None
		self.last_sweep_nb_points = None
		self.last_sweep_step = None
		self.last_sweep_finished = True

		self.idn = self.get_idn()
		if self.idn[0:36] != "KEITHLEY INSTRUMENTS INC.,MODEL 2400":
			print("Error: Cannot communicate with Keithley 2400\n")
		else:
			self.nb_points_max = self.query_ascii_values("TRAC:POIN? MAX")[0]
			self.nb_points = self.query_ascii_values("TRAC:POIN?")[0]
			
	def __str__(self):
		return self.idn

	def __repr__(self):
		return self.idn


	def line_frequency(self):
		return self.query_ascii_values(':SYST:LFR?')[0]

	def is_protocol_488dot1(self):
		tmp = self.query("SYST:MEP?")
		if tmp == "1":
			return False
		elif tmp == "0":
			return True
		else:
			print("Error: SYST:MEP? returning instead of '0' or '1'.".format(tmp))
			return RETURN_ERROR


	# see p. 18-51 of Keithley 2400 User's manual
	def is_overflow_ascii(self,str):
		if str == "+9.9E37":
			return True
		else:
			return False

	# see p. 18-51 of Keithley 2400 User's manual
	def is_overflow_float(self,x):
		if x == 9.9e37:
			return True
		else:
			return False

	# resets the internal timestamp ok K2400. See Section 9 of User's manual
	def reset_timestamp(self):
		self.write(":SYST:TIME:RES")

	def get_timestamp(self):
		return self.query_ascii_values(":SYST:TIME?")[0]

	def set_format_binary(self):
		self.write(":FORM:DATA READ,32")

	def set_format_ascii(self):
		self.write(":FORM:DATA ASC")

	def read_binary(self, N=1):
		pass
	# converts Binary output by the K2400 to Python float
	# arguments: N = number of readings, default 1
	def bin2num(self, N=1):
		pass

	# NOT WORKING
	def go_to_local(self):
		self.write("GTL")

	# NOT WORKING
	def group_execute_trigger(self):
		self.write("GET")


	def set_current_limits(self, min_current, max_current):
		if max_current >= min_current:
			self.min_current = min_current
			self.max_current = max_current
		else:
			print("Error: upper limit should be greater than lower limit.")

	def get_current_limits(self):
		return [self.min_current, self.max_current]

	def set_voltage_limits(self, min_voltage, max_voltage):
		if max_voltage >= min_voltage:
			self.min_voltage = min_voltage
			self.max_voltage = max_voltage
		else:
			print("Error: upper limit should be greater than lower limit.")

	def get_voltage_limits(self):
		return [self.min_voltage, self.max_voltage]

	def get_range(self):
		pass    # TODO

	def compliance_voltage(self, voltage=None):
		if voltage is None:
			return self.query_ascii_values("VOLT:PROT?")[0]
		elif abs(voltage) <= 210:
			self.write("VOLT:PROT {0}".format(voltage))
		else:
			print("Error: compliance voltage should be <= 210V.")


	def compliance_current(self, current=None):
		if current is None:
			return self.query_ascii_values("CURR:PROT?")[0]
		elif abs(current) <= 1.05:
			self.write("CURR:PROT {0}".format(current))
		else:
			print("Error: compliance current should be <= 1.05A.")


	# WARNING: current range can only be set if sourcing current. Otherwise, no effect !
	def range_current(self, current=None): # use 0 for AUTO RANGE
		if current is None:
			return self.query_ascii_values("CURR:RANG?")[0]
		elif current == 0:
			self.write("SOUR:CURR:RANG:AUTO ON")
			self.current_range = 0
		elif abs(current) > 0 and abs(current) <= 1.05:
			self.write("SOUR:CURR:RANG:AUTO OFF")
			self.write("SOUR:CURR:RANG {0}".format(current))
			self.current_range = self.query_ascii_values("CURR:RANG?")[0]
			return self.current_range
		else:
			print("Error: current range should be <= 1.05A (use 0 for auto-range).")

	# WARNING: voltage range can only be set if sourcing voltage. Otherwise, no effect !
	def range_voltage(self, voltage=None): # use 0 for AUTO RANGE
		if voltage is None:
			return self.query_ascii_values("VOLT:RANG?")[0]
		elif voltage == 0:
			self.write("SOUR:VOLT:RANG:AUTO ON")
			self.voltage_range = 0
		elif abs(voltage) > 0 and abs(voltage) <= 210:
			self.write("SOUR:VOLT:RANG:AUTO OFF")
			self.write("SOUR:VOLT:RANG {0}".format(voltage))
			self.voltage_range = self.query_ascii_values("VOLT:RANG?")[0]
			return self.voltage_range
		else:
			print("Error: current range should be <= 210V (use 0 for auto-range).")


	# May be used to check if multiple sensing modes are enabled
	def sense_howmany(self):
		return self.query_ascii_values("FUNC:COUNT?")[0]


	def source_current(self,arg=None):
		if arg==None:
			bla = self.query("SOUR:FUNC?")
			if bla in ["CURR", "CURRent", "CURRENT", "current"]:
				return True
			else:
				return False
		elif arg is True:
			self.write("SOUR:FUNC CURR")
		elif arg is False:
			self.write("SOUR:FUNC VOLT")
		else:
			print("Error: argument must be absent (None), True, False. MEMORY function not implemented (p.18-74).")

	def source_voltage(self,arg=None):
		if arg==None:
			bla = self.query("SOUR:FUNC?")
			if bla in ["VOLT", "VOLTage", "VOLTAGE", "voltage"]:
				return True
			else:
				return False
		elif arg is True:
			self.write("SOUR:FUNC VOLT")
		elif arg is False:
			self.write("SOUR:FUNC CURR")
		else:
			print("Error: argument must be absent (None), True, False. MEMORY function not implemented (p.18-74).")

	def source_mode_fixed(self,arg=None):
		if self.source_current():
			if arg==None:
				bla = self.query("SOUR:CURR:MODE?")
				if bla in ["FIX", "FIXed", "FIXED", "fixed"]:
					return True
				else:
					return False
			elif arg is True:
				self.write("SOUR:CURR:MODE FIX")
			elif arg is False:
				self.write("SOUR:CURR:MODE SWE")
			else:
				print("Error: argument must be absent (None), True, False. LIST mode not implemented (p.18-74).")
		elif self.source_voltage():
			if arg==None:
				bla = self.query("SOUR:VOLT:MODE?")
				if bla in ["FIX", "FIXed", "FIXED", "fixed"]:
					return True
				else:
					return False
			elif arg is True:
				self.write("SOUR:VOLT:MODE FIX")
			elif arg is False:
				self.write("SOUR:VOLT:MODE SWE")
			else:
				print("Error: argument must be absent (None), True, False. LIST mode not implemented (p.18-74).")
		else:
			print("Error: Cannot change source mode with MEMORY function.")



	# Queries, enable or disables each SENSE functions
	def sense_current(self,arg=None):
		if arg==True:
			self.write("FUNC 'CURR'")
		elif arg==False:
			self.write("FUNC:OFF 'CURR'")
		else:
			status = self.query("FUNC:STATE? 'CURR'")
			if status in ["1"]:
				return True
			elif status in ["0"]:
				return False
			else:
				print("Error: FUNC:STATE? 'CURR' is neither '0' or '1'.")
				return RETURN_ERROR

	def sense_voltage(self,arg=None):
		if arg==True:
			self.write("FUNC 'VOLT'")
		elif arg==False:
			self.write("FUNC:OFF 'VOLT'")
		else:
			status = self.query("FUNC:STAT? 'VOLT'")
			if status in ["1"]:
				return True
			elif status in ["0"]:
				return False
			else:
				print("Error: FUNC:STATE? 'VOLT' is neither '0' or '1'.")
				return RETURN_ERROR

	def sense_resistance(self,arg=None):
		if arg==True:
			self.write("FUNC 'RES'")
		elif arg==False:
			self.write("FUNC:OFF 'RES'")
		else:
			status = self.query("FUNC:STATE? 'RES'")
			if status in ["1"]:
				return True
			elif status in ["0"]:
				return False
			else:
				print("Error: FUNC:STATE? 'RES' is neither '0' or '1'.")
				return RETURN_ERROR




	# Three functions to set and query the output status
	def output_on(self):
		self.write("OUTP:STAT ON")

	def output_off(self):
		self.write("OUTP:STAT OFF")

	def output(self, arg=None):
		if arg==True:
			self.write("OUTP:STAT ON")
		elif arg==False:
			self.write("OUTP:STAT OFF")
		else:
			status = self.query("OUTP:STAT?")
			if status in ["ON","1"]:
				return True
			elif status in ["OFF", "0"]:
				return False
			else:
				print("Error: OUTP:STAT? is neither 'OFF', 'ON', '0' or '1'.")
				return RETURN_ERROR

	# Sets and queries which terminals are used (front or rear)
	def use_rear_terminals(self, arg=None):
		if arg==True:
			self.write("ROUT:TERM REAR")
		elif arg==False:
			self.write("ROUT:TERM FRON")
		else:
			status = self.query("ROUT:TERM?")
			if status in ["FRONT","FRONt","front","FRON","fron"]:
				return False
			elif status in ["REAR","rear"]:
				return True
			else:
				print("Error: ROUT:TERM? is neither 'FRONT','FRONt','front','FRON','fron', 'REAR' or 'rear'.")
				return RETURN_ERROR


	def set_current(self, current):
		if (current <= self.max_current) and (current >= self.min_current):
			self.write("SOUR:CURR {0}".format(current))
		else:
			print("Error: current out of range. use set_current_limits(min,max).")

	def get_current(self):
		bla = self.query("SOUR:CURR?")
		try:
			output = float(bla)
		except:
			print("Error in get_current. Value read: {0}".format(bla))
			output = None
		return output

	def set_voltage(self, voltage):
		if (voltage <= self.max_voltage) and (voltage >= self.min_voltage):
			self.write("SOUR:VOLT {0}".format(voltage))
		else:
			print("Error: voltage out of range. use set_voltage_limits(min,max).")

	def get_voltage(self):
		bla = self.query("SOUR:VOLT?")
		try:
			output = float(bla)
		except:
			print("Error in get_voltage. Value read: {0}".format(bla))
			output = None
		return output

	def data_nb_points(self):
		return self.query_ascii_values("TRAC:POIN:ACT?")[0]

	def data_buffer_read(self):
		return self.query_ascii_values("TRAC:DATA?")

	def data_buffer_clear(self):
		self.write("TRAC:CLE")

	def data_buffer_size(self,N=None):
		if N is None:
			return self.query_ascii_values("TRAC:POIN?")[0]
		elif N >= 1 and N <= self.nb_points_max:
			self.write("TRAC:POIN {0}".format(N))
		else:
			print("Error: buffer size must be between 1 and {0}".format(self.nb_points_max))

	def trigger_clear(self):
		self.write("TRIG:CLE")

	def initiate(self):
		self.write("INIT")

	def fetchval(self):
		bla = self.query_ascii_values("FETC?")
		return bla	# PROCESS THE OTHER DATA TOO

	def readval(self):
		bla = self.query_ascii_values("READ?")
		return bla	# PROCESS THE OTHER DATA TOO


	def abort(self):
		self.write("ABOR")

	def errors_clear(self):
		self.write("SYST:CLE")

	def errors_howmany(self):
		return self.query_ascii_values("SYST:ERR:COUN?")[0]

	def errors_get_last(self):
		return self.query("SYST:ERR?")

	def errors_get_all(self):
		return self.query("SYST:ERR:ALL?")

	def set_sweep_rate(self, sweep_rate):
		if sweep_rate > 0 and sweep_rate <= 0.1:
			self.sweep_rate = sweep_rate
		else:
			print("If you want a sweep rate higher than 0.1 A/s, zero or negative, please change the program...")

	def set_current_smooth(self, current):
		if current <= self.max_current and current >= self.min_current:
			# nb_steps = 50
			self.last_sweep_current_final = current
			self.last_sweep_current_init = self.get_current()
			if self.last_sweep_current_init != self.last_sweep_current_final:
				self.last_sweep_time = (self.last_sweep_current_final - self.last_sweep_current_init) / self.sweep_rate
				step = (self.last_sweep_current_final - self.last_sweep_current_init) / (self.sweep_nb_points - 1)
				delay = self.last_sweep_time / (self.sweep_nb_points - 1)
				if delay > self.sweep_min_delay:
					self.last_sweep_delay = delay
					self.last_sweep_nb_points = self.sweep_nb_points
					self.last_sweep_step = step
				else:
					self.last_sweep_delay = self.sweep_min_delay
					self.last_sweep_nb_points = self.last_sweep_time / self.last_sweep_delay
					self.last_sweep_step = (self.last_sweep_current_final - self.last_sweep_current_init) / self.last_sweep_nb_points
				self.write("SOUR:SWE:SPAC LIN")
				self.write("SOUR:CURR:STAR {0}".format(self.last_sweep_current_init))
				self.write("SOUR:CURR:STOP {0}".format(self.last_sweep_current_final))
				self.write("SOUR:CURR:STEP {0}".format(self.last_sweep_step))
				self.write("SOUR:DEL {0}".format(self.last_sweep_delay))
				self.write("SOUR:SWE:RANG FIX")
				self.write("SOUR:SWE:COUN 1")
				self.write("SOUR:SWE:ARM")
				self.write("INIT")
				self.last_sweep_finished = False
		else:
			print("Error: Current must be in the range {0} to {1} mA".format(self.min_current, self.max_current))

	def wait_for_sweep(self):
		while not self.last_sweep_finished:
			if self.last_sweep_current_final == self.get_current():
				self.last_sweep_finished = True
			else:
				sleep(min(self.last_sweep_delay, self.min_request_delay))

	def abort_sweep(self):
		self.write("SOUR:SWE:ABOR")
		self.last_sweep_finished = True

	def reset(self):
		self.write("*RST")
		self.write("*CLS")