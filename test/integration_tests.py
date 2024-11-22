import home_monitoring_data_gen as dg
from components import __TempSensor__

OUTPUT_BASE_PATH = "../output"

def one_sensor_full_test():
    # parameters and setup
    num_days = 7
    cycle_len = 1000    # 1000 ms
    failrate = 0.001
    temp_bias = 2.0
    total_cycles = int(num_days * (86400000 / cycle_len))
    # build the object to simulate a week
    home = dg.HomeMonitoringDataGen(start_date_str="2023-04-11T09:00:00", num_days=num_days,
                                    num_occupants=1, temp_bias=temp_bias, 
                                    minor_cycle_len=cycle_len, sensor_fail_rate=failrate)
    # using t2 we can test the ieee encoding
    home.sensors["t2"] = __TempSensor__(fail_rate=failrate, start_temp=72.0, 
                                        sunlight="direct", bias=temp_bias)
    home.custom_build()
    
    # run test
    home.start(name="integration_t1", output_dir_base_path=OUTPUT_BASE_PATH)

    # check for the folder/file structure
    # check for dataframe format
    # check for correct number of cycles
    # check for correct ending datetime


# build and run integration tests
if __name__ == "__main__":
    tests = [one_sensor_full_test]
    passes = 0
    for test in tests:
        print(f"Running: {test.__name__}")
        passed, diff = test()
        passes += int(passed)
        print(f"Test {"PASSED" if passed else "FAILED"}")
        if not passed:
            print(diff)