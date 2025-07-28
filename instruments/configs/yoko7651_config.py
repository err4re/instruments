from dataclasses import dataclass
from typing import List, Union
import numpy as np

@dataclass
class YokoCurrSweepConfig:
    """
    Configuration class for using Yokogawa 7651 as a current source.

    Attributes:
        currents (List[float]): A list of currents (in Amperes) to be sourced by the Yoko.
        current_range (float): Current range needed to iterate through currents in currents list.
    """
    currents: Union[np.ndarray[np.float64], list[float]]
    sweep_length: int = None
    #wait in seconds after current change
    wait: float = 0.2

    current_range: float = None
    

    def __post_init__(self):
        self.sweep_length = len(self.currents)
        
        if self.current_range == None:
            self.current_range = max(abs(self.currents))

        # Check if the current range can cover all the currents in the list
        if any(abs(current) > self.current_range for current in self.currents):
            max_abs_current = max(abs(current) for current in self.currents)
            raise ValueError(f"The current range of {self.current_range} A is not sufficient "
                             f"to supply the maximum absolute current of {max_abs_current} A "
                             "in the currents list.")
        


@dataclass
class YokoVoltSweepConfig:
    """
    Configuration class for using Yokogawa 7651 as a voltage source.

    Attributes:
        voltages (List[float]): A list of voltages (in Volts) to be sourced by the Yoko.
        voltage_range (float): Voltage range needed to iterate through voltages in voltages list.
    """
    voltages: Union[np.ndarray[np.float64], list[float]]
    sweep_length: int = None
    #wait in seconds after voltage change
    wait: float = 0.2

    voltage_range: float = None
    

    def __post_init__(self):
        self.sweep_length = len(self.voltages)
        
        if self.voltage_range == None:
            self.voltage_range = max(abs(self.voltages))

        # Check if the current range can cover all the currents in the list
        if any(abs(voltage) > self.voltage_range for voltage in self.voltages):
            max_abs_voltage = max(abs(voltage) for voltage in self.voltages)
            raise ValueError(f"The voltage range of {self.voltage_range} V is not sufficient "
                             f"to supply the maximum absolute voltage of {max_abs_voltage} V "
                             "in the voltages list.")
