#!/bin/sh

export DB_HOST='10.222.17.221'
export DB_USER='postgres'
export DB_PASS='p@ssw0rd'
export DB_NAME='open_lmis'
export DB_PORT='5432'

./reason_migration.py