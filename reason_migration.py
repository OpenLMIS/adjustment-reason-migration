#!/usr/bin/python

import psycopg2.extras
import reason_utils
import db
import uuid
import sys
import os

log_dir = 'log'

if not os.path.exists(log_dir):
    os.makedirs(log_dir)
debug = open(log_dir + '/debug.log', 'w')

msg = "Starting migration of Adjustment Reasons from Reference Data to Stock Management\n"
print msg
debug.write(msg)

with psycopg2.connect("dbname='open_lmis' user='postgres' host='192.168.1.6' password='p@ssw0rd'") as conn:
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    facility_types = db.fetch_facility_types(cur)
    facility_type_count = len(facility_types)

    refdata_reasons = db.fetch_refdata_reasons(cur)
    refdata_reason_count = len(refdata_reasons)

    stock_reasons = db.fetch_stock_reasons_with_valid_assignments(cur)

    ref_stock_mapping = {}
    new_items = []

    new_reason_count = 0
    new_valid_reason_count = 0

    msg = "Migrating {} reasons from Reference Data to Stock Management, using {} facility types" \
        .format(refdata_reason_count, facility_type_count)
    print msg
    debug.write(msg)
    debug.write('\n')

    # We go through ref data resons, mapping them to valid reasons, creating missing reasons in the process
    i = 0
    combo_count = facility_type_count * refdata_reason_count

    for refdata_reason in refdata_reasons:
        debug.write("Reference data reason: ")
        debug.write(str(refdata_reason))
        debug.write('\n')

        for facility_type in facility_types:
            debug.write('Checking facility type: ' + facility_type['name'] + '\n')
            mapping_key = reason_utils.build_mapping_key(refdata_reason['id'], facility_type['id'])

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

                ref_stock_mapping[mapping_key] = stock_reason[1]
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
                                                      program_id, reason_type)
                    stock_reasons.append(entry)
                    new_items.append(entry)

                    ref_stock_mapping[mapping_key] = vra_id

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
                                                      reason_type)
                    stock_reasons.append(entry)
                    new_items.append(entry)

                    ref_stock_mapping[mapping_key] = vra_id

                    new_reason_count += 1
                    new_valid_reason_count += 1

            i += 1
            percentage = int((float(i) / combo_count) * 100)

            sys.stdout.write("\rMigration progress: {}%".format(percentage))
            sys.stdout.flush()

    msg = "\n\nDone migrating Reference Data reasons to Stock Management. Added {} new reasons, and {} valid reason " \
          "assignments.\n".format(str(new_reason_count), str(new_valid_reason_count))

    print msg
    debug.write(msg)

    adjustment_count = db.count_adjustments(cur)

    msg = "Migrating {} Requisition Adjustments to use Stock Reason IDs".format(adjustment_count)

    print msg
    debug.write(msg)
    debug.write('\n')

    vra_ids = db.fetch_valid_reason_assignment_ids(cur)

    facility_type_map = db.fetch_facility_type_map(cur)

    updated_adjustments_count = 0

    req_cur = db.create_req_adjustment_cursor(conn)

    i = 0
    for record in req_cur:
        a_id = record['id']
        reason_id = record['reasonid']
        facility_id = record['facilityid']
        program = record['programid']

        facility_type = facility_type_map[facility_id]

        debug.write('Processing adjustment {}. Facility type: {}, program: {}, current reason id: {}\n'
                    .format(a_id, facility_type, program, reason_id))

        if reason_id in vra_ids:
            debug.write('Reason points to a stock management UUID already: ' + reason_id + '\n')
        else:
            mapping_key = reason_utils.build_mapping_key(reason_id, facility_type)
            new_reason_id = ref_stock_mapping[mapping_key]

            debug.write('Changing reason ID to: ' + new_reason_id + '\n')

            db.update_adjustment(cur, a_id, new_reason_id)

            updated_adjustments_count += 1

        i += 1
        percentage = int((float(i) / adjustment_count) * 100)

        sys.stdout.write("\rMigration progress: {}%".format(percentage))
        sys.stdout.flush()

    msg = '\n\nMigration finished. Updated {} Requisition Adjustments\n'.format(updated_adjustments_count)
    print msg
    debug.write(msg)
