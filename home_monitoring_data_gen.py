"""
Contains object that generates simulated home monitoring data
"""
# native imports
import datetime
import os

# third party imports
import numpy as np
import pandas as pd

# local imports
from input_scrubbing import *
from components import __TempSensor__, __PassiveSensor__, __Co2Sensor__, __HumiditySensor__
from components import __SmokeDetector__, PASSIVE_SENSOR_STYLE, SUNLIGHT_STATE

SUNRISE_HOUR = 6
SUNSET_HOUR = 18
YEAR_LEN_DAYS = 365.25
START_TEMP_F = 70.0
DOOR_MOTION_SENSOR_CYCLE = 30_000
CO2_SENSOR_CYCLE_DELAY = 150
HUMIDITY_SENSOR_DELAY = 100
TICKS_PER_DAY = 86_400_000
TICK_SCALE = 1_000
MAX_DATAFRAME_SIZE = 100_000_000
SMOKE_ARRAY_DTYPE = np.dtype("u8, u1, u1, u1, u1, U1")

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
        self.temp_sensor_df = pd.DataFrame(columns=["date", "time", "sensor", "packet_id", "payload"])
        self.passive_sensor_df = pd.DataFrame(columns=["datetime", "sensor_id", "voltage"])
        self.humidity_co2_sensor_data = ""
        self.smoke_detector_data = np.zeros(shape=(1,), dtype=SMOKE_ARRAY_DTYPE)

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

    # returns the sunlight state based on current time
    # and sensor position
    def __get_sunlight_state__(self, sensor_pos_east: bool) -> SUNLIGHT_STATE:
        if self.current_datetime.hour >= SUNSET_HOUR:
            return "night"
        elif self.current_datetime.hour == 12:
            return "indirect"
        else:
            sun_pos = ("east" if self.current_datetime.hour < 12 else 
                       "west")
            match (sensor_pos_east, sun_pos):
                case (False, "east"):
                    return "indirect"
                case (False, "west"):
                    return "direct"
                case (True, "east"):
                    return "direct"
                case (False, "east"):
                    return "indirect"
                
    # returns factor used to calculate certain sensors'
    # chances of triggering
    def __get_sensor_kappa__(self, style: PASSIVE_SENSOR_STYLE = "motion"):
        sundown = self.current_datetime.hour > SUNSET_HOUR
        match (style, sundown):
            case ("motion", False): # motion sensor during the day
                return 24.0
            case ("motion", True):  # motion sensor during the night
                return 6.0
            case ("door", False):   # door sensor during the day
                return 4.0
            case ("door", True):    # door sensor during the night
                return 1.0

    def process_temp_sensor(self, sensor, sensor_name: str, ieee_encoded: bool = False):
        sunlight_state = self.__get_sunlight_state__(sensor_pos_east=(sensor_name == "t2"))
        # sample the sensor
        temp = (__TempSensor__)(sensor).sample(self.minor_cycle_len, 
                                               sunlight_state, self.temp_bias)
        #
        # TODO: store the data


    def process_passive_sensor(self, sensor):
        # get kappa
        kappa = self.__get_sensor_kappa__((__PassiveSensor__)(sensor).style)
        # sample the sensor
        voltage = (__PassiveSensor__)(sensor).sample(kappa)
        # TODO: store the data

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
        # build and reset if needed
        self.__build__(reset)
                
        # create the top directory
        tag = datetime.datetime.now().replace(" ","T").replace(":","_").replace(".","_")
        topdir = f"{name}_{tag}"
        if not os.path.isdir(topdir):
            os.mkdir(topdir)

        # create data file names
        door_motion_filepath = os.path.join(topdir, f"{name}_door_motion(1).parquet")
        temp_data_filepath = os.path.join(topdir, f"{name}_temp_data(1).parquet")
        co2_humidity_filepath = os.path.join(topdir, f"{name}_co2_humidity_data(1).pkl")
        smoke_detector_filepath = os.path.join(topdir, f"{name}_smoke_detector_data(1).byte")
        
        # set start time
        self.current_datetime = self.start_date
        # loop through all time steps
        for i in range(self.total_cycles):
            print(f"Cycle {i}: {str(self.current_datetime)}")
            # advance the datetime stamp
            self.current_datetime += datetime.timedelta(milliseconds=self.minor_cycle_len)
            # loop through each sensor
            for sensor_name, sensor in self.sensors.items():
                # process temperature sensors
                if sensor_name.startswith("t"):
                    self.process_temp_sensor(sensor, 
                                             ieee_encoded=(sensor_name.isin(("t2",))))
                # process motion and door sensors
                elif sensor_name.startswith("m") or sensor_name.startswith("d"):
                    self.process_passive_sensor(sensor)
