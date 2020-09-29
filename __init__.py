import os
import logging
from pathlib import Path

if not os.path.exists('app'):   # use /app for logging and caching
    os.makedirs('app')

logging.basicConfig(format='%(asctime)s: [%(levelname)-8s] %(message)s',
                datefmt='%Y-%m-%d_%I:%M:%S_%p',
                filename=os.path.expandvars('./app/app_DCFoutput.log'),
                filemode='w',
                level=logging.INFO)
logger = logging.getLogger()

VERSION = 'v0.3-alpha.0'
HERE = Path(__file__).parent
TIMEOUT_12HR = 12*60*60  # cache timeout of 12 hours for getting Financial Reported Data update
DEFAULT_TICKER = 'AAPL'
DEFAULT_SNAPSHOT_UUID = '95df36ac-bc52-52e1-bdf6-bac53b7aa4ca'
