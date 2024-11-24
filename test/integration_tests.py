import os
import sys
import datetime
import pandas as pd
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))
import home_monitoring_data_gen as dg
from components import __TempSensor__

OUTPUT_BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                                "../../output")

# builds a setup with one senso and runs the
# entire process throug to file output
def one_sensor_full_test():
    # parameters and setup
    num_days = 7
    cycle_len = 3600000 # 1 hour
    failrate = 0.001
    temp_bias = 2.0
    total_cycles = int(num_days * (86400000 / cycle_len))
    start_date_str = "2023-04-11T09:00:00"

    # build the object to simulate a week
    home = dg.HomeMonitoringDataGen(start_date_str=start_date_str, num_days=num_days,
                                    num_occupants=1, temp_bias=temp_bias, 
                                    minor_cycle_len=cycle_len, sensor_fail_rate=failrate)
    
    # using t2 we can test the ieee encoding
    home.sensors["t2"] = __TempSensor__(fail_rate=failrate, start_temp=72.0, 
                                        sunlight="direct", bias=temp_bias)
    home.custom_build()
    
    # run test
    output_path = home.start(name="integration_t1", output_dir_base_path=OUTPUT_BASE_PATH)

    # diffs in expected vs actual output, if any
    diffs = []
    
    # check for the folder/file structure
    dir_created = os.path.isdir(output_path)
    if not dir_created:
        diffs.append(f"Expected creation of directory {output_path}, but failed.")
        return False, diffs
    file_created = False
    df = None
    for name in os.listdir(output_path):
        if (("temperature_data" in name) and name.endswith(".parquet") and 
            os.path.isfile(os.path.join(output_path,name))): 
            df = pd.DataFrame(os.path.isfile(os.path.join(output_path,name)))
            file_created = True
            break
    if not file_created:
        diffs.append("Expected creation of temperature data parquet file, but failed.")
        return False, diffs
    
    # check for dataframe format
    if df is None: # df is valid
        diffs.append("Expected temperature parquet to contain dataframe, but failed.")
        return False, diffs
    expected_df_cols = ["date", "time", "sensor", "packet_id", "payload"]
    if df.columns.tolist() != expected_df_cols: # correct columns
        diffs.append(f"Expected dataframe to have columns {expected_df_cols}, but got {df.columns.tolist()}")
        return False, diffs
    expected_rows = total_cycles * 4 # 4 packets per cycle
    if df.shape[0] != expected_rows:
        diffs.append(f"Expected dataframe to have {expected_rows} rows, but got {df.shape[0]}")
        return False, diffs

    # check for correct ending datetime
    end_date = datetime.datetime.fromisoformat(start_date_str) + datetime.timedelta(milliseconds=int(total_cycles*cycle_len))
    expected_end_date_str = end_date.strftime("%Y-%M-%D") 
    if df.iloc[-1,0] != expected_end_date_str:
        diffs.append(f"Expected final date stamp to be {expected_end_date_str}, but got {df.iloc[-1,0]}")
        return False, diffs
    expected_end_time_str = end_date.strftime("%H:%M:%S.%f")
    if df.iloc[-1,1] != expected_end_time_str:
        diffs.append(f"Expected final time stamp to be {expected_end_time_str}, but got {df.iloc[-1,1]}")
        return False, diffs
    return True, diffs
    
# run integration tests
if __name__ == "__main__":
    tests = [one_sensor_full_test]
    passes = 0
    for test in tests:
        print(f"Running: {test.__name__}")
        passed, diff = test()
        passes += int(passed)
        print(f"Test {'PASSED' if passed else 'FAILED'} for reasons:")
        if not passed:
            for i, msg in enumerate(diff):
                print(f"{i+1}. {msg}")