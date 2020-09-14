import os
import logging

if not os.path.exists('tmp'):   # use /tmp for logging and caching
    os.makedirs('tmp')

logging.basicConfig(format='%(asctime)s: [%(levelname)-8s] %(message)s',
                datefmt='%Y-%m-%d_%I:%M:%S_%p',
                filename=os.path.expandvars('./tmp/app_DCFoutput.log'),
                filemode='w',
                level=logging.INFO)
logger = logging.getLogger()