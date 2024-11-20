"""
Code for sensor objects
"""
import numpy as np
from abc import ABC, abstractmethod
from typing import Literal

PASSIVE_SENSOR_STYLE = Literal["motion","door"]
SUNLIGHT_STATE = Literal["direct","indirect","night"]

BAD_TEMP_F = -999999.0
BAD_PPM = 99_999
OCCUPANT_PPM_SCALE = 100
BAD_HUMIDITY = 999.999
MAX_DEG_F_CHANGE_PER_MILLISEC = 1e-6
TICKS_PER_ALRM_BATT_LIFE = 20_736_000_000
TICKS_PER_ALRM_BATT_OFFSET = 2_592_000_000.0
SMOKE_CHANCE_PER_TICK = 1.27e-10
LOGIC_ONE_MV_MIN = 3100
LOGIC_ZERO_MV_MAX = 1800
MV_MAX = 5000
MV_MIN = 0

class __Sensor__(ABC):
    @abstractmethod
    def sample(self, _):
        pass

class __TempSensor__(__Sensor__):
    def __init__(self, fail_rate: float, start_temp: float, sunlight: SUNLIGHT_STATE, bias: float):
        self.fail_rate = fail_rate
        self.prev_temp = start_temp
        self.bias = bias
        # offset start temp for sun position
        offset = 0
        match sunlight:
            case "direct":
                offset = bias
            case "indirect":
                offset = 0
            case "night":
                offset = -1*bias
        self.prev_temp += offset
    
    def night_cycle(self):
        self.prev_temp -= self.bias

    def day_cycle(self):
        self.prev_temp += self.bias

    def sample(self, delta_time: int):
        # check fail rate first
        # note, fails do not update previous val
        if np.random.random_sample() <= self.fail_rate:
            # if fails, 50/50 chance for bad read or NaN
            if np.random.random_sample() <= 0.5:
                return np.nan
            else:
                return BAD_TEMP_F
        
        # if no fail, get random sample change from previous temp
        else:
            # calculate change
            max_abs_change = delta_time * MAX_DEG_F_CHANGE_PER_MILLISEC
            temp_change = np.random.uniform(low=-1.0*max_abs_change, 
                                            high=max_abs_change)
            
            # accumulate change
            next_temp = self.prev_temp + temp_change
            self.prev_temp = next_temp
            return next_temp
        
class __PassiveSensor__(__Sensor__):
    def __init__(self, pings_per_cycle: int, style: PASSIVE_SENSOR_STYLE):
        self.pings_per_cycle = pings_per_cycle or 100
        self.pings = 0
        self.style = style

    def sample(self, kappa: float):
        """
        Samples this instance of a passive sensor

        Args:
            kappa (float): chance of the sensor triggering [0,1)
        
        Returns:
            int: value in mV indicating whether the sensor tripped
            (>= 3100) or not (<= 1800). In between values indicate
            a neutral state in between update cycles.
        """
        self.pings = (self.pings + 1) % self.pings_per_cycle
        if self.pings == 1:
            test_value = np.random.random()
            if test_value < kappa:
                return int(np.random.uniform(low=LOGIC_ONE_MV_MIN, high=MV_MAX))
            else:
                return int(np.random.uniform(low=MV_MIN, high=LOGIC_ZERO_MV_MAX))
        else:
            return int(np.random.uniform(low=LOGIC_ZERO_MV_MAX+1, high=LOGIC_ONE_MV_MIN-1))
        
class __Co2Sensor__(__Sensor__):
    def __init__(self, cycle_delays: int, n_occupants: int,
                 mean_ppm: float = 700.0, std_ppm: float = 270.0):
        self.cycle_delays = cycle_delays
        self.n_occupants = n_occupants
        self.mean_ppm = mean_ppm
        self.std_ppm = std_ppm

    def __get_ppm__(self):
        base_val = int(np.random.normal(loc=self.mean_ppm, scale=self.std_ppm))
        if base_val < 0:
            base_val = 0
        occupant_shift = np.random.choice(self.n_occupants+1)*OCCUPANT_PPM_SCALE
        return int(base_val + occupant_shift)

    def sample(self, cycle: int):
        if (cycle % self.cycle_delays) == 0:
            return self.__get_ppm__()
        else:
            return BAD_PPM
    
class __HumiditySensor__(__Sensor__):
    def __init__(self, cycle_delays: int, mean_humidity: float = 40.0, 
                 std_humidity: float = 9.0):
        self.cycle_delays = cycle_delays
        self.mean_humidity = mean_humidity
        self.std_humidity = std_humidity

    def __get_humidity__(self):
        base_val = np.random.normal(loc=self.mean_humidity, scale=self.std_humidity)
        if base_val < 0:
            base_val = 0
        return base_val

    def sample(self, cycle: int):
        if (cycle % self.cycle_delays) == 0:
            return self.__get_humidity__()
        else:
            return BAD_HUMIDITY
        
class __SmokeDetector__(__Sensor__):
    def __init__(self, minor_cycle_len: int):
        self.minor_cycle_len = minor_cycle_len
        self.smoke_chance = SMOKE_CHANCE_PER_TICK * minor_cycle_len
        self.__calc_battery_life__()
        self.cycles = 0

    def __calc_battery_life__(self):
        base = TICKS_PER_ALRM_BATT_LIFE / self.minor_cycle_len
        offset = int(np.random.uniform(low=0.0, high=TICKS_PER_ALRM_BATT_OFFSET))
        self.battery_life = base + offset
    
    def sample(self):
        self.cycles += 1
        status = {"battery_dead": False, "smoke": False}
        if self.cycles == self.battery_life:
            status["battery_dead"] = True
            self.__calc_battery_life__()
            self.cycles = 0
        status["smoke"] = np.random.random() <= self.smoke_chance
        return status