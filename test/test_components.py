import sys
sys.path.append("../")
import numpy as np
from components import __TempSensor__, __PassiveSensor__, __Co2Sensor__, __HumiditySensor__, __SmokeDetector__
from components import BAD_TEMP_F, LOGIC_ZERO_MV_MAX, LOGIC_ONE_MV_MIN, BAD_PPM, OCCUPANT_PPM_SCALE, BAD_HUMIDITY

# grouping tests for temp sensor
class TestTempSensor():
    # setting up a sensor with high failrate to
    # make sure the the failrate works
    def test_temp_sensor_hi_failrate(self):
        # setup the test
        sensor = __TempSensor__(fail_rate=0.75, start_temp=100.0, 
                                sunlight="indirect", bias=0.0)
        sensor.seed(123)
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
    def test_temp_sensor_lo_failrate(self):
        # setup the test
        sensor = __TempSensor__(fail_rate=0.0001, start_temp=100.0,
                                sunlight="indirect", bias=0.0)
        sensor.seed(123)
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
    def test_temp_sensor_sunlight(self):
        # setup the test
        bias = 1.0
        sensor1 = __TempSensor__(fail_rate=0.0001, start_temp=100.0, 
                                sunlight="direct", bias=bias)
        sensor1.seed(123)
        sensor2 = __TempSensor__(fail_rate=0.0001, start_temp=100.0, 
                                sunlight="indirect", bias=bias)
        sensor2.seed(123)
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

# grouping tests for passive sensors
class TestPassiveSensor():
    # setting up a motion sensor and testing to make
    # sure the correct number of readings show up given
    # the ping rate and total samples
    def test_passive_sensor_ping_frequency(self):
        # set up the test
        ppc = 10
        n = 20
        kappa = 24 / 86400000 # 24 times per day
        expected_readings = n // ppc
        sensor = __PassiveSensor__(ppc, "motion")
        sensor.seed(123)
        values = []

        # run n samples
        for _ in range(n):
            values.append(sensor.sample(kappa))

        # check that the readings are as expected
        readings = [v for v in values if (v <= LOGIC_ZERO_MV_MAX) or (v >= LOGIC_ONE_MV_MIN)]
        assert len(readings) == expected_readings

    # setting up a door sensor and testing to make
    # sure a high kappa value generates a lot of
    # of triggers
    def test_passive_sensor_hi_kappa(self):
        # set up the test
        ppc = 10
        n = 100
        kappa = 0.75
        expected_readings = n // ppc
        sensor = __PassiveSensor__(ppc, "door")
        sensor.seed(123)
        values = []

        # run n samples
        for _ in range(n):
            values.append(sensor.sample(kappa))

        # check that the readings are as expected
        triggers = [v for v in values if v >= LOGIC_ONE_MV_MIN]
        assert (len(triggers) / expected_readings) >= 0.5

    # setting up a door sensor and testing to make
    # sure a low kappa value generates very few
    # triggers
    def test_passive_sensor_lo_kappa(self):
        # set up the test
        ppc = 10
        n = 100
        kappa = 0.02
        expected_readings = n // ppc
        sensor = __PassiveSensor__(ppc, "door")
        sensor.seed(123)
        values = []

        # run n samples
        for _ in range(n):
            values.append(sensor.sample(kappa))

        # check that the readings are as expected
        nontriggers = [v for v in values if v <= LOGIC_ZERO_MV_MAX]
        assert (len(nontriggers) / expected_readings) >= 0.9

# grouping tests for CO2 sensor
class TestCo2Sensor():
    # set up a CO2 sensor and run a few samples
    # to make sure the the correct proportion
    # of actual readings comes out, based on the
    # cycle delay
    def test_co2_sensor_normal(self):
        # set up test
        delay = 10
        sensor = __Co2Sensor__(delay, 1)
        sensor.seed(123)
        n = 100
        expected_readings = n // delay
        expected_flags = n - expected_readings
        values = []

        # run n samples
        for i in range(n):
            values.append(sensor.sample(i))
        readings = [v for v in values if v != BAD_PPM]
        flags = [v for v in values if v == BAD_PPM]

        # check that the proportion of readings is correct
        assert ((len(readings) == expected_readings) and 
                (len(flags) == expected_flags))
        
    # set up a CO2 sensor that always records
    # zero and run a few samples to make sure 
    # test the the correct occupant shift
    def test_co2_sensor_normal(self):
        # set up test
        delay = 10
        occupants = 2
        sensor = __Co2Sensor__(delay, occupants, 0.0, 0.0)
        sensor.seed(123)
        n = 100
        values = []

        # run n samples
        for i in range(n):
            values.append(sensor.sample(i))
        readings = [v for v in values if v != BAD_PPM]

        # check that the readings all recorded the shift
        assert max(readings) == OCCUPANT_PPM_SCALE*occupants

# grouping tests for humidity sensor
class TestHumiditySensor():
    # set up a humidity sensor and run a few samples
    # to make sure the the correct proportion
    # of actual readings comes out, based on the
    # cycle delay
    def test_humidity_sensor_normal(self):
        # set up test
        delay = 20
        sensor = __HumiditySensor__(delay)
        sensor.seed(123)
        n = 1000
        expected_readings = n // delay
        expected_flags = n - expected_readings
        values = []

        # run n samples
        for i in range(n):
            values.append(sensor.sample(i))
        readings = [v for v in values if v != BAD_HUMIDITY]
        flags = [v for v in values if v == BAD_HUMIDITY]

        # check that the proportion of readings is correct
        assert ((len(readings) == expected_readings) and 
                (len(flags) == expected_flags))
        
# grouping for smoke detector tests
class TestSmokeDetector():
    # set up a smoke detector and give it a high chance of
    # having the alarm go off so we can test the functionality
    def test_smoke_detector_smoke_alarm(self):
        # set up the test
        cycle_len = 1e9 # this gives us a chance of smoke about 1/10 cycles
        sensor = __SmokeDetector__(cycle_len)
        sensor.seed(123)
        n = 100
        smoke_events_low = 5
        smoke_events_high = 15
        smoke_events = 0

        # run n samples
        for _ in range(n):
            status = sensor.sample()
            if status["smoke"]:
                smoke_events += 1
        
        # make sure the number of smoke events is within range
        assert smoke_events_low <= smoke_events <= smoke_events_high
    
    # set up a smoke detector and give it a high chance of
    # having the alarm go off so we can test the functionality
    def test_smoke_detector_smoke_battery(self):
        # set up the test
        cycle_len = int(20e6) # this gives us a dead battery about every 1000 cycles
        sensor = __SmokeDetector__(cycle_len)
        sensor.seed(123)
        n = int(1e4)
        battery_events_low = 5
        battery_events_high = 15
        battery_events = 0

        # run n samples
        for _ in range(n):
            status = sensor.sample()
            if status["battery_dead"]:
                battery_events += 1
        
        # make sure the number of smoke events is within range
        assert battery_events_low <= battery_events <= battery_events_high