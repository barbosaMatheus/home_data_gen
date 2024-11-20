import sys
sys.path.append("../")
import numpy as np
from components import __TempSensor__, BAD_TEMP_F

# setting up a sensor with high failrate to
# make sure the the failrate works
def test_temp_sensor_hi_failrate():
    # setup the test
    sensor = __TempSensor__(fail_rate=0.75, start_temp=100.0, 
                            sunlight="indirect", bias=0.0)
    n = 100
    samples = []

    # run n samples
    for _ in range(n):
        t = sensor.sample(1000)
        samples.append(t)

    # check that most (> 50% of the samples are bad)
    bad_samples = [s for s in samples if (s == BAD_TEMP_F) or (np.isnan(s))]
    assert (len(bad_samples) / len(samples)) > 0.5

# setting up a sensor with low (normal) failrate to
# make sure the the failrate works
def test_temp_sensor_lo_failrate():
    # setup the test
    sensor = __TempSensor__(fail_rate=0.0001, start_temp=100.0,
                            sunlight="indirect", bias=0.0)
    n = 100
    samples = []

    # run n samples
    for _ in range(n):
        t = sensor.sample(1000)
        samples.append(t)

    # check that < 1% of the samples are bad
    bad_samples = [s for s in samples if (s == BAD_TEMP_F) or (np.isnan(s))]
    assert (len(bad_samples) / len(samples)) < 0.01

# setting up two sensors, one in direct sunlight and
# one in indirect. Taking plenty samples and making
# sure the direct sunlight sensor is warmer on average
# to make sure the sunlight offset works
def test_temp_sensor_sunlight():
    # setup the test
    bias = 1.0
    sensor1 = __TempSensor__(fail_rate=0.0001, start_temp=100.0, 
                             sunlight="direct", bias=bias)
    sensor2 = __TempSensor__(fail_rate=0.0001, start_temp=100.0, 
                             sunlight="indirect", bias=bias)
    n = 100
    samples1 = []
    samples2 = []

    # run n samples
    for _ in range(n):
        samples1.append(sensor1.sample(1000))
        samples2.append(sensor2.sample(1000))
        
    mean1 = sum(samples1) / n
    mean2 = sum(samples2) / n

    # check that on average sensor 1 is warmer
    print(samples1)
    print(samples2)
    assert mean1 > mean2

if __name__ == "__main__":
    test_temp_sensor_sunlight()