# Library for controling Yokogawa 7651 Programmable DC source
# Author: Jean-Loup SMIRR, jlsmirr|at|gmail dot com
# 2016-12, Collège de France
# Dependency: instr module (contains standard VISA instruments functions), itself based on pyvisa module
# 
# 
# Pages and Sections mentions in the comments refer to Yokogawa 7651 User's manual 3rd Edition May 1996

RETURN_ERROR = False
RETURN_NO_ERROR = True

import instr
import importlib
importlib.reload(instr)
from time import sleep


class Yoko7651(instr.Instr):
	def __init__(self, visa_name, visa_library=''):
		super(Yoko7651, self).__init__(visa_name, visa_library)
		self.visa_instr.write_termination = "\n"
		#self.visa_instr.baud_rate = 9600
		self.visa_instr.chunk_size = 2048*8
		self.visa_instr.timeout = 1000	# ms

		self.write("H0")	# turns headers off, cf p. 6-35
		self.write("DL1")	# term char: LF
		self.visa_instr.read_termination = "\n"

		self.ranges = [
			{"mode":"VOLTAGE","value":12e-3,"code":"F1R2"},
			{"mode":"VOLTAGE","value":120e-3,"code":"F1R3"},
			{"mode":"VOLTAGE","value":1.2,"code":"F1R4"},
			{"mode":"VOLTAGE","value":12,"code":"F1R5"},
			{"mode":"VOLTAGE","value":32,"code":"F1R6"},
			{"mode":"CURRENT","value":1.2e-3,"code":"F5R4"},
			{"mode":"CURRENT","value":12e-3,"code":"F5R5"},
			{"mode":"CURRENT","value":120e-3,"code":"F5R6"}
			]

		self.write("OS")
		self.idn = self.read()
		tmp = self.read()
		self.range_code = tmp[0:4]
		self.function = [x["mode"] for x in self.ranges if x["code"]==self.range_code][0]
		self.range_i = None
		self.range_v = None
		if self.function == "CURRENT":
			self.range_i = [x["mode"] for x in self.ranges if x["code"]==self.range_code][0]
		elif self.function == "VOLTAGE":
			self.range_v = [x["value"] for x in self.ranges if x["code"]==self.range_code][0]
		else:
			print("ERROR: cannot recognize function and range")

		self.meas_mode = tmp[4:5]
		self.value = tmp
		self.read()
		tmp = self.read().split("LA")
		self.limit_v = float(tmp[0][3:])
		self.limit_i = float(tmp[1])/1000
		self.read()

		self.is_output_on = self.output()
		
		self._clean = False

	def clean(self):
		# self.visa_instr.clear() ##don't use clear for yoko651. It resets it, and makes it bug (need to switch on/off)
		self.visa_instr.close()
		self._clean = True
		print(f"VISA instrument released ({self.visa_name}).")

	def __del__(self):
		if not self._clean:
			self.clean()
		del self.visa_instr
		# del self.visa_resource_manager
			
	def __str__(self):
		return self.idn

	def __repr__(self):
		return self.idn


	def trig(self):
		self.write("E")

	def source_current(self):
		if self.function == "CURRENT":
				print("WARNING: already sourcing current. Doing nothing")
		else:
			if self.range_i is None:
				self.write("F5R4")
				self.function = "CURRENT"
				self.range_current(1.2e-3)
			else:
				self.write([x["code"] for x in self.ranges if x["value"]==self.range_i and x["mode"]=="CURRENT"][0])
				self.function = "CURRENT"

	def source_voltage(self):
		if self.function == "VOLTAGE":
				print("WARNING: already sourcing voltage. Doing nothing")
		else:
			if self.range_v is None:
				self.write("F1R2")
				self.function = "VOLTAGE"
				self.range_voltage(12e-3)
			else:
				self.write([x["code"] for x in self.ranges if x["value"]==self.range_v and x["mode"]=="VOLTAGE"][0])
				self.function = "VOLTAGE"



	def voltage(self, v=None):
		if self.function is not "VOLTAGE":
				print("ERROR: switch to voltage sourcing mode before changing voltage value")
				return RETURN_ERROR
		else:
			if v is None:
				bla = self.query("OD")
				return float(bla)
			elif isinstance(v,float) or isinstance(v,int):
				if v > self.range_v:
					print("ERROR: increase voltage range. Voltage unchanged")
				else:
					self.write("S{}".format(v))
					self.trig()
			else:
				print("ERROR: voltage must be a number...")
				return RETURN_ERROR


	def current(self, i=None):
		if self.function is not "CURRENT":
				print("ERROR: switch to current sourcing mode before changing current value")
				return RETURN_ERROR
		else:
			if i is None:
				bla = self.query("OD")
				return float(bla)
			elif isinstance(i,float) or isinstance(i,int):
				if i > self.range_i:
					print("ERROR: increase current range. Current unchanged")
				else:
					self.write("S{}".format(i))
					self.trig()
			else:
				print("ERROR: current must be a number...")
				return RETURN_ERROR


	def limit_current(self,ilim=None):
		if ilim is None:
			return self.limit_i
		elif isinstance(ilim,float) or isinstance(ilim,int):
			if 5e-3<=ilim<=120e-3:
				self.write("LA{}".format(round(ilim*1000)))
				self.limit_i = round(ilim*1000)/1000
			else:
				print("ERROR: current limit must be between 5 and 120 mA (will be rounded to mA)")
				return RETURN_ERROR
		else:
			print("ERROR: current limit must be between 5 and 120 mA (will be rounded to mA)")
			return RETURN_ERROR

	def limit_voltage(self,vlim=None):
		if vlim is None:
			return self.limit_v
		elif isinstance(vlim,float) or isinstance(vlim,int):
			if 1<=vlim<=32:
				self.write("LV{}".format(round(vlim)))
				self.limit_v = round(vlim)
			else:
				print("ERROR: voltage limit must be between 1 and 30 V (will be rounded to V)")
				return RETURN_ERROR
		else:
			print("ERROR: voltage limit must be between 1 and 30 V (will be rounded to V)")
			return RETURN_ERROR





	# WARNING: current range can only be set if sourcing current
	def range_current(self, irange=None):
		if self.function is not "CURRENT":
				print("ERROR: switch to current sourcing mode before changing current range")
				return RETURN_ERROR
		else:
			if irange is None:
				return self.range_i
			elif isinstance(irange,float) or isinstance(irange,int):
				if abs(irange)<=1.2e-3:
					self.write("R4E")
					self.range_i = 1.2e-3
					if abs(irange) != 1.2e-3:
						print("WARNING: actual range set to 1.2 mA")
				elif 1.2e-3<abs(irange)<=12e-3:
					self.write("R5E")
					self.range_i = 12e-3
					if abs(irange) != 12e-3:
						print("WARNING: actual range set to 12 mA")
				elif 12e-3<abs(irange)<=120e-3:
					self.write("R6E")
					self.range_i = 120e-3
					if abs(irange) != 120e-3:
						print("WARNING: actual range set to 120 mA")
				else:
					print("ERROR: max current is 120 mA")
					return RETURN_ERROR
			else:
				print("ERROR: parameter must be a value between 0 and 120e-3 (or omitted for query")


	# WARNING: voltage range can only be set if sourcing voltage
	def range_voltage(self, vrange=None):
		if self.function is not "VOLTAGE":
				print("ERROR: switch to voltage sourcing mode before changing voltage range")
				return RETURN_ERROR
		else:
			if vrange is None:
				return self.range_v
			elif isinstance(vrange,float) or isinstance(vrange,int):
				if abs(vrange)<=12e-3:
					self.write("R2E")
					self.range_v = 12e-3
					if abs(vrange) != 12e-3:
						print("WARNING: actual range set to 12 mV")
				elif 12e-3<abs(vrange)<=120e-3:
					self.write("R3E")
					self.range_v = 120e-3
					if abs(vrange) != 120e-3:
						print("WARNING: actual range set to 120 mV")
				elif 120e-3<abs(vrange)<=1.2:
					self.write("R4E")
					self.range_v = 1.2
					if abs(vrange) != 1.2:
						print("WARNING: actual range set to 1.2 V")
				elif 1.2<abs(vrange)<=12:
					self.write("R5E")
					self.range_v = 12
					if abs(vrange) != 12:
						print("WARNING: actual range set to 12 V")
				elif 12<abs(vrange)<=32:
					self.write("R6E")
					self.range_v = 32
					if abs(vrange) != 32:
						print("WARNING: actual range set to 32 V")
				else:
					print("ERROR: max voltage is 32 V")
					return RETURN_ERROR
			else:
				print("ERROR: parameter must be a value between 0 and 32 (or omitted for query")



	# Functions to set and query the output status
	def output(self, arg=None, force=False):
		if arg==True and not self.is_output_on:
			if self.function == "VOLTAGE" and np.abs(self.voltage()) > 0 and not force:
				print("ERROR: To force turning output ON when value is non-zero, use output(True,True) syntax. Output still OFF.")
				return RETURN_ERROR
			if self.function == "CURRENT" and np.abs(self.current()) > 0 and not force:
				print("ERROR: To force turning output ON when value is non-zero, use output(True,True) syntax. Output still OFF.")
				return RETURN_ERROR
			self.write("O1E")
			self.is_output_on = True
		elif arg==True and self.is_output_on:
			print("WARNING: Output already ON. Doing nothing.")
		elif arg==False and self.is_output_on:
			if self.function == "VOLTAGE" and np.abs(self.voltage()) > 0 and not force:
				print("ERROR: To force turning output OFF when value is non-zero, use output(False,True) syntax. Output still ON.")
				return RETURN_ERROR
			if self.function == "CURRENT" and np.abs(self.current()) > 0 and not force:
				print("ERROR: To force turning output OFF when value is non-zero, use output(False,True) syntax. Output still ON.")
				return RETURN_ERROR
			self.write("O0E")
			self.is_output_on = False
		elif arg==False and not self.is_output_on:
			print("WARNING: Output already OFF. Doing nothing.")
		elif arg is None:
			status = self.query("OC")
			if int(status[5:]) & 0b00010000 == 0b00010000:
				self.is_output_on = True
				return True
			elif int(status[5:]) & 0b00010000 == 0b00000000:
				self.is_output_on = False
				return False
			else:
				print("ERROR: Bit 5 of OC is neither 0 or 1 (obviously, coding error!)")
				return RETURN_ERROR
		else:
			print("ERROR: argument must be a boolean or omitted for query")
			return RETURN_ERROR

def output_force(self, arg=None):
	return self.output(arg, force=True)

def Output(self, arg=None):
	return self.output(arg, force=True)

def output_on(self):
	return self.output(True)

def output_off(self):
	return self.output(False)
