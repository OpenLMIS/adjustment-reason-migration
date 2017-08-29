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

from urlparse import urlparse


class JdbcUrl:

    def __init__(self, url):
        to_parse = url.replace('jdbc:', '')

        parsed_url = urlparse(to_parse)

        self.db_name = parsed_url.path.replace('/', '')
        self.port = parsed_url.port if parsed_url.port is not None else 5432
        self.host = parsed_url.hostname
        self.scheme = parsed_url.scheme
