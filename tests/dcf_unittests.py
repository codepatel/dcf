import os,sys,inspect
import unittest
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.insert(0, os.path.dirname(current_dir))
from callbacks import check_ticker_validity
from get_fin_report import get_financial_report
from get_dcf_valuation import get_dcf_df

class DCFUnitTest(unittest.TestCase):
    def setUp(self):
        self.result = None
        pass
    def teardown(self):
        pass    
    def testwithValidTicker(self):
        self.result = get_financial_report('CNC')
        self.assertTrue(self.result[1])
    def testwithInvalidTicker(self):
        self.assertRaises(ValueError, get_financial_report, 'INVALID')