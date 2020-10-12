import unittest
if __package__:
    from .dcf_unittests import DCFUnitTest
else:
    from dcf_unittests import DCFUnitTest

def suite():
    '''
    Test suite
    '''
    suite = unittest.TestSuite()
    suite.addTests(        
        unittest.TestLoader().loadTestsFromTestCase(DCFUnitTest)
    )
    return suite

if __name__ == '__main__':
    # unittest.main(argv=['ignored'], exit=False)   # for Notebooks
    unittest.TextTestRunner(verbosity=2).run(suite())