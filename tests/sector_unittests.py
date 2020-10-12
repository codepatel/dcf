import os,sys,inspect
import unittest
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.insert(0, os.path.dirname(current_dir))
from get_fin_report import get_sector_data

class SectorUnitTest(unittest.TestCase):
    def setUp(self):
        self.result = None
        pass
    def tearDown(self):
        pass    
    def testwithValidSector(self):
        for sector in ['Electronic Technology', 'Health Technology', 'Technology Services']:
            self.result = 'advanced-stats' in list(get_sector_data(sector).values())[0]
            self.assertTrue(self.result, 'FAIL with: ' + sector)