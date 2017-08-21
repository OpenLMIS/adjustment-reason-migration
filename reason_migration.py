#!/usr/bin/python

import psycopg2.extras
import reason_utils
import db
import uuid
import os
import sys

db_host = '10.222.17.221'
db_port = '5432'
db_name = 'open_lmis'
db_pass = 'p@ssw0rd'
db_user = 'postgres'

log_dir = 'log'

if not os.path.exists(log_dir):
    os.makedirs(log_dir)

with open(log_dir + '/adjustment-migration.log', 'w') as debug:
    reason_utils.print_and_debug(debug,
                                 'Starting migration of Adjustment Reasons from Reference Data to Stock Management\n')

    reason_utils.print_and_debug(debug, 'Connecting to database {} on {}:{}'.format(db_name, db_host, db_port))

    with db.connect(host=db_host, port=db_port, db_name=db_name, user=db_user, password=db_pass) as conn:
        reason_utils.print_and_debug(debug, 'Connection successful\n')

        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        facility_types = db.fetch_facility_types(cur)
        facility_type_count = len(facility_types)

        refdata_reasons = db.fetch_refdata_reasons(cur)
        refdata_reason_count = len(refdata_reasons)

        stock_reasons = db.fetch_stock_reasons_with_valid_assignments(cur)

        ref_stock_mapping = {}

        new_reason_count = 0
        new_valid_reason_count = 0

        reason_utils.print_and_debug(debug, "Migrating {} reasons from Reference Data to Stock Management using {} "
                                            "facility types".format(refdata_reason_count, facility_type_count))

        # We go through ref data resons, mapping them to valid reasons, creating missing reasons in the process

        for refdata_reason in refdata_reasons:
            debug.write("Reference data reason: ")
            debug.write(str(refdata_reason))
            debug.write('\n')

            for facility_type in facility_types:
                debug.write('Checking facility type: ' + facility_type['name'] + '\n')
                mapping_key = reason_utils.build_reason_mapping_key(refdata_reason['id'], facility_type['id'])

                program_id = refdata_reason['programid']
                facility_type_id = facility_type['id']
                name = refdata_reason['name']
                description = refdata_reason['name']
                reason_type = 'CREDIT' if refdata_reason['additive'] else 'DEBIT'

                stock_reason = reason_utils.find_full_stock_reason(refdata_reason, stock_reasons, facility_type)

                if stock_reason is not None:
                    # We have found a reason/valid reason combo that matches
                    debug.write('Found exact existing valid reason. id: {}, name: {}\n'
                                .format(stock_reason[1], stock_reason['name']))

                    ref_stock_mapping[mapping_key] = stock_reason[0]
                else:
                    stock_reason = reason_utils.find_stock_reason(refdata_reason, stock_reasons)
                    if stock_reason is not None:
                        # We found the reason, but not for the program/facility type combo
                        debug.write(
                            'Found existing reason in stock, but not for this program/facility type. Id: {}, name: {}\n'
                                .format(stock_reason[0], stock_reason['name']))
                        debug.write('Need to create valid reason for program & facility type\n')

                        vra_id = str(uuid.uuid4())
                        r_id = stock_reason[0]

                        db.insert_valid_reason(cur, vra_id, facility_type_id, program_id, r_id)

                        entry = reason_utils.reason_entry(r_id, vra_id, name, description, facility_type_id,
                                                          program_id, reason_type, stock_reason['reasoncategory'],
                                                          stock_reason['isfreetextallowed'])
                        stock_reasons.append(entry)

                        ref_stock_mapping[mapping_key] = r_id

                        new_valid_reason_count += 1
                    else:
                        # We didn't find anything
                        debug.write('Need to create new stock reason and valid reason\n')

                        r_id = str(uuid.uuid4())
                        reason_type = 'CREDIT' if refdata_reason['additive'] else 'DEBIT'

                        db.insert_stock_reason(cur, r_id, refdata_reason['name'], refdata_reason['description'], True,
                                               'Adjustment', reason_type)

                        vra_id = str(uuid.uuid4())

                        db.insert_valid_reason(cur, vra_id, facility_type['id'], refdata_reason['programid'], r_id)

                        entry = reason_utils.reason_entry(r_id, vra_id, name, description, facility_type_id, program_id,
                                                          reason_type, 'ADJUSTMENT', True)
                        stock_reasons.append(entry)

                        ref_stock_mapping[mapping_key] = r_id

                        new_reason_count += 1
                        new_valid_reason_count += 1

        reason_utils.print_and_debug(debug, "Done migrating Reference Data reasons to Stock Management. Added {} new "
                                            "reasons, and {} valid reason assignments.\n"
                                     .format(str(new_reason_count), str(new_valid_reason_count)))

        stock_ids = db.fetch_stock_reason_ids(cur)

        facility_type_map = db.fetch_facility_type_map(cur)

        # Build mappings for snapshot assignment
        program_type_reason_mapping = {}
        for entry in stock_reasons:
            key = reason_utils.build_program_ftype_mapping_reason(entry['facilitytypeid'], entry['programid'])
            if program_type_reason_mapping.get(key) is None:
                program_type_reason_mapping[key] = list()
            program_type_reason_mapping[key].append(entry)

        req_count = db.count_requisitions(cur)
        req_cur = db.create_requisitions_cursor(conn)

        reason_utils.print_and_debug(debug,
                                     "Creating available reason snapshots for {} Requisitions.".format(req_count))

        debug.write("Clearing existing snapshots")
        db.clear_snapshots(cur)

        new_snapshot_count = 0
        i = 0
        for req in req_cur:
            req_id = req['id']
            program_id = req['programid']
            facility_id = req['facilityid']

            facility_type_id = facility_type_map.get(facility_id)
            if facility_type_id is None:
                i += 1
                debug.write('WARN: facility does not exist: {}\n'.format(facility_id))
                continue

            debug.write('Processing requisition {}. Facility type: {}, program: {}\n'
                        .format(req_id, facility_type_id, program_id))

            mapping_key = reason_utils.build_program_ftype_mapping_reason(facility_type_id, program_id)

            entry_list = program_type_reason_mapping.get(mapping_key)
            if entry_list is not None:
                for entry in entry_list:
                    reason_id = entry[0]
                    debug.write("Creating a snapshot for requisition {} and reason {}\n".format(req_id, reason_id))
                    db.insert_requisition_snapshot_reason(cur, req_id, entry)
                    new_snapshot_count += 1

            i += 1
            percentage = int((float(i) / req_count) * 100)

            sys.stdout.write("\rMigration progress: {}%".format(percentage))
            sys.stdout.flush()

        reason_utils.print_and_debug(debug, "\nFinished creating creating snapshot adjustment reasons for {} "
                                            "requisitions. Created {} snapshots.\n".format(req_count,
                                                                                           new_snapshot_count))

        adjustment_count = db.count_adjustments(cur)

        reason_utils.print_and_debug(debug, "Migrating {} Requisition Adjustments to use Stock Reason IDs"
                                     .format(adjustment_count))

        updated_adjustments_count = 0
        adj_cur = db.create_req_adjustment_cursor(conn)

        i = 0
        for record in adj_cur:
            a_id = record['id']
            reason_id = record['reasonid']
            facility_id = record['facilityid']
            program = record['programid']

            facility_type_id = facility_type_map.get(facility_id)
            if facility_type_id is None:
                debug.write('WARN: facility does not exist: {}\n'.format(facility_id))
                continue

            debug.write('Processing adjustment {}. Facility type: {}, program: {}, current reason id: {}\n'
                        .format(a_id, facility_type_id, program, reason_id))

            if reason_id in stock_ids:
                debug.write('Reason points to a stock management UUID already: ' + reason_id + '\n')
            else:
                mapping_key = reason_utils.build_reason_mapping_key(reason_id, facility_type_id)
                new_reason_id = ref_stock_mapping[mapping_key]

                debug.write('Changing reason ID to: ' + new_reason_id + '\n')

                db.update_adjustment(cur, a_id, new_reason_id)

                updated_adjustments_count += 1

            i += 1
            percentage = int((float(i) / adjustment_count) * 100)

            sys.stdout.write("\rMigration progress: {}%".format(percentage))
            sys.stdout.flush()

        reason_utils.print_and_debug(debug, "\nMigration finished. Had to update {} out of {} Requisition Adjustments\n"
                                     .format(updated_adjustments_count, adjustment_count))

    reason_utils.print_and_debug(debug, 'Migration finished successfully')
