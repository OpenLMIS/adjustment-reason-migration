#!/usr/bin/python

from urlparse import urlparse


class JdbcUrl:

    def __init__(self, url):
        to_parse = url.replace('jdbc:', '')

        parsed_url = urlparse(to_parse)

        self.db_name = parsed_url.path.replace('/', '')
        self.port = parsed_url.port if parsed_url.port is not None else 5432
        self.host = parsed_url.hostname
        self.scheme = parsed_url.scheme
