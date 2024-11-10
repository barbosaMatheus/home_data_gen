"""
Main file for home monitoring data gen project.
Takes user args and runs/manages the generator.
"""
import argparse

parser = argparse.ArgumentParser("Home Monitoring System Simulator and Data Generator")
parser.add_argument("-n", "--name", dest="base_name", type=str, 
                    help="Base name to pre-appended to files")
parser.add_argument("-s", "--start", dest="start_date", type=str,
                    help="Start date in YYYY-MM-DD format",
                    required=False, default="1900-01-01")
parser.add_argument("-d", "--days", dest="num_days", type=int,
                    help="Number of days to simulate",
                    required=False, default=365)
parser.add_argument("-c", "--cycle", dest="minor_cycle_len", type=int,
                    help="minor cycle (min refresh rate) in milliseconds",
                    required=False, default=100)
parser.add_argument("-b", "--bias", dest="temp_bias", type=float,
                    help=("bias for room temp on sun-side during day" +
                          " and temp drop during night (in F)"),
                    required=False, default=3.0)
parser.add_argument("-f", "--fail", dest="fail_rate", type=float,
                    help="temp/humidity/CO2 sensors failure rate [0.0-1.0)",
                    required=False, default=0.001)
args = parser.parse_args()

