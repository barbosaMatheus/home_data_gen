import home_monitoring_data_gen as dg

def one_sensor_full_sim_and_output_test():
    pass

# build and run integration tests
if __name__ == "__main__":
    tests = [one_sensor_full_sim_and_output_test]
    passes = 0
    for test in tests:
        print(f"Running: {test.__name__}")
        passed, diff = test()
        passes += int(passed)
        print(f"Test {"PASSED" if passed else "FAILED"}")
        if not passed:
            print(diff)