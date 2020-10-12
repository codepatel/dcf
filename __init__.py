import os
import logging
from pathlib import Path
import json
from app import cache

if not os.path.exists('app'):   # use /app for logging and caching
    os.makedirs('app')

logging.basicConfig(format='%(asctime)s: [%(levelname)-8s] %(message)s',
                datefmt='%Y-%m-%d_%I:%M:%S_%p',
                filename=os.path.expandvars('./app/app_DCFoutput.log'),
                filemode='w',
                level=logging.INFO)
logger = logging.getLogger()

VERSION = 'v0.4-alpha.0'
HERE = Path(__file__).parent
TIMEOUT_12HR = 12*60*60  # cache timeout of 12 hours for getting Financial Reported Data update
DEFAULT_TICKER = 'AAPL'
DEFAULT_SNAPSHOT_UUID = '95df36ac-bc52-52e1-bdf6-bac53b7aa4ca'

# Delete pyc: find . -name \*.pyc -delete

@cache.memoize(timeout=TIMEOUT_12HR*2*30)    # Use Cache Timeout of 30 days for symbols data
def get_symbols():
    with open(Path(HERE, 'assets', 'symbols.json')) as symfile:
        symdata = json.load(symfile)
    return symdata

def ticker_dict():  # For user-entered ticker validation
    return {s['symbol']:s['symbol']+'('+s['exchange']+'):'+s['name'] for s in get_symbols()}

def exchange_list():
    return list(set([s['exchange'] for s in get_symbols()]))
