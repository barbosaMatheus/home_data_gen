"""
Contains object that generates simulated home monitoring data
"""
import pandas as pd
from input_scrubbing import *
import datetime
from components import __TempSensor__, __PassiveSensor__

SUNRISE = "06:00:00"
SUNSET = "18:00:00"
YEAR_LEN_DAYS = 365.25
START_TEMP_F = 70.0
DOOR_MOTION_SENSOR_CYCLE = 30000

class HomeMonitoringDataGen():
    """
    Generates simulated data for a home monitorting system. Given a
    start date, a number of days to sim, minor cycle length, temp bias
    and sensor fail rate.

    Attributes:
        start_date_str (str): start date string, must be convertible to iso datetime.
        num_days (int): number of days to sim.
        minor_cycle_len (int): minor cycle lenght, in milliseconds. Which is how
            often the simulation updates at its fastest rate.
        temp_bias (float): bias for temperature on the side of the house with the
            Sun during the day, as well as the temperature drop at sunset.
        sensor_fail_rate (float): rate at which the temperature, humidity and CO2
            sensors fail, giving missing or incorrect data.
    """
    def __init__(self, start_date_str: str, num_days: int, minor_cycle_len: int, 
                 temp_bias: float, sensor_fail_rate: float):
        self.start_date = scrub_date_str(start_date_str, default_x="2024-06-15")
        self.num_days = scrub_pos_int(num_days, default_x=1000)
        self.minor_cycle = scrub_pos_int(minor_cycle_len, default_x=500)
        self.temp_bias = scrub_temp_f(temp_bias)
        self.sensor_fail_rate = scrub_proportion(x=sensor_fail_rate, default_x=0.0)
        self.__is_built__ = False

    # build components
    def __build__(self, force=False):
        if not self.__is_built__ and not force:
            # temp sensors
            self.t1 = __TempSensor__(self.sensor_fail_rate, START_TEMP_F)
            self.t2 = __TempSensor__(self.sensor_fail_rate, START_TEMP_F)
            
            # door sensors
            self.d1 = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle, style="door")
            self.d2 = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle, style="door")
            self.d3 = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle, style="door")

            # motion detectors
            self.m1 = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle, style="motion")
            self.m2 = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle, style="motion")
            self.m3 = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle, style="motion")

            # CO2 sensors
            # smoke detectors
            self.__is_built__ = True

    def start(self, name: str, reset: bool = False):
        """
        Starts the simulation process, with the option to reset,
            which forces a build, regenerating the components.
        
        Args:
            name (str): name which will pre-append to the current simulation
                output files.
            reset (bool): if True, will force build the object, which
                resets the components.
        """
        self.__build__(reset)