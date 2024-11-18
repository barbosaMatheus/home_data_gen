# Home Monitoring System Simulator and Data Generator
Data simulator/generator which mocks a home monitoring system. Simulates data output from a home monitoring system. The way the data is output is purposely non-uniform and convoluted across the different sensors. This is because the idea is to generate a potentially large dataset that can be used to demo a data engineering project where the data is aggregated efficiently and accurately through an EPL pipeline. Unless otherwise noted, files will be output in .parquet format due to the potential for the large size. 

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
    - T2 outputs its value in two different packets, the first being the least significant word (LSW) and the second being the second being the MSW. When put together they form a [half-precision floating-point number](https://en.wikipedia.org/wiki/Half-precision_floating-point_format) These values will be stored as integers, but when correctly converted to half-precision they will represent Fahrenheit.
      
2. Door/Motion Sensors
    - Updates every 30 seconds, or when there is a door opening or motion detected by one of the sensors
    - Datetime stamp is in YYYYJJJ-SSSSS where YYYYJJJ is the Julian date and SSSSS is a zero-padded, 5-digit value representing the number of seconds since midnight
    - The sensors report a voltage in units of milliVolts as an integer. Any value at or above 3100mV (3.1V) is considered a logic "1" or a detection by the sensor. Values at or below 1800mV (1.8V) are considered logic "0" or no detection. In between values are undefined, these will be the values transmitted in between triggers and snapshots.
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
    - Data is output as a string stream to a file in the following format YYYYMMMDDHHMMSS=AAA.aaa%BBBBBppm:
    
    | YYYY | MMM   | DD  | HHMMSS | =         | AAA.aaa% | BBBBBppm |
    |------|-------|-----|--------|-----------|----------|----------|
    | year | month | day | time   | separator | humidity | CO2      |

    - A file output may look like this:
```
2019Feb10150318=045.003%03014ppm2019Feb10150458=045.001%99999ppm2019Feb10150548=999.999%03017ppm2019Feb10150638=045.015%99999ppm
```

4. Smoke Detector
    - Data is output to an MDB file
    - Collection of datetime stamps of when the smoke detector alarm went off and the reason
    - Reason is a 4-character field where "SMKE" means smoke detected and "BATT" means dead battery

| Field    | Type    |
|----------|---------|
| year     | Int(64) |
| month    | Int(4)  |
| day      | Int(8)  |
| hours    | Int(8)  |
| minutes  | Int(8)  |
| reason   | Char(4) |
   
