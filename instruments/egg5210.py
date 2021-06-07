# Library for controling EG&G 5210 Lock-in amplifier
# Author: Jean-Loup SMIRR, jlsmirr|at|gmail dot com
# 2016-12, Collège de France
# Dependency: instr module (contains standard VISA instruments functions), itself based on pyvisa module
# 
# 
# Pages and Sections mentions in the comments refer to EG&G 5210 Instruction manual revision 219874-A-MNL-G (2002)

RETURN_ERROR = False
RETURN_NO_ERROR = True

TAU = 0.1	# (s) characteristic time for command processing by instrument (measured time was 70 ms)
TIMEOUT_NORMAL = 0.8 # (s)
TIMEOUT_NORMAL = 10. # (s)

import instr
import importlib
importlib.reload(instr)
from time import sleep, time
from math import log10, floor
import numpy as np

# instead of using the dictionnary self.fullscale_codes, may use the following formula (see p. 6-21)
def rangecode_to_range(code):
	def round_to_1_significant_digit(x):
		return round(x, -int(floor(log10(abs(x)))))
	return round_to_1_significant_digit((1 + (2*(code%2)))*10**(int(code/2)-7))


class Egg5210(instr.Instr):
	def __init__(self, visa_name, visa_library=''):
		super(Egg5210, self).__init__(visa_name, visa_library)
		self.visa_instr.read_termination = "\r"
		self.visa_instr.write_termination = "\r"
		#self.visa_instr.baud_rate = 9600
		self.visa_instr.chunk_size = 128*8
		self.visa_instr.timeout = 5000	# ms
		self.send_end = True
		self.query_delay = 0.1 # in seconds. Useless since we use our own query based on STB
		self.visa_instr.clear()

		self.gpib_address = int(visa_name.split("::")[-2].split(",")[-1])

		# print(self.gpib_address)

		# self.write("GP {gpib_addr} {term_type}".format(gpib_addr=self.gpib_address,term_type=0))	# GPIB address read from visa_name, term_type 0 is \r (cf p. 6-18)
		self.value_separator = "," # can be ASCII 13 or 32 to 125 : "\r", " " to "}" according to p. 6-18.
		#sleep(2000e-3)
		self.write("DD {}".format(ord(self.value_separator)))		# use comma (ASCII 44) as a value separator

		self.fullscale_codes = [	# code used with SEN command, corresponding full-scale sensitivity in Volt (max value is 1.5*sensitivity)
			{"code":0, "sensitivity":100.e-9},
			{"code":1, "sensitivity":300.e-9},
			{"code":2, "sensitivity":1.e-6},
			{"code":3, "sensitivity":3.e-6},
			{"code":4, "sensitivity":10.e-6},
			{"code":5, "sensitivity":30.e-6},
			{"code":6, "sensitivity":100.e-6},
			{"code":7, "sensitivity":300.e-6},
			{"code":8, "sensitivity":1.e-3},
			{"code":9, "sensitivity":3.e-3},
			{"code":10,"sensitivity":0.010},
			{"code":11,"sensitivity":0.030},
			{"code":12,"sensitivity":0.100},
			{"code":13,"sensitivity":0.300},
			{"code":14,"sensitivity":1.},
			{"code":15,"sensitivity":3.}
		]
		self.timeconstant_codes = [	# code used with TC (or XTC) command, corresponding timeconstant in seconds
			{"code":0, "timeconstant":0.001},
			{"code":1, "timeconstant":0.003},
			{"code":2, "timeconstant":0.01},
			{"code":3, "timeconstant":0.03},
			{"code":4, "timeconstant":0.1},
			{"code":5, "timeconstant":0.3},
			{"code":6, "timeconstant":1.},
			{"code":7, "timeconstant":3.},
			{"code":8, "timeconstant":10.},
			{"code":9, "timeconstant":30.},
			{"code":10,"timeconstant":100.},
			{"code":11,"timeconstant":300.},
			{"code":12,"timeconstant":1000.},
			{"code":13,"timeconstant":3000.}
		]

		self.fullscale = self.get_sensitivity()
		self.timeconstant = self.get_timeconstant()


	# NECESSARY ?
	# def write(self,command):
	# 	self.visa_instr.write(command)
	# 	t0 = time()
	# 	ready_to_check = not self.is_command_complete()
	# 	while (not ready_to_check) & ( time()-t0 < TIMEOUT ):
	# 		sleep(TAU)
	# 		ready_to_check = not self.is_command_complete()
	# 	if not ready_to_check:
	# 		print("ERROR command not complete in write()")
	# 		return RETURN_ERROR


	# def query(self,command):
	# 	self.write(command)
	# 	t0 = time()
	# 	available = self.is_data_available()
	# 	while (not available) & ( time()-t0 < TIMEOUT ):
	# 		sleep(TAU)
	# 		available = self.is_data_available()
	# 	if not available:
	# 		print("ERROR data not available in query()")
	# 		return RETURN_ERROR
	# 	out = self.visa_instr.read()
	# 	t0 = time()
	# 	complete = self.is_command_complete()
	# 	while (not complete) & ( time()-t0 < TIMEOUT ):
	# 		sleep(TAU)
	# 		complete = self.is_command_complete()
	# 	if not complete:
	# 		print("ERROR command not complete in query()")
	# 		return RETURN_ERROR
	# 	return out

	def write(self,command):
		return self.communicate(command)

	def query(self,command):
		return self.communicate(command)

	def communicate(self,command):
		if command.startswith(('ANR ', 'AQN ', 'AS ', 'ASM ', 'ATS ', 'AXO ')):
			timeout = TIMEOUT_LONG
		else:
			timeout = TIMEOUT_NORMAL

		t0 = time()
		ret = ""
		out = ""
		
		while time()-t0 < timeout:
			try:
				sb = self.visa_instr.read_stb()
				assert sb & 0b10000111 == 0b00000001
			except:
				print(f"Before command {command}: \tsb={sb}")
				if sb & 0b10000000 == 0b10000000:
					out = self.visa_instr.read()
					print(f"Reading leftover data before command: value={out}")
			else:
				break
			finally:
				sleep(TAU)

		sb = self.visa_instr.read_stb()
		if (sb & 0b10000011 != 0b00000001):
			raise RuntimeError(f"ERROR cannot reset STB before sending command ({command})")

		self.visa_instr.write(command)
		sleep(TAU)

		sb = self.visa_instr.read_stb()

		t0 = time()
		while (sb & 0b00000001 == 0b00000000) & ( time()-t0 < timeout ):
			sb = self.visa_instr.read_stb()
			sleep(TAU)
			if sb & 0b10000000 == 0b10000000:
				ret += self.visa_instr.read()

		if sb & 0b00000100 == 0b00000100:
			raise RuntimeError(f"ERROR parameter error ({command})")
			ret = None
		
		if sb & 0b00000010 == 0b00000010:
			raise RuntimeError(f"ERROR invalid command ({command})")
			ret = None

		if sb & 0b00000001 == 0b00000000:
			raise RuntimeError(f"ERROR command not complete. Timeout ({timeout:.3f}s).")
			ret = None

		return ret


			
	def __str__(self):
		return self.gpib_address

	def __repr__(self):
		return self.gpib_address

	# SHOULD BE GOOD
	def is_command_complete(self):
		status = self.visa_instr.read_stb()
		# print("{0:08b}".format(status))
		if status & 0b00000001 == 0b00000001:
			return True
		elif status & 0b00000001 == 0b00000000:
			return False
		else:
			print("ERROR: Bit 0 of STB is neither 0 or 1 (obviously, coding error!)")
			return RETURN_ERROR

	# SHOULD BE GOOD
	def is_data_available(self):
		status = self.visa_instr.read_stb()
		# print("{0:08b}".format(status))
		if status & 0b10000000 == 0b10000000:
			return True
		elif status & 0b10000000 == 0b00000000:
			return False
		else:
			print("ERROR: Bit 7 of STB is neither 0 or 1 (obviously, coding error!)")
			return RETURN_ERROR

	def is_overload(self):
		status = self.visa_instr.read_stb()
		# print("{0:08b}".format(status))
		if status & 0b00010000 == 0b00010000:
			return True
		elif status & 0b00010000 == 0b00000000:
			return False
		else:
			print("ERROR: Bit 4 of STB is neither 0 or 1 (obviously, coding error!)")
			return RETURN_ERROR

	def is_unlock(self):
		status = self.visa_instr.read_stb()
		# print("{0:08b}".format(status))
		if status & 0b00001000 == 0b00001000:
			return True
		elif status & 0b00001000 == 0b00000000:
			return False
		else:
			print("ERROR: Bit 3 of STB is neither 0 or 1 (obviously, coding error!)")
			return RETURN_ERROR


	# def is_data_available_and_ready(self):
	# 	status = self.visa_instr.read_stb()
	# 	# print("{0:08b}".format(status))
	# 	if status & 0b10000001 == 0b10000001:
	# 		return True
	# 	# elif status & 0b10000001 == 0b10000000 | status & 0b10000001 == 0b00000001):
	# 	# 	return False
	# 	else:
	# 		return False
	# 		# print("ERROR: Bit 7 of STB is neither 0 or 1 (obviously, coding error!)")
	# 		# return RETURN_ERROR


	def get_sensitivity(self):
		code = self.query("SEN")
		self.fullscale = [x["sensitivity"] for x in self.fullscale_codes if x["code"] == int(code)][0]
		return self.fullscale


	def set_sensitivity(self, voltage, vernier=False):
		"""
		Sets sensitivity to range immediately above the value given in parameter
		TODO unless vernier=True, then sensistivity is set exactly as given as parameter
		"""
		try:
			if isinstance(voltage,float):
				if voltage < 3.:
					if not vernier:
						code = self.write('SEN {}'.format(min([s["code"] for s in self.fullscale_codes if s["sensitivity"] >= voltage])))
						self.fullscale = [x["sensitivity"] for x in self.fullscale_codes if x["code"] == int(code)][0]
					else:
						raise(NotImplementedError)
				else:
					raise(ValueError)
			else:
				raise(TypeError)
		except:
			return RETURN_ERROR
		else:
			return RETURN_NO_ERROR

	def filtering(self, type=None):
		possible_values = ['FLAT', 'NOTCH', 'LP', 'BP']
		if type is None:
			out = self.query("FLT")
			try:
				out = int(out)
			except:
				return RETURN_ERROR
			else:
				return possible_values[out]
		else:
			if isinstance(type,str):
				if type.upper() in possible_values:
					self.write(f"FLT {possible_values.index(type)}")
				else:
					print(f"Only {possible_values} are possible")
					return RETURN_NO_ERROR
			else:
				raise ValueError(f"type can be either None (to query) or a string in {possible_values} (to set) ")
				return RETURN_ERROR

	def dynamic_range(self, type=None):
		possible_values = ['HI STAB', 'NORM', 'HI RES']
		if type is None:
			out = self.query("DR")
			try:
				out = int(out)
			except:
				return RETURN_ERROR
			else:
				return possible_values[out]
		else:
			if isinstance(type,str):
				if type.upper() in possible_values:
					self.write(f"DR {possible_values.index(type)}")
				else:
					print(f"Only {possible_values} are possible")
					return RETURN_NO_ERROR
			else:
				raise ValueError(f"Type can be either None (to query) or a string in {possible_values} (to set) ")
				return RETURN_ERROR


	def auto_sensitivity(self):
		"""
		Sets sensitivity automagically (AS command) so that the magnitude output lies between 25% and 95%
		Returns nothing (use get_sensitivity() to check)
		"""
		self.write('AS')

	def auto_tune(self):
		"""
		Sets sensitivity automagically (AS command) so that the magnitude output lies between 25% and 95%
		Returns nothing (use get_sensitivity() to check)
		"""
		self.write('ATS')


	def get_timeconstant(self):
		code = self.query("TC")
		self.timeconstant = [x["timeconstant"] for x in self.timeconstant_codes if x["code"] == int(code)][0]
		return self.timeconstant

	def set_timeconstant(self, timeconstant):
		"""
		Sets timeconstant to range immediately above the value given in parameter
		"""
		try:
			if isinstance(timeconstant,float):
				if timeconstant < 3.:
					code = self.write('TC {}'.format(min([s["code"] for s in self.timeconstant_codes if s["timeconstant"] >= timeconstant])))
					self.fullscale = [x["timeconstant"] for x in self.timeconstant_codes if x["code"] == int(code)][0]
				else:
					raise(ValueError)
			else:
				raise(TypeError)
		except:
			return RETURN_ERROR
		else:
			return RETURN_NO_ERROR



	def get_frequency(self):
		"""
		returns the frequency of reference oscillator
		(whether internal, external / manual or tracked)
		"""
		out = self.query("FRQ")
		return np.float(out)/1000

	def auto_phase(self):
		"""
		equivalent to pressing Auto Phase on front panel
		"""
		self.write("AQN")

	def auto_measure(self):
		"""
		equivalent to pressing Auto Measure on front panel
		"""
		self.write("ASM")

	def dB_per_octave(self, slope=12):
		"""
		sets output filter to 12dB per decade
		"""
		try:
			assert slope==6 or slope==12
		except:
			return RETURN_ERROR
		else:
			self.write("XDB {}".format(1 if slope is 6 else 1))
			return RETURN_NO_ERROR


	def get_x(self):
		out = self.query("X")
		return np.float(out)*self.fullscale/10000

	def get_y(self):
		out = self.query("Y")
		return np.float(out)*self.fullscale/10000

	def get_phase_degrees(self):
		out = self.query("PHA")
		return np.float(out)/1000

	def get_phase_radians(self):
		out = self.query("PHA")
		return np.float(out)/1000 * np.pi/180

	def get_complex(self):
		out = self.query("XY").split(self.value_separator)
		return np.float(out[0])*self.fullscale/10000 + 1j*np.float(out[1])*self.fullscale/10000

	def get_complex_(self):
		out = self.query("MP").split(self.value_separator)
		return np.float(out[0])*self.fullscale/10000 * np.exp(1j*np.float(out[1])*np.pi/180/1000)


	def get_x_quick(self):
		"""
		Gets X value with minimal overhead, for frequent readings. Less reliability checks but quicker.
		"""
		self.visa_instr.write_raw("*")
		out = self.visa_instr.read()
		return np.float(out)*self.fullscale/10000


	def reference_internal(self, is_internal=None):
		"""
		Queries (None) or sets whether the reference signal is external (True) or internal (False).
		"""
		if is_internal is None:
			out = self.query("IE")
			try:
				out = bool(int(out))
			except:
				return RETURN_ERROR
			else:
				return out
		else:
			try:
				assert (is_internal is True) or (is_internal is False)
			except AssertionError:
				raise ValueError("is_internal can be either None (query) or True or False (set) ")
				return RETURN_ERROR
			else:
				self.write(f"IE {1 if is_internal else 0}")
				return RETURN_NO_ERROR


	def harmonic_mode(self, is_harmonic_mode=None):
		"""
		Queries (None) or sets whether the detection on the first harmonic of the reference signal is ON (True) or OFF (False).
		"""
		if is_harmonic_mode is None:
			out = self.query("F2F")
			try:
				out = bool(int(out))
			except:
				return RETURN_ERROR
			else:
				return out
		else:
			try:
				assert (is_harmonic_mode is True) or (is_harmonic_mode is False)
			except AssertionError:
				raise ValueError("is_harmonic_mode can be either None (query) or True or False (set) ")
				return RETURN_ERROR
			else:
				self.write(f"F2F {1 if is_harmonic_mode else 0}")
				return RETURN_NO_ERROR

	def filter_mode(self, is_auto=None):
		"""
		Queries (None) or sets whether the filter frequency is automatic (True) or manual (False).
		"""
		if is_auto is None:
			out = self.query("ATC")
			try:
				out = bool(int(out))
			except:
				return RETURN_ERROR
			else:
				return out
		else:
			try:
				assert (is_auto is True) or (is_auto is False)
			except AssertionError:
				raise ValueError("is_auto can be either None (query) or True or False (set) ")
				return RETURN_ERROR
			else:
				self.write(f"ATC {1 if is_auto else 0}")
				return RETURN_NO_ERROR


	def why_overload(self):
		if self.isoverload():
			out = self.query("N")
			try:
				isover = int(out)
			except:
				return RETURN_ERROR
			else:
				over_causes={
				"not used":0b00000001,
				"current mode set to 10**8 A/V":0b00000010,
				"current mode set to 10**6 A/V":0b00000100,
				"Y channel output overload":0b00001000,
				"X channel output overload":0b00010000,
				"PSD overload":0b00100000,
				"input overload":0b01000000,
				"reference unlock":0b10000000
				}
				overload_causes = []
				for o in over_causes.values():
					if isover & o == o:
						try:
							overload_causes.append([k for k in over_causes.keys() if over_causes[k]==o].pop())
						except IndexError:
							print("No overload error found in Overload Byte but overload bit in Status Byte is ON... Why ?")
							pass
				return overload_causes
		else:
			return None

