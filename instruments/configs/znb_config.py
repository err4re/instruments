from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class ZnbLinConfig:
    """
    Configuration class for a linear VNA sweep.

    Attributes:
        center_frequency (float): Center frequency of the sweep in Hz.
        span (float): Frequency span of the sweep in Hz.
        start_frequency (float): Start frequency of the sweep in Hz.
        stop_frequency (float): Stop frequency of the sweep in Hz.
        bandwidth (float): Bandwidth of the sweep in Hz.
        num_points (int): Number of points in the sweep.
        num_averages (int): Number of averages for the sweep.
        power (float): Power level for the sweep in dBm.
        powers (np.ndarray[np.float64]): Power levels in case of a power sweep in dBm.
    """
    center_frequency: float = None
    span: float = None
    start_frequency: float = None
    stop_frequency: float = None
    bandwidth: float = None
    num_points: int = None
    num_averages: int = None
    average_mode: str = 'MOVing'
    power: float = None
    powers: np.ndarray[np.float64] = None
    power_sweep_length: int = None

    def __post_init__(self):
        # Calculate and validate frequency parameters
        self._validate_and_calculate_frequencies()
        self._validate_power_sweep()

        # Validate other parameters
        if self.bandwidth is None:
            raise ValueError("Bandwidth is not set.")
        if self.num_points is None:
            raise ValueError("Number of points is not set.")
        if self.num_averages is None:
            raise ValueError("Number of averages is not set.")        
        if self.power is None:
            raise ValueError("Power level is not set.")
        
    def _validate_power_sweep(self):
        #in case of a power sweep set length
        if self.powers is not None:
            
            #check maximum power here in the future?

            self.power_sweep_length = len(self.powers)
            self.power = self.powers[0]


    def _validate_and_calculate_frequencies(self):
        # Validate and calculate frequencies
        if self.center_frequency and self.span:
            self.start_frequency = self.center_frequency - self.span / 2
            self.stop_frequency = self.center_frequency + self.span / 2
        elif self.start_frequency and self.stop_frequency:
            self.span = self.stop_frequency - self.start_frequency
            self.center_frequency = self.start_frequency + self.span / 2
        else:
            raise ValueError("Either center frequency and span or start and stop frequencies must be provided.")

    def __str__(self):
        return (f"Power: {self.power} dBm, "
                f"Center Frequency: {self.center_frequency} Hz, "
                f"Span: {self.span} Hz, "
                f"Start Frequency: {self.start_frequency} Hz, "
                f"Stop Frequency: {self.stop_frequency} Hz, "
                f"Bandwidth: {self.bandwidth} Hz, "
                f"Number of Points: {self.num_points}, "
                f"Number of Averages: {self.num_averages}")
    
@dataclass
class ZnbCWConfig:
    """
    Configuration class for a CW VNA sweep.

    Attributes:
        center_frequency (float): Center frequency of the sweep in Hz.
        bandwidth (float): Bandwidth of the sweep in Hz.
        num_points (int): Number of points in the sweep.
        num_averages (int): Number of averages for the sweep.
        power (float): Power level for the sweep in dBm.
        powers (np.ndarray[np.float64]): Power levels in case of a power sweep in dBm.
    """
    center_frequency: float = None
    bandwidth: float = None
    num_points: int = None
    num_averages: int = None
    average_mode: str = 'MOVing'
    power: float = None
    powers: np.ndarray[np.float64] = None
    power_sweep_length: int = None

    def __post_init__(self):
        # Calculate and validate frequency parameters
        self._validate_power_sweep()

        # Validate other parameters
        if self.bandwidth is None:
            raise ValueError("Bandwidth is not set.")
        if self.num_points is None:
            raise ValueError("Number of points is not set.")
        if self.num_averages is None:
            raise ValueError("Number of averages is not set.")        
        if self.power is None:
            raise ValueError("Power level is not set.")


    def _validate_power_sweep(self):
        #in case of a power sweep set length
        if self.powers is not None:
            
            #check maximum power here in the future?

            self.power_sweep_length = len(self.powers)
            self.power = self.powers[0]


@dataclass
class ZnbSegm:
    """
    Configuration class for a single segment of a segmented VNA sweep.

    Attributes:
        index (int): Index of the segment in a segmented sweep.
        center_frequency (float): Center frequency of the segment in Hz.
        span (float): Frequency span of the segment in Hz.
        start_frequency (float): Start frequency of the segment in Hz.
        stop_frequency (float): Stop frequency of the segment in Hz.
        bandwidth (float): Bandwidth of the segment in Hz.
        num_points (int): Number of points in the segment.
        power (float): Power level for the segment in dBm.
    """
    index: int = None
    center_frequency: float = None
    span: float = None
    start_frequency: float = None
    stop_frequency: float = None
    bandwidth: float = None
    num_points: int = None
    power: float = None

    def __post_init__(self):
        if self.index is None:
            raise ValueError("Segment index is not set.")
        if self.num_points is None:
            raise ValueError("Number of points is not set.")
        elif self.index == 1:
            if self.bandwidth is None:
                raise ValueError("Bandwidth is not set for first segment.")
            if self.power is None:
                raise ValueError("Power for first segment is not set.")

        self._validate_and_calculate_frequencies()

        

    def _validate_and_calculate_frequencies(self):
        if self.center_frequency and self.span:
            self.start_frequency = self.center_frequency - self.span / 2
            self.stop_frequency = self.center_frequency + self.span / 2
        elif self.start_frequency and self.stop_frequency:
            self.span = self.stop_frequency - self.start_frequency
            self.center_frequency = self.start_frequency + self.span / 2
        else:
            raise ValueError("Either center frequency and span or start and stop frequencies must be provided.")


@dataclass
class ZnbSegmConfig:
    """
    Configuration class for a segmented VNA sweep.

    Attributes:
        segments (List[VnaSegm]): List of segment configurations.
        num_segments: Number of segments.
        num_averages (int): Number of averages for the sweep.
    """
    segments: List[ZnbSegm]

    num_segments: int = None

    num_averages: int = None

    num_points: int = None

    
    def __post_init__(self):
        # set number of segments
        if self.num_segments == None:
            self.num_segments = len(self.segments)

        elif self.num_segments != len(self.segments):
            raise ValueError("The number segments in list does not correspond to the set number.")
        
        # check if average is set
        elif self.num_averages == None:
            raise ValueError("Number of averages is not set.")
        
        # total number of points in sweep
        self.num_points = sum([segm.num_points for segm in self.segments])
        
    # functionality to add or remove segments in the future?
        

@dataclass
class ZnbExtTrigOutConfig:
    """
    Configuration class for VNA trigger settings.

    Attributes:
        enable (bool): Enable state of the trigger ('ON' or 'OFF').
        interval (str): Interval of the trigger (e.g., 'SWEep').
        position (str): Position of the trigger (e.g., 'BEFore').
        output_polarity (str): Output polarity of the trigger ('POSitive' or 'NEGative').
    """
    enable: bool = True
    interval: str = "SWEep"
    position: str = "AFTer"
    output_polarity: str = "POSitive"

    def __str__(self):
        return (f"Enable: {self.enable}, "
                f"Interval: {self.interval}, "
                f"Position: {self.position}, "
                f"Output Polarity: {self.output_polarity}")
    

# add CW config in the future?