#!/bin/sh

docker run -e DATABASE_URL='jdbc:postgresql://10.222.17.221:5432/open_lmis' -e POSTGRES_USER='postgres' -e POSTGRES_PASSWORD='p@ssw0rd' -v '/tmp:/log'  openlmis/adjustment-reason-migration:1.0
