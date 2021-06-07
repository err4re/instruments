import instr
from time import sleep
print('i am imported')
class K2182a(instr.Instr):
    def __init__(self, visa_name):
        super(K2182a, self).__init__(visa_name)
        self.visa_instr.read_termination = '\r'
        self.visa_instr.write_termination = '\r'
        self.visa_instr.baud_rate = 9600
        self.visa_instr.chunk_size = 2048*8

        self.channel='CHANNEL1'
        self.mes_range='AUTO'
        self.rate=5
        self.analog_filter_status='OFF'
        self.digital_filter_status='OFF'
        self.digital_filter_window=0.01
        self.digital_filter_count=10
        self.digital_filter_type='MOVING'



        self.write("*RST")
        self.write( ":SENSE:FUNC 'VOLT'" )
        self.write( ":SENSE:CHANNEL 1" )
    
    
    def set_channel(self,channel_number):
        if channel_number==1:
            self.channel='CHANNEL1'
            self.write( ":SENSE:CHANNEL 1")
        elif channel_number==2:
            self.channel='CHANNEL2'
            self.write( ":SENSE:CHANNEL 2")
        elif channel_number==0:
            self.channel='CHANNEL0'
            self.write( ":SENSE:CHANNEL 0")
        else:
            print('incorrect channel number')

    def set_range(self,mes_range):
        self.mes_range=mes_range
        if self.mes_range=='AUTO':
            self.write("SENSE:VOLTAGE:{0}:RANGE:AUTO On".format(self.channel))
        else:
            self.write("SENSE:VOLTAGE:{0}:RANGE:UPPER {1}".format(self.channel,self.mes_range)) 


    # use integer values of line period
    def set_integration_time(self,NPLC):
        self.rate=NPLC
        self.write(":SENSE:VOLTAGE:NPLCycles {0}".format(NPLC))    
           
    def set_analog_filtering(self,Status):
             self.analog_filter_status=Status
             self.write(":SENSE:VOLTAGE:{0}:LPASS {1}".format(self.channel,Status))

    def set_digital_filtering(self,Status,DIG_window=0.01,DIG_count=10,DIG_type='MOVING'):
             self.digital_filter_status=Status
             self.write(":SENSE:VOLTAGE:{0}:DFILTER:STATE {1}".format(self.channel,Status))
             if Status=='ON':
                self.digital_filter_window=DIG_window
                self.digital_filter_count=DIG_count
                self.digital_filter_type=DIG_type
                self.write(":SENSE:VOLTAGE:{0}:DFILTER:WINDOW {1}".format(self.channel,DIG_window))
                self.write(":SENSE:VOLTAGE:{0}:DFILTER:COUNT {1}".format(self.channel,DIG_count))
                self.write(":SENSE:VOLTAGE:{0}:DFILTER:TCONTROL {1}".format(self.channel,DIG_type))



    def get_voltage(self,iterations=1):
        self.write("INITIATE:CONT OFF")
        result=0
        for i in range(iterations):
            tmp=(self.query("READ?").split('E'))
            result+=float(tmp[0])*10**int(tmp[1])
        return(result/iterations)



    def get_last_error(self):
        return self.query("SYST:ERR?")

    def reset(self):
        self.write("*RST")
        self.write("*CLS")