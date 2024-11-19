# Home Monitoring System Simulator and Data Generator
Data simulator/generator which mocks a home monitoring system. Simulates data output from a home monitoring system. The way the data is output is purposely non-uniform and convoluted across the different sensors. This is because the idea is to generate a potentially large dataset that can be used to demo a data engineering project where the data is aggregated efficiently and accurately through an EPL pipeline. Unless otherwise noted, files will be output in .parquet format due to the potential for the large size. Some files may have multiple iterations (i.e.: foo_file(1).parquet, foo_file(2).parquet) if the data becomes too large in RAM.

For simplicity, the house has 4 rooms, and is shaped like a "T". The bottom part of the "T" faces exactly South, the Sun always rises exactly in the East and sets exactly to the West. The Sun rises at 06\:00 and sets at 18\:00, it is directly overhead at 12\:00. The side of the house with the sun will have slightly warmer temperatures during the day, while both sides will have cooler temperatures at night.

Smoke detectors will go off on chance based on a cadence of ten times per year. The chance will be calculated at every minor cycle. Given a minor cycle length (in milliseconds) of $m$, the chance of smoke alarm at every minor cycle will be $p = m \times 1.27 \times 10^{-10}$ based on year length of 365.25 days. The smoke alarm also goes off every $\lfloor \frac{20736000000}{m} \rfloor \pm \lfloor \frac{2592000000}{m}$ minor cycles for dead batteries.

![layout](https://github.com/user-attachments/assets/5459986f-93a2-4608-947b-ccf094617aa0)

Components
=============
- Two temp sensors on opposite sides of house
- door open/close sensors
- motion detectors
- humidity sensors
- CO2 sensors
- smoke detectors

User Options
==============
- base name (will be pre-appended to files)
- start date
- days to sim
- minor cycle (min refresh rate) in milliseconds
- number of occupants in home
- sun bias: for room temp on sun-side during day and temp drop during night
- temp/humidity/CO2 sensors failure rate (missing data or bad reading)

Occupant Behavior
===============
Occupants will take random walks through the house during the daytime, and some at night. For simplicity, these will be simulated by the door and motion sensors each having a chance of triggering $\kappa = \dfrac{n\beta}{86400000}$ where $n$ is the number of occupants and:

| sensor | time of day | beta |
|--------|-------------|------|
| motion | day         | 24.0 |
|        | night       | 4.0  |
| door   | day         | 6.0  |
|        | night       | 1.0  |

Data Output
================
1. Temperature Sensors
    - Will update at each minor cycle
    - Date in yyyy-mm-dd format (i.e.: "1995-02-01" for February 2, 1995)
    - Time in hh\:mm\:ss.SSS format (.i.e.: 17\:05:\15.500)
    - T1 outputs temperature value in units of Fahrenheit as a signed floating point value ranging from -100.0 to +250.0
    - T2 outputs its value in four different packets in least significant word first (LSW-First) order. When put together they form a [single-precision floating-point number](https://en.wikipedia.org/wiki/Single-precision_floating-point_format) These values will be stored as integers, but when correctly converted to single-precision they will represent Fahrenheit.
    - These will be stored in a joint file named temperature_data.parquet that will contain a dataframe similar to:

    | date       | time           | sensor | packet_id | payload |
    |------------|----------------|--------|-----------|---------|
    | 1995-02-01 | 13\:46\:08.347 | T1     | T1P00     | 72.054  |
    | 1995-02-01 | 13\:46\:08.347 | T2     | T2P00     | 0x83    |
    | 1995-02-01 | 13\:46\:08.347 | T2     | T2P01     | 0x00    |
    | 1995-02-01 | 13\:46\:08.347 | T2     | T2P10     | 0x90    |
    | 1995-02-01 | 13\:46\:08.347 | T2     | T2P11     | 0x42    |
    | 1995-02-01 | 13\:46\:08.847 | T1     | T1P00     | 72.061  |
    | 1995-02-01 | 13\:46\:08.847 | T2     | T2P00     | 0x06    |
    | 1995-02-01 | 13\:46\:08.847 | T2     | T2P01     | 0x01    |
    | 1995-02-01 | 13\:46\:08.847 | T2     | T2P10     | 0x90    |
    | 1995-02-01 | 13\:46\:08.847 | T2     | T2P11     | 0x42    |

2. Door/Motion Sensors
    - Updates every 30 seconds, or when there is a door opening or motion detected by one of the sensors
    - Datetime stamp is in YYYYJJJ-SSSSS where YYYYJJJ is the Julian date and SSSSS is a zero-padded, 5-digit value representing the number of seconds since midnight
    - The sensors report a voltage in units of milliVolts as an integer. Any value at or above 3100mV (3.1V) is considered a logic "1" or a detection by the sensor. Values at or below 1800mV (1.8V) are considered logic "0" or no detection. In between values are undefined, these will be the values transmitted in between triggers and snapshots.
    - Data will be grouped and output to a file called temp_data.parquet
    - Data is grouped in a dataframe like so:
    
    | datetime      | sensor_id | voltage |
    |---------------|-----------|---------|
    | 2017045-09205 | M1        | 4200    |
    | 2017045-09205 | D1        | 2600    |

3. Humidity/CO2 Sensors
    - These sensors plug into the same hub and collect their data together, but have staggered cycles
    - Humidity sensor updates every 100 minor cycles and CO2 sensor updates every 150 minor cycles
    - Humidity is zero-padded percentage, CO2 levels are zero-padded parts-per-million from 0 to 50,000
    - **NOTE:** Sensors values will report 999.999 or 99999 in between updates, but these are not the actual readings. They should be treated as "missing" or erroneous data
    - Data is output as a string stream to a file (which will be compressed to save space) in the following format YYYYMMMDDHHMMSS=AAA.aaa%BBBBBppm:
    
    | YYYY | MMM   | DD  | HHMMSS | =         | AAA.aaa% | BBBBBppm |
    |------|-------|-----|--------|-----------|----------|----------|
    | year | month | day | time   | separator | humidity | CO2      |

    - A file will be called co2_humidity_data.pkl and the contents once decompressed will look similar to this:
```
2019Feb10150318=045.003%03014ppm2019Feb10150458=045.001%99999ppm2019Feb10150548=999.999%03017ppm2019Feb10150638=045.015%99999ppm...
```

4. Smoke Detector
    - Data is output to binary file called smoke_detector.bin
    - Collection of datetime stamps of when the smoke detector alarm went off and the reason
    - Reason is a 1-character field where "S" means smoke detected and "B" means dead battery
    - Will be stored in memory as an array but will be written out to a byte file name "smoke_detector_data.byte"
    - The array, once decoded from bytes, may look like this:

    [[<year_as_int64>,<month_as_int8>,<day_as_int8>,<hours_as_int8>,<minutes_as_int8>,<reason_as_char(1)>],
     [<year_as_int64>,<month_as_int8>,<day_as_int8>,<hours_as_int8>,<minutes_as_int8>,<reason_as_char(1)>],
     [<year_as_int64>,<month_as_int8>,<day_as_int8>,<hours_as_int8>,<minutes_as_int8>,<reason_as_char(1)>]...]