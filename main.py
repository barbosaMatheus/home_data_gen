"""
Main file for home monitoring data gen project.
Takes user args and runs/manages the generator.

> python main.py -n <name> -s <start_date> -d <days> -p <occup>
                 -c <cycle> -b <tbias> -f <frate> -o <outdir> 
                 -e <est> -m <mult> -q <quiet>

Estimate run for two years with 3 occupants 
starting in Jan 1st 2024:

>> python main.py -n twoyears -s 2024-01-01 -d 730 -p 3 -e True

Run a 10 week sim with 5 occupants, recording as often as
every 100 ms, with high fail rate sensors:

>> python main.py --name hifail --days 70 --occup 5 --f 0.15
"""
import argparse
from home_monitoring_data_gen import HomeMonitoringDataGen

parser = argparse.ArgumentParser("Home Monitoring System Simulator and Data Generator")
parser.add_argument("-n", "--name", dest="base_name", type=str, 
                    help="Base name to pre-appended to files")
parser.add_argument("-s", "--start", dest="start_date", type=str,
                    help="Start date in YYYY-MM-DD format",
                    required=False, default="1900-01-01")
parser.add_argument("-d", "--days", dest="num_days", type=int,
                    help="Number of days to simulate",
                    required=False, default=365)
parser.add_argument("-p", "--occup", dest="num_occupants", type=int,
                    help="Number of occupants in the home",
                    required=False, default=2)
parser.add_argument("-c", "--cycle", dest="minor_cycle_len", type=int,
                    help="minor cycle (min refresh rate) in milliseconds",
                    required=False, default=500)
parser.add_argument("-b", "--bias", dest="temp_bias", type=float,
                    help=("bias for room temp on sun-side during day" +
                          " and temp drop during night (in F)"),
                    required=False, default=0.0001)
parser.add_argument("-f", "--fail", dest="fail_rate", type=float,
                    help="temp/humidity/CO2 sensors failure rate [0.0-1.0)",
                    required=False, default=0.001)
parser.add_argument("-o", "--outdir", dest="output_dir", type=str,
                    help="output directory path, defaults to pwd",
                    required=False, default="./")
parser.add_argument("-e", "--estimate", dest="estimate", type=bool,
                    help=("If True, estimate the time taken for this setup instead of"
                          " actually running the full sim"),
                    required=False, default=False)
parser.add_argument("-m", "--mult", dest="multiplier", type=float,
                    help="If estimation is True, this will be used as multiplier",
                    required=False, default=2.0)
parser.add_argument("-q", "--quiet", dest="quiet", type=bool,
                    help="If True, most output is suppressed while  running the sim",
                    required=False, default=False)
args = parser.parse_args()

if __name__ == "__main__":
    gen = HomeMonitoringDataGen(start_date_str=args.start_date, num_days=args.num_days,
                                num_occupants=args.num_occupants,
                                minor_cycle_len=args.minor_cycle_len, 
                                temp_bias=args.temp_bias,
                                sensor_fail_rate=args.fail_rate)
    if args.estimate:
        gen.estimate(force_build=True, multiplier=args.multiplier)
    else:
        output_dir = gen.start(name=args.base_name, 
                               output_dir_base_path=args.output_dir, 
                               quiet=args.quiet)
        print(f"Files written to {output_dir}")
