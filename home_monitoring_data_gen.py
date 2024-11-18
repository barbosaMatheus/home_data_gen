"""
Contains object that generates simulated home monitoring data
"""
import pandas as pd
from input_scrubbing import *
import datetime
import os
from components import __TempSensor__, __PassiveSensor__, __Co2Sensor__, __HumiditySensor__, __SmokeDetector__

SUNRISE = "06:00:00"
SUNSET = "18:00:00"
YEAR_LEN_DAYS = 365.25
START_TEMP_F = 70.0
DOOR_MOTION_SENSOR_CYCLE = 30_000
CO2_SENSOR_CYCLE_DELAY = 150
HUMIDITY_SENSOR_DELAY = 100
TICKS_PER_DAY = 86_400_000
TICK_SCALE = 1_000

class HomeMonitoringDataGen():
    """
    Generates simulated data for a home monitorting system. Given a
    start date, a number of days to sim, minor cycle length, temp bias
    and sensor fail rate.

    Attributes:
        start_date_str (str): start date string, must be convertible to iso datetime.
        num_days (int): number of days to sim.
        num_occupants (int) number of occupants in the home.
        minor_cycle_len (int): minor cycle lenght, in milliseconds. Which is how
            often the simulation updates at its fastest rate.
        temp_bias (float): bias for temperature on the side of the house with the
            Sun during the day, as well as the temperature drop at sunset.
        sensor_fail_rate (float): rate at which the temperature, humidity and CO2
            sensors fail, giving missing or incorrect data.
    """
    def __init__(self, start_date_str: str, num_days: int, num_occupants: int, 
                 minor_cycle_len: int, temp_bias: float, sensor_fail_rate: float):
        self.start_date = scrub_date_str(start_date_str, default_x="2024-06-15")
        self.num_days = scrub_pos_int(num_days, default_x=1000)
        self.num_occupants = scrub_pos_int(num_occupants, default_x=1)
        self.minor_cycle_len = scrub_pos_int(minor_cycle_len, default_x=500)
        self.temp_bias = scrub_temp_f(temp_bias)
        self.sensor_fail_rate = scrub_proportion(x=sensor_fail_rate, default_x=0.0)
        self.total_cycles = (TICKS_PER_DAY/self.minor_cycle_len)*self.num_days
        self.__is_built__ = False

    # build components
    def __build__(self, force=False):
        if not self.__is_built__ and not force:
            # sensors list
            self.sensors = {}

            # temp sensors
            self.sensors["t1"] = __TempSensor__(self.sensor_fail_rate, START_TEMP_F)
            self.sensors["t2"] = __TempSensor__(self.sensor_fail_rate, START_TEMP_F)
            
            # door sensors
            self.sensors["d1"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="door")
            self.sensors["d2"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="door")
            self.sensors["d3"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="door")

            # motion detectors
            self.sensors["m1"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="motion")
            self.sensors["m2"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="motion")
            self.sensors["m3"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="motion")

            # CO2 sensor
            self.sensors["c1"] = __Co2Sensor__(CO2_SENSOR_CYCLE_DELAY, self.num_occupants)

            # humidity sensor
            self.sensors["h1"] = __HumiditySensor__(HUMIDITY_SENSOR_DELAY)
            
            # smoke detector
            self.sensors["s1"] = __SmokeDetector__(self.minor_cycle_len)

            # confirm build
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
        
        filenames = {}
        
        tag = datetime.datetime.now().replace(" ","T").replace(":","_").replace(".","_")
        topdir = f"{name}_{tag}"
        if not os.path.isdir(topdir):
            os.mkdir(topdir)
        
        self.current_datetime = self.start_date
        for i in range(self.total_cycles):
            print(f"Cycle {i}: {str(self.current_datetime)}")
            self.current_datetime += datetime.timedelta(milliseconds=self.minor_cycle_len)
            