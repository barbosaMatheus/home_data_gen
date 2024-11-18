"""
Input scrubbing utilities
"""
import sys
from datetime import datetime

DEFAULT_FLOAT = 0.0
DEFAULT_INT = 0
DEFAULT_ANY = None
DEFAULT_TEMP_F = 70.0
DEFAULT_START_DATE_STR = "1900-01-01"

def scrub_numeric(x, x_type, default_x, xmin, xmax, include_left: bool, include_right: bool):
    default = None
    if not isinstance(default_x, x_type):
        default = DEFAULT_ANY
    else:
        default = default_x
    if ((include_left and x < xmin) or (not include_left and x <= xmin) or 
        (not isinstance(x, x_type)) or (include_right and x > xmax) or
        (not include_right and x >= xmax)):
        return default
    else:
        return x

def scrub_proportion(x: float, default_x: float, xmin: float = 0.0, xmax: float = 1.0, 
                     include_left: bool = True, include_right: bool = False):
    default = None
    if not isinstance(default_x, float):
        default = DEFAULT_FLOAT
    else:
        default = default_x
    return scrub_numeric(x, float, default, xmin, xmax, include_left, include_right)

def scrub_temp_f(x: float, default_x: float):
    default = None
    if not isinstance(default_x, float):
        default = DEFAULT_TEMP_F
    else:
        default = default_x
    return scrub_numeric(x, float, default, xmin=-100.0, xmax=250.0, 
                         include_left=True, include_right=True)

def scrub_pos_int(x: int, default_x: int):
    default = None
    if not isinstance(default_x, float):
        default = DEFAULT_INT
    else:
        default = default_x
    return scrub_numeric(x, int, default, xmin=0, xmax=sys.maxsize, 
                         include_left=True, include_right=True)

def scrub_date_str(x: str, default_x: str):
    default = None
    if not isinstance(default_x, str):
        default = DEFAULT_START_DATE_STR
    else:
        default = default_x
    try:
        start_date = datetime.fromisoformat(x)
    except ValueError:
        start_date = datetime.fromisoformat(default)
    finally:
        return start_date
