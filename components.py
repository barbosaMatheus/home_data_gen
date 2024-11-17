"""
Code for sensor objects
"""
import numpy as np
from abc import ABC, abstractmethod
from typing import Literal

PASSIVE_SENSOR_STYLE = Literal["motion","door"]

BAD_SENSOR_VAL = -999999.0
MAX_DEG_F_CHANGE_PER_MILLISEC = 1e-6

class __Sensor__(ABC):
    @abstractmethod
    def sample(self, _):
        pass

    @abstractmethod
    def trigger(self):
        passs

class __TempSensor__(__Sensor__):
    def __init__(self, fail_rate: float, start_temp: float):
        self.fail_rate = fail_rate
        self.prev_temp = start_temp
    
    def sample(self, delta_time: int):
        # check fail rate first
        # note, fails do not update previous val
        if np.random.random_sample() <= self.fail_rate:
            # if fails, 50/50 chance for bad read or NaN
            if np.random.random_sample <= 0.5:
                return np.nan
            else:
                return BAD_SENSOR_VAL
        # if no fail, get random sample change from previous temp
        else:
            max_abs_change = delta_time * MAX_DEG_F_CHANGE_PER_MILLISEC
            temp_change = np.random.uniform(low=-1.0*max_abs_change, 
                                            high=max_abs_change)
            next_temp = self.prev_temp + temp_change
            self.prev_temp = next_temp
            return next_temp
        
class __PassiveSensor__(__Sensor__):
    def __init__(self, pings_per_cycle: int, style: PASSIVE_SENSOR_STYLE):
        self.pings_per_cycle = pings_per_cycle
        self.pings = 0
        self.style = style

    def sample(self, kappa: float):
        self.pings = (self.pings + 1) % self.pings_per_cycle
        if self.pings == 1:
            test_value = np.random.random()
            if test_value <= kappa:
                return int(np.random.uniform(low=3100, high=5000))
            else:
                return int(np.random.uniform(low=0, high=1800))
        else:
            return int(np.random.uniform(low=1801, high=2900))
        

