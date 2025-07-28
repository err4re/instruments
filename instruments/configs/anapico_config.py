from dataclasses import dataclass
import numpy as np


@dataclass
class AnaFreqSweepConfig:
    """
    Configuration class for Anapico frequency sweeps.

    Attributes:
        power_mode (str): Mode of power setting (e.g., 'FIX').
        power (float): Power level in dBm.
        start_frequency (float): Start frequency of the sweep in Hz.
        stop_frequency (float): Stop frequency of the sweep in Hz.
        num_points (int): Number of points in the sweep.
        sweep_delay (float): Delay between sweep points in seconds.
        sweep_count (int): Number of sweeps to perform.
        trigger_source (str): Trigger source (e.g., 'EXTernal').
        trigger_type (str): Trigger type (e.g., 'POINt').
        trigger_slope (str): Trigger slope (e.g., 'POSitive').
        continuous_mode (str): Continuous mode setting (e.g., 'ON' or 'OFF').
        frequency_mode (str): Frequency mode for the sweep (e.g., 'SWEep').
    """
    
    num_points: int = None  # Number of points in the sweep
    power: float = None  # Power level in dBm
    channel: int = 1 # Channel to output frequenct sweep on
    start_frequency: float = None # Start frequency in Hz
    stop_frequency: float = None # Stop frequency in Hz
    center_frequency: float = None
    span: float = None
    frequencies: np.ndarray = None
    sweep_dwell_time: float = 0.01 # in seconds
    sweep_delay: float = 0  # Delay between sweep points in seconds
    sweep_count: int = 1  # Number of sweeps
    power_mode: str = "FIX"
    trigger_source: str = "EXTernal"
    trigger_type: str = "POINt"
    trigger_slope: str = "POSitive"
    continuous_mode: str = "ON"
    frequency_mode: str = "SWEep"
    powers: np.ndarray[np.float64] = None
    power_sweep_length: int = None

    dummy: bool = True
    dummy_frequency: float = None # extra start frequency that will get skipped due to double triggering at beginning, to actually start at start frequency


    def __post_init__(self):
        # Calculate and validate frequency parameters
        self._validate_and_calculate_frequencies()
        self._validate_power_sweep()

    def _validate_and_calculate_frequencies(self):
        # Validate and calculate frequencies
        if self.center_frequency and self.span:
            self.start_frequency = self.center_frequency - self.span / 2
            self.stop_frequency = self.center_frequency + self.span / 2

            self.frequencies = self._sweep_frequencies()

        elif self.start_frequency and self.stop_frequency:
            self.span = self.stop_frequency - self.start_frequency
            self.center_frequency = self.start_frequency + self.span / 2

            self.frequencies = self._sweep_frequencies()

        else:
            raise ValueError("Either center frequency and span or start and stop frequencies must be provided.")
        
    def _validate_power_sweep(self):
        #in case of a power sweep set length
        if self.powers is not None:
            
            #check maximum power here in the future?

            self.power_sweep_length = len(self.powers)
            self.power = self.powers[0]
        

    def _sweep_frequencies(self) -> np.ndarray:
        if self.dummy:
            frequencies = np.linspace(self.start_frequency, self.stop_frequency, self.num_points)
            self.dummy_frequency = self.start_frequency - frequencies[1] + frequencies[0]
        else:
            frequencies = np.linspace(self.start_frequency, self.stop_frequency, self.num_points)

        return frequencies
    

    def change_center_frequency(self, center_frequency):

        self.start_frequency = None
        self.stop_frequency = None
        self.center_frequency = center_frequency

        self._validate_and_calculate_frequencies()
        

@dataclass
class AnaExtTrigInConfig:
    """
    Configuration class for Anapico external trigger in.

    Attributes:
        trigger_source (str): Trigger source can be IMMediate|KEY|EXTernal|BUS
        trigger_type (str): Trigger type can be NORMal|GATE|POINt
        trigger_slop (str): Trigger slope can be POSitive|NEGative|NP|PN
        continuous_initiate (bool): CONTinuous True, repeatedly accepts trigger events
    """
    trigger_source: str = "EXTernal"
    trigger_type: str = "POINt"
    trigger_slope: str = "POSitive"
    continuous_initiate: bool = True

    # choice between external trigger in and external trigger out in the future?
    # for now external trigger in is the default