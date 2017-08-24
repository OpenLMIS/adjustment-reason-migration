#!/bin/sh

docker run -e DB_HOST='10.222.17.221' -e DB_USER='postgres' -e DB_PASS='p@ssw0rd' -e DB_NAME='open_lmis' -e DB_PORT='5432' -v '/tmp:/log'  openlmis/adjustment-reason-migration
