#!/usr/bin/python
# coding=utf-8

"""
This program is part of the OpenLMIS logistics management information system platform software.
Copyright © 2017 VillageReach

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU Affero General Public License as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Affero General Public License for more details. You should have received a copy of
the GNU Affero General Public License along with this program. If not, see
http://www.gnu.org/licenses.  For additional information contact info@OpenLMIS.org.
"""

import unittest
import reason_utils
from jdbcurl import JdbcUrl


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

    def test_build_mapping_key(self):
        ref_id = "XXXX-432"
        f_id = "VVVV-333"

        result = reason_utils.build_mapping_key(ref_id, f_id)

        self.assertEqual("XXXX-432_VVVV-333", result)


class TestJdbcParseMethods(unittest.TestCase):

    def test_jdbc_parse(self):
        jdbcurl = JdbcUrl("jdbc:postgresql://db:5433/open_lmis")

        self.assertEqual(5433, jdbcurl.port)
        self.assertEqual('db', jdbcurl.host)
        self.assertEqual('open_lmis', jdbcurl.db_name)
        self.assertEqual('postgresql', jdbcurl.scheme)

    def test_jdbc_parse_default_port(self):
        jdbcurl = JdbcUrl("jdbc:postgresql://aws-rds.host.com/name1")

        self.assertEqual(5432, jdbcurl.port)
        self.assertEqual('aws-rds.host.com', jdbcurl.host)
        self.assertEqual('name1', jdbcurl.db_name)
        self.assertEqual('postgresql', jdbcurl.scheme)

    def test_jdbc_url_without_prefix(self):
        jdbcurl = JdbcUrl("postgresql://10.222.17.221:5432/open_lmis")

        self.assertEqual(5432, jdbcurl.port)
        self.assertEqual('10.222.17.221', jdbcurl.host)
        self.assertEqual('open_lmis', jdbcurl.db_name)
        self.assertEqual('postgresql', jdbcurl.scheme)

if __name__ == '__main__':
    unittest.main()
