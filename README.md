# openlmis-adjustment-reason-migration

Cross service migration of adjustment reasons used by Requisition - from Referencedata to Stock Management.

## Pre-requisites 

* Already using OpenLMIS 3.0.x or 3.1.x.
* Hosting OpenLMIS inside Docker with Docker Compose, and using PostgreSQL or AWS RDS as the database, with all OpenLMIS services using the same database instance.
* Requires administrator-level server access.

It is **strongly** suggested to run the migration on a staging/test server with a copy of production data 
first in order to verify the migration before running on production server

## Migration instructions

Pre-planning: Schedule downtime to perform the upgrade; do the upgrade on a Test/Staging server in advance before Production.

1. Bring server offline (so no more edits to data will be accepted from users). Stop the OpenLMIS services (docker-compose down).
2. Take full database backup. (And make sure you have a backup of the code/services deployed as well so you could roll back if necessary.)
3. Upgrade to OpenLMIS 3.2.0 components (usual steps to change versions of components used in your ref-distro docker-compose.yml).
4. Run the migration script. See section below for details.
5. Start the server to run OpenLMIS again (docker-compose up).
6. Run some manual tests to ensure the system is in good health (try viewing a requisition or examining a few records).
7. Bring server online (begin accepting outside traffic from users again).


## Usage

In order to use the first, you need the configuration file for it in your local working directory.
In the top-level directory of this repository execute:

```bash
cp sample-config/.env .
```

Then edit the file, so that it points to your database. The script needs to
connect to PostgreSQL database instance which OpenLMIS is using.

**Note:** You can also use the .env file you are using for the OpenLMIS distribution - the configuration is compatible.

Next simply run the migration script using Docker Compose:

```bash
docker-compose run adjustment-reason-migration
```

That's it - the migration will run and give you output about its progress.
For detailed debug information, the script logs to a file *called adjustment-migration.log*.
By default the directory under which this file is placed is mount in the *docker-compose.yml* file
to */tmp*. So in order to view the file, use a command similar to:

```bash
less /tmp/adjustment-migration.log
```

## Building

The Docker image is built on Docker Hub. In order to build it locally, simply run the build script:

```bash
./util-scripts/build.sh
``` 

## Script details

This script performs the migration of reasons from the Referencedata service to the Stock Management service, as well
as the migration of Requisition adjutments to use the UUIDs of the reasons in stock management.

The migration executes three steps:

### Step 1 - migration of reasons from Reference Data to Stock Management

Reasons will be migrated from Reference Data to the Stock Management Service. In refdata, a reason has a program
for which it is valid. In Stock Management, reasons do not store this information - they have valid reason assignments
associated with them. Such a valid reason assignment stores an ID of the program and an ID of the faciliy type.

In order to perform this migration, we match the refdata reasons against stock reasons using the name, description
and type. If they match, we treat them as the same. If a matching stock adjustment does not exist we create it,
if it does we use it. 

Since in refdata reasons are not associated with facility types, we have to iterate over all facility types 
from refdata for each reason. We match a refdata reason against a stock reason joined with the valid reason 
assignment - if the assignment by the given program of the refdata reason and facility type does not exist, 
we create it.  

During this migration step the script creates a mapping between refdata reasons and stock reasons for step 3,
it also stores the information about the new reasons for step 2. Refdata reasons are left as they were after
this step is finished.

Since we do matching during this step, running it multiple times on the same database should not make a
difference.

### Step 2 - creation of valid reason lists (snapshots) for each requisition

In this step, we iterate over all of the requisitions. For each of them, we find all valid reason assignments,
based on their program and the type of their facility. We create a snapshot of that reason and tie it to the
requisition, copying over the data from stock management.

At the end of this step, we update the modified date for all requisitions, so that they will be retrieved again
on the UI.

Note that before this step, we clear all the snapshots from the database for performance. This does not affect
normal use cases, since in those cases these snapshots are not there at all. It allows to run the migration
multiple times without duplicating data however, without any performance penalty.

### Step 3 - change reason IDs in requisitions to point to stock management reasons

In the last step, we iterate over all stock adjustments and based on the mapping from step #1, we assign them
new reason ids that point to stock. If an adjustments already has an ID that points to a stock management
reason, we leave it alone.

See further information: 

JIRA Ticket: [OLMIS-2830](https://openlmis.atlassian.net/browse/OLMIS-2830)

Wiki background: [Connecting Stock Management and Requisition Services](https://openlmis.atlassian.net/wiki/spaces/OP/pages/114234797/Connecting+Stock+Management+and+Requisition+Services)

## Error reporting

The script will report on two possible issues with data in te standard output: non-existent facilities for 
requisitions and non-existent reason IDs for stock adjustments. Detailed data on these as well as more information
can be found in the debug log.

The script also reports on the numbers of data it processes as well the number of updates it executes.

If the script is ran twice, it should not corrupt the data, since it does all the necessary checks before
altering the data. Any additional data that was added in the meantime will be migrated. Make note that however,
that valid reason snapshots in requisitions will always be recreated and the requisition modification date 
will be updated. Checking if those already exist is not done for performance reasons.
