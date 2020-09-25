import os
import logging
from pathlib import Path

if not os.path.exists('tmp'):   # use /tmp for logging and caching
    os.makedirs('tmp')

logging.basicConfig(format='%(asctime)s: [%(levelname)-8s] %(message)s',
                datefmt='%Y-%m-%d_%I:%M:%S_%p',
                filename=os.path.expandvars('./tmp/app_DCFoutput.log'),
                filemode='w',
                level=logging.INFO)
logger = logging.getLogger()

HERE = Path(__file__).parent
TIMEOUT_12HR = 12*60*60  # cache timeout of 12 hours for getting Financial Reported Data update
VERSION = 'v0.2-alpha.1'