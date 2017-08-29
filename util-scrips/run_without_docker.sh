#!/bin/sh

export DATABASE_URL='postgresql://10.222.17.221:5432/open_lmis'
export POSTGRES_USER='postgres'
export POSTGRES_PASSWORD='p@ssw0rd'

./reason_migration.py