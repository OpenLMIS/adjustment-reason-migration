#!/usr/bin/python

import unittest
import reason_utils


class TestStringMethods(unittest.TestCase):

    def test_reason_type_comparison(self):
        stock_reason = {'reasontype': 'CREDIT'}
        refdata_reason = {'additive': True}
        self.assertTrue(reason_utils.reason_type_equal(refdata_reason, stock_reason))

        stock_reason['reasontype'] = 'DEBIT'
        self.assertFalse(reason_utils.reason_type_equal(refdata_reason, stock_reason))

        refdata_reason['additive'] = False
        self.assertTrue(reason_utils.reason_type_equal(refdata_reason, stock_reason))
    
    def test_reason_properties_equal(self):
        stock_reason = {'reasontype': 'CREDIT', 'name': 'TRANSFER_IN', 'description': 'something'}
        refdata_reason = {'additive': True, 'name': 'TRANSFER_IN', 'description': 'something'}

        self.assertTrue(reason_utils.reason_properties_equal(refdata_reason, stock_reason))

        stock_reason['description'] = 'different'
        self.assertFalse(reason_utils.reason_properties_equal(refdata_reason, stock_reason))

if __name__ == '__main__':
    unittest.main()
