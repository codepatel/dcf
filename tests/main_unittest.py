import unittest
if __package__:
    from .dcf_unittests import DCFUnitTest
    from .sector_unittests import SectorUnitTest
else:
    from dcf_unittests import DCFUnitTest
    from sector_unittests import SectorUnitTest

def suite():
    '''
    Test suite
    '''
    suite = unittest.TestSuite()
    suite.addTests(        
        unittest.TestLoader().loadTestsFromTestCase(DCFUnitTest)
    )
    suite.addTests(        
        unittest.TestLoader().loadTestsFromTestCase(SectorUnitTest)
    )
    return suite

if __name__ == '__main__':
    # unittest.main(argv=['ignored'], exit=False)   # for Notebooks
    unittest.TextTestRunner(verbosity=2).run(suite())