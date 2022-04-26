from instruments import instr
import numpy as np


class Fsva(instr.Instr):
  def __init__(self, visa_name, visa_library=''):
    super(Fsva, self).__init__(visa_name, visa_library)
    self.visa_instr.read_termination = '\n'
    self.visa_instr.timeout = 5000
    #        self.write("ROSCillator EXTernal")

  @property
  def unit(self):
    return self.query('UNIT:POW?')

  @unit.setter
  def unit(self, unit):
    allowed_units = 'DBM','V','A','W','DBPW','WATT','DBPT','DBUV','DBMV','VOLT','DBUA','AMPere'
    if unit in allowed_units:
      return self.query('UNIT:POW?')
    else:
      print('WARNING: invalid paremeter. No change.')
      return None

  def get_trace(self, tracenum=1):
    self.write('FORM REAL,32')
    # JLS : float (4 bytes) resolution is not enough for narrow-band
    #f = self.visa_instr.query_binary_values(f'TRAC:X? TRACE{tracenum:d}', datatype='f', is_big_endian=False)
    f = self.get_frequencies()
    s = self.visa_instr.query_binary_values(f'TRAC? TRACE{tracenum:d}', datatype='f', is_big_endian=False)
    return np.array(f), np.array(s)

  def get_frequencies(self):
    #self.write('FORM ASCII')
    fmin = self.f_start
    fmax = self.f_stop
    N = self.nb_points
    #data = np.array(data_str.rstrip().split(',')).astype('float64')
    return np.linspace(fmin,fmax,N)

  def sweep_now(self):
    self.write('INIT')

  @property
  def sweep_time(self):
    return float(self.query('SWE:TIME?'))

  @sweep_time.setter
  def sweep_time(self, time):
    self.write(f'SWE:TIME {time}s')

  @property
  def VBW(self):
    return float(self.query('BWID:VID?'))


  @property
  def RBW(self):
    return float(self.query('BWID?'))

  @property
  def nb_points(self):
    return int(self.query('SWE:POIN?'))

  @property
  def averaging(self):
    is_averaging_on = bool(self.query('AVER?'))
    if is_averaging_on:
      return int(self.query('AVER:COUN?'))
    else:
      return 1

  @property
  def f_center(self):
    return float(self.query('FREQ:CENT?'))

  @f_center.setter
  def f_center(self, f_center):
      self.write(f'FREQ:CENT {f_center}')

  @property
  def f_span(self):
    return float(self.query('FREQ:SPAN?'))

  @f_span.setter
  def f_span(self, f_span):
      self.write(f'FREQ:SPAN {f_span}')

  @property
  def f_start(self):
    return float(self.query('FREQ:STAR?'))

  @property
  def f_stop(self):
    return float(self.query('FREQ:STOP?'))

  def running(self):
    if '1' == self.query('*OPC?'):
      return False
    else:
      return True