"""
Contains object that generates simulated home monitoring data
"""
# native imports
import datetime
import os
import re
from time import time, time_ns

# third party imports
import numpy as np
import pandas as pd
import pickle

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
MAX_STRING_SIZE = 10_000_000
MAX_ARRAY_SIZE = 10_000_000
MAX_BYTE_RATE = 840                     # estimated peak bytes written per cycle to largest dataframe
SMOKE_ARRAY_DTYPE = np.dtype("u8, u1, u1, u1, u1, U1")



class DataLimits():
    """
    Contains data size limits for different data types

    Attributes:
        max_dataframe_size (int): max size in bytes, a dataframe
            can be in memory before it gets written out to file.
        max_string_size (int): max size in bytes, a string object
            can be in memory before it gets written out to file.
        max_array_size (int): max size in bytes, a numpy array
            can be in memory before it gets written out to file.
    """
    def __init__(self, max_dataframe_size: int = MAX_DATAFRAME_SIZE, 
                 max_string_size: int = MAX_STRING_SIZE,
                 max_array_size: int = MAX_ARRAY_SIZE):
        self.max_dataframe_size = max_dataframe_size
        self.max_string_size = max_string_size
        self.max_array_size = max_array_size


    def get_all(self):
        """
        Returns all max sizes as a tuple in the order: dataframe, 
        string, array.
        """
        return self.max_dataframe_size, self.max_string_size, self.max_array_size


    def set_all(self, df_size: int, str_size: int, arr_size: int):
        """
        Sets the max sizes, if possible. Any that fail will remain the same.

        Arguments:
            df_size (int): max size in bytes, a dataframe
                can be in memory before it gets written out to file.
            str_size (int): max size in bytes, a string object
                can be in memory before it gets written out to file.
            arr_size (int): max size in bytes, a numpy array
                can be in memory before it gets written out to file.
        """
        self.max_dataframe_size = scrub_pos_int(df_size, self.max_dataframe_size)
        self.max_string_size = scrub_pos_int(str_size, self.max_string_size)
        self.max_array_size = scrub_pos_int(arr_size, self.max_array_size)




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
        data_limits (DataLimits): object that stores in-memory size limits for different
            data types. When the accumulated data (approximately) exceeds the limit, it
            will be written out to a file and cleared to start a new set of data.
    """
    def __init__(self, start_date_str: str, num_days: int, num_occupants: int, 
                 minor_cycle_len: int, temp_bias: float, sensor_fail_rate: float,
                 data_limits: DataLimits = None):
        self.start_date = scrub_date_str(start_date_str, default_x="2024-06-15")
        self.num_days = scrub_pos_int(num_days, default_x=1000)
        self.num_occupants = scrub_pos_int(num_occupants, default_x=1)
        self.minor_cycle_len = scrub_pos_int(minor_cycle_len, default_x=500)
        self.temp_bias = scrub_temp_f(temp_bias, default_x=2.0)
        self.sensor_fail_rate = scrub_proportion(x=sensor_fail_rate, default_x=0.0)
        self.total_cycles = int((TICKS_PER_DAY/self.minor_cycle_len)*self.num_days)
        self.__is_built__ = False
        self.temp_sensor_df = pd.DataFrame(columns=["date", "time", "sensor", "packet_id", "payload"])
        self.passive_sensor_df = pd.DataFrame(columns=["datetime", "sensor_id", "voltage"])
        self.humidity_co2_sensor_data = ""
        self.smoke_detector_data = np.array([], dtype=SMOKE_ARRAY_DTYPE)
        self.sensors = {}
        # if no passed in limits we use the defaults
        self.data_limits = data_limits or DataLimits()
        # how often (in cycles) to check/flush the RAM, with some wiggle room
        self.flush_rate = self.data_limits.max_dataframe_size // MAX_BYTE_RATE // 2


    def custom_build(self):
        """
        Use this if components were custom built
        so the object will set the built flag. No
        checks are done, so make sure that that
        build integrity is externally checked.
        """
        # confirm build
        self.__is_built__ = True


    # resets states before a new build and/or run
    def __reset__(self):
        self.door_motion_latest_filepath = None
        self.temp_data_latest_filepath = None
        self.co2_humidity_latest_filepath = None
        self.smoke_detector_latest_filepath = None
        self.sensors = {}
        self.__is_built__ = False


    # build components
    def __build__(self, force=False):
        # we run this loop if the components were not previously built
        # or if the inputs are forcing a build
        if (not self.__is_built__) or force:
            self.__reset__()

            # temp sensors
            sunlight_state = self.__get_sunlight_state__(sensor_pos_east=False)
            self.sensors["t1"] = __TempSensor__(self.sensor_fail_rate, START_TEMP_F, sunlight_state, self.temp_bias)
            sunlight_state = self.__get_sunlight_state__(sensor_pos_east=True)
            self.sensors["t2"] = __TempSensor__(self.sensor_fail_rate, START_TEMP_F, sunlight_state, self.temp_bias)
            
            # door sensors
            self.sensors["d1"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="door")
            self.sensors["d2"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="door")
            self.sensors["d3"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="door")

            # motion detectors
            self.sensors["m1"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="motion")
            self.sensors["m2"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="motion")
            self.sensors["m3"] = __PassiveSensor__(DOOR_MOTION_SENSOR_CYCLE // self.minor_cycle_len, style="motion")

            # humidity sensor
            self.sensors["h1"] = __HumiditySensor__(HUMIDITY_SENSOR_DELAY)

            # CO2 sensor
            self.sensors["c1"] = __Co2Sensor__(CO2_SENSOR_CYCLE_DELAY, self.num_occupants)
            
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
        beta = 1.0
        match (style, sundown):
            case ("motion", False): # motion sensor during the day
                beta *= 24.0
            case ("motion", True):  # motion sensor during the night
                beta *= 6.0
            case ("door", False):   # door sensor during the day
                beta *= 4.0
            case ("door", True):    # door sensor during the night
                beta *= 1.0
        return (self.num_occupants * beta) / TICKS_PER_DAY


    # processes one cycle for a temperature sensor
    def __process_temp_sensor__(self, sensor: __TempSensor__, sensor_name: str, ieee_encoded: bool = False):
        # sample the sensor
        temp = sensor.sample(self.minor_cycle_len)
        
        # encode data
        # date (Y-M-D), time (H:M:S.sss),
        # sensor (Tx), packet_id (TxPyy), payload
        num_packets = 4 if ieee_encoded else 1
        row = [self.current_datetime.strftime("%Y-%m-%d"), self.current_datetime.strftime("%H:%M:%S.%f"),
               sensor_name.upper(),"",0]
        if num_packets > 1:
            temp_str = np.float32(temp).tobytes().hex()
            for i, word in enumerate([temp_str[i:i+2] for i in range(0,len(temp_str),2)]):
                packet_id = f"{sensor_name.upper()}P{i:02b}"
                payload = f"0x{word}"
                row[3:5] = [packet_id, payload]
                self.temp_sensor_df.loc[self.temp_sensor_df.shape[0]] = row
        else:
            packet_id = f"{sensor_name.upper()}P00"
            payload = str(temp)
            row[3:5] = [packet_id, payload]
            self.temp_sensor_df.loc[self.temp_sensor_df.shape[0]] = row


    # processes one cycle for a passive sensor
    def __process_passive_sensor__(self, sensor: __PassiveSensor__, sensor_name: str):
        # get kappa
        kappa = self.__get_sensor_kappa__(sensor.style)
        # sample the sensor
        voltage = sensor.sample(kappa)
        # encode and store data in the format
        # <yr><day_of_yr>-<secs_since_mnight> | <sensor> | <mV> |
        year = self.current_datetime.year
        yday = self.current_datetime.timetuple().tm_yday
        secs_since_mnight = int((self.current_datetime.hour * 3600) + 
                             (self.current_datetime.minute * 60) + 
                             self.current_datetime.second)
        datetime_stamp = f"{year:04}{yday:03}-{secs_since_mnight:05}"
        row = [datetime_stamp, sensor_name.upper(), voltage]
        self.passive_sensor_df.loc[self.passive_sensor_df.shape[0]] = row


    # process one cycle for a co2 sensor
    def __process_humidity_co2_sensor__(self, sensor, sensor_name: str, cycle: int):
        # read the value (same for both)
        sensor_reading = sensor.sample(cycle)
        # format for record: YYYYMMMDDhhmmss=xxx.xxx%yyyyyppm
        # humidity sensor we need to record the datetime stamp
        if sensor_name.startswith("h"):
            self.humidity_co2_sensor_data += self.current_datetime.strftime("%Y%b%d%H%M%S")
            self.humidity_co2_sensor_data += f"{sensor_reading:.3f}%"
        # co2 sensor we onlt record the value
        elif sensor_name.startswith("c"):
            self.humidity_co2_sensor_data += f"{sensor_reading:03}ppm"


    # process one cycle for the smoke detector
    def __process_smoke_detector_data__(self, sensor: __SmokeDetector__):
        status = sensor.sample()
        # alarm went off for dead battery
        if status["battery_dead"]:
            self.smoke_detector_data = np.append(self.smoke_detector_data, 
                                                 np.array((self.current_datetime.year,
                                                           self.current_datetime.month,
                                                           self.current_datetime.day,
                                                           self.current_datetime.hour,
                                                           self.current_datetime.minute,'B'), 
                                                           dtype=SMOKE_ARRAY_DTYPE))
        # alarm went off for smoke
        if status["smoke"]:
            self.smoke_detector_data = np.append(self.smoke_detector_data, 
                                                 np.array((self.current_datetime.year,
                                                           self.current_datetime.month,
                                                           self.current_datetime.day,
                                                           self.current_datetime.hour,
                                                           self.current_datetime.minute,'S'), 
                                                           dtype=SMOKE_ARRAY_DTYPE))


    # advances time by one cycle
    def __advance_time__(self):
        prev_hour = self.current_datetime.hour
        self.current_datetime += (datetime.timedelta(milliseconds=self.minor_cycle_len))
        next_hour = self.current_datetime.hour
        # if going from day to night
        if (prev_hour > SUNRISE_HOUR) and (prev_hour < SUNSET_HOUR) and (next_hour >= SUNSET_HOUR):
            for sensor_name in self.sensors.keys():
                if sensor_name.startswith("t"):
                    self.sensors[sensor_name].night_cycle()
        # if going from night to day
        elif ((prev_hour > SUNSET_HOUR) or (prev_hour < SUNRISE_HOUR)) and (next_hour >= SUNRISE_HOUR):
            for sensor_name in self.sensors.keys():
                if sensor_name.startswith("t"):
                    self.sensors[sensor_name].day_cycle()


    # generates non-clashing file name for the next
    # sequence of data from the same source
    def __gen_next_filename__(self, old_name: str):
        # find the tag using regex
        tag = re.findall(r"\([0-9]+\)", old_name)[-1]
        # increment index to create new tag
        new_tag = f"({int(tag[1:-1])+1})"
        return old_name.replace(tag, new_tag)


    # writes data if it is too large to hold in memory or if
    # the simulation has finished
    def __flush__(self, sim_over=False):
        # "no-write" mode
        if self.topdir_path is None:
            return
        # temperature data
        if sim_over or (self.temp_sensor_df.memory_usage().sum() >= self.data_limits.max_dataframe_size):
            self.temp_sensor_df.to_parquet(self.temp_data_latest_filepath)
            self.temp_sensor_df = self.temp_sensor_df[0:0]
            self.temp_data_latest_filepath = self.__gen_next_filename__(self.temp_data_latest_filepath)
        # passive sensors data
        if sim_over or (self.passive_sensor_df.memory_usage().sum() >= self.data_limits.max_dataframe_size):
            self.passive_sensor_df.to_parquet(self.door_motion_latest_filepath)
            self.passive_sensor_df = self.passive_sensor_df[0:0]
            self.door_motion_latest_filepath = self.__gen_next_filename__(self.door_motion_latest_filepath)
        # humidity and co2 sensors data
        if sim_over or (len(self.humidity_co2_sensor_data) >= self.data_limits.max_string_size):
            pickle.dump(self.humidity_co2_sensor_data, open(self.co2_humidity_latest_filepath, "wb"))
            self.humidity_co2_sensor_data = ""
            self.co2_humidity_latest_filepat = self.__gen_next_filename__(self.co2_humidity_latest_filepath)
        # smoke detector data
        if sim_over or (self.smoke_detector_data.nbytes >= self.data_limits.max_array_size):
            self.smoke_detector_data.tofile(self.smoke_detector_latest_filepath, sep="") # to binary file
            self.smoke_detector_data = np.array([], dtype=SMOKE_ARRAY_DTYPE)
            self.smoke_detector_latest_filepath = self.__gen_next_filename__(self.smoke_detector_latest_filepath)

    
    def estimate(self, force_build: bool = True, multiplier: float = 2.0):
        """
        Runs low cycles with the current setup to estimate how long the
        full simulation would take. Resets after calculating.

        Args:
            force_build (bool): if True (default), will force a build before
                running the short sim. Optionally set this to false for custom 
                built objects.
            multipliter (float): multiplier for the estimate. The final reported
                time estimate will be <total_seconds>*<total_cycles>*<multiplier>.

        Raises
            RuntimeError if the object has not been built and force_build is not set.
        """
        if not force_build and not self.__is_built__:
            raise RuntimeError("Simulation is not ready, insert your own sensors and call"
                               " custom_build(), or run with force_build=True")
            return
        actual_cycles = self.total_cycles
        avg_usec_per_cyc = 0
        n = 30
        for i in range(1, n+1):
            self.total_cycles = i
            start_time = time_ns()
            self.start(name="estimate", output_dir_base_path=None, 
                       reset=force_build, quiet=True)
            usec = (time_ns() - start_time) / 1000
            avg = usec / i
            avg_usec_per_cyc += avg
            self.__reset__()
            print(f"Ran {i} cycle(s) in {usec/1000:.6f} milliseconds, {avg/1000:.6f} ms/cyc average")
        estimated = (avg_usec_per_cyc/n)*actual_cycles*multiplier
        self.total_cycles = actual_cycles
        print(f"Estimated time for {actual_cycles} cycles is " +
              f"{datetime.timedelta(microseconds=estimated)}")


    def start(self, name: str, output_dir_base_path: str = "", 
              reset: bool = False,  quiet: bool = False):
        """
        Starts the simulation process, with the option to reset,
            which forces a build, regenerating the components.
        
        Args:
            name (str): name which will pre-append to the current simulation
                output files.
            output_dir_base_path (str): base path for the output directory,
                which defaults to pwd if not given, or if set to None will
                run in "no-write" mode where the data is not written out. 
                This can be useful for debugging and estimation.
            reset (bool): if True, will force build the object, which
                resets the components.
            quiet (bool): if False, will print out some information
                during sim.
        """
        # real start time for sim timing
        start_time = time()
        # set start date
        self.current_datetime = self.start_date

        # build and reset if needed
        self.__build__(reset)
            
        # running in "no-write" mode
        if output_dir_base_path is None:
            self.topdir_path = None
        else:
            # create the top directory
            tag = str(datetime.datetime.now()).replace(" ","T").replace(":","_").replace(".","_")
            topdir = os.path.join(output_dir_base_path, f"{name}_{tag}")
            if not os.path.isdir(topdir):
                os.mkdir(topdir)
            self.topdir_path = topdir

            # create data file names
            self.door_motion_latest_filepath = os.path.join(topdir, f"{name}_door_motion_data(1).parquet")
            self.temp_data_latest_filepath = os.path.join(topdir, f"{name}_temp_data(1).parquet")
            self.co2_humidity_latest_filepath = os.path.join(topdir, f"{name}_co2_humidity_data(1).pkl")
            self.smoke_detector_latest_filepath = os.path.join(topdir, f"{name}_smoke_detector_data(1).bin")
        
        # loop through all time steps
        for i in range(self.total_cycles):
            if not quiet:
                print(f"Cycle {i+1} of {self.total_cycles}: {str(self.current_datetime)}")
            # advance the datetime stamp
            self.__advance_time__()
            # check/flush RAM if needed
            if (i % self.flush_rate) == 0:
                self.__flush__()
            # loop through each sensor
            for sensor_name, sensor in self.sensors.items():
                # process temperature sensors
                if sensor_name.startswith("t"):
                    self.__process_temp_sensor__(sensor, sensor_name,
                                                ieee_encoded=(sensor_name in ("t2",)))
                # process motion and door sensors
                elif sensor_name.startswith("m") or sensor_name.startswith("d"):
                    self.__process_passive_sensor__(sensor, sensor_name)

                # process humidity and CO2 sensors
                elif sensor_name.startswith("h") or sensor_name.startswith("c"):
                    self.__process_humidity_co2_sensor__(sensor, sensor_name, i)
                
                # process smoke detector
                elif sensor_name.startswith("s"):
                    self.__process_smoke_detector_data__(sensor)

        # final flush with sim_over flag on to write out all data
        self.__flush__(sim_over=True)
        if not quiet:
            total_sim_time = time() - start_time
            avg_secs_per_cyc = total_sim_time / self.total_cycles
            print(f"Simulation took {datetime.timedelta(seconds=total_sim_time)}, {avg_secs_per_cyc} s/cyc average")
        return self.topdir_path
