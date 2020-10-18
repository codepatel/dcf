import os,sys,inspect
import unittest
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.insert(0, os.path.dirname(current_dir))
from callbacks import check_ticker_validity
from get_fin_report import get_financial_report, get_yahoo_fin_values
from get_dcf_valuation import get_dcf_df

class DCFUnitTest(unittest.TestCase):
    def setUp(self):
        self.result = None
        pass
    def tearDown(self):
        pass    
    def testwithValidTicker(self):
        for ticker in ['AAPL', 'BAC', 'PGR', 'EPR', 'EAF', 'SKX', 'MU']:
            self.result = get_financial_report(ticker)
            self.assertTrue(self.result[1], 'FAIL with: ' + ticker)
    def testwithInvalidTicker(self):
        self.assertRaises(KeyError, check_ticker_validity, 'INVALID')
        self.assertRaises(ValueError, get_financial_report, 'INVALID')
    def testwithYahooTicker(self):
        self.result = get_yahoo_fin_values('WMT')
        self.assertTrue(self.result[1] < 0.5)
    def testwithDCFinputs(self):
        dcf_input = {'AAPL':{'stats_dict':{'lastprice':115}}}
        self.result = get_dcf_df(dcf_input, '0', '10', '5', '32', '1.2', '15', '1.25', '3.5', '8.5', None, 
                                    273430, 17890, 10630, 86220, 2.97, 93050, 94050, 17250, 0, 0, 0, 3, 29, 0, False, [1], '1f46bbc4-b0b5-5932-8ccf-9f4ebda9e047')
        self.assertAlmostEqual(self.result[1]['estimated_value_per_share'], 50.37, delta=0.01)
        self.result = get_dcf_df(dcf_input, '0', '10', '5', '32', '1.2', '15', '4.5', '6.5', '8.5', None, 
                                    273430, 17890, 10630, 86220, 2.97, 93050, 94050, 17250, 0, 0, 0, 3, 29, 0, True, [1], '1f46bbc4-b0b5-5932-8ccf-9f4ebda9e047')
        self.assertAlmostEqual(self.result[1]['estimated_value_per_share'], 57.61, delta=0.01)