#!/usr/bin/python

import psycopg2.extras
import reason_utils
import db
import uuid


with psycopg2.connect("dbname='open_lmis' user='postgres' host='192.168.1.6' password='p@ssw0rd'") as conn:
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    facility_types = db.fetch_facility_types(cur)

    refdata_reasons = db.fetch_refdata_reasons(cur)

    stock_reasons = db.fetch_stock_reasons_with_valid_assignments(cur)

    ref_stock_mapping = {}
    new_items = []

    new_reason_count = 0
    new_valid_reason_count = 0

    # We go through ref data resons, mapping them to valid reasons, creating missing reasons in the process
    for refdata_reason in refdata_reasons:
        print "Reference data reason: "
        print refdata_reason

        for facility_type in facility_types:
            print 'Checking facility type: ' + facility_type['name']
            mapping_key = reason_utils.build_mapping_key(refdata_reason['id'], facility_type['id'])

            program_id = refdata_reason['programid']
            facility_type_id = facility_type['id']
            name = refdata_reason['name']
            description = refdata_reason['name']
            reason_type = 'CREDIT' if refdata_reason['additive'] else 'DEBIT'

            stock_reason = reason_utils.find_full_stock_reason(refdata_reason, stock_reasons, facility_type)

            if stock_reason is not None:
                # We have found a reason/valid reason combo that matches
                print 'Found exact existing valid reason. id: {}, name: {}'\
                    .format(stock_reason[1], stock_reason['name'])

                ref_stock_mapping[mapping_key] = stock_reason[1]
            else:
                stock_reason = reason_utils.find_stock_reason(refdata_reason, stock_reasons)
                if stock_reason is not None:
                    # We found the reason, but not for the program/facility type combo
                    print 'Found existing reason in stock, but not for this program/facility type. Id: {}, name: {}'\
                        .format(stock_reason[0], stock_reason['name'])
                    print 'Need to create valid reason for program & facility type'
                    
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
                    print 'Need to create new stock reason and valid reason'

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

    print "Done migrating Reference Data reasons to Stock Management. Added {} new reasons, and {} valid reason " \
          "assignments.".format(str(new_reason_count), str(new_valid_reason_count))
    print "Migrating Requisition adjustments to use Stock Reason IDs"

    vra_ids = db.fetch_valid_reason_assignment_ids(cur)

    facility_type_map = db.fetch_facility_type_map(cur)

    updated_adjustments_count = 0

    req_cur = db.create_req_adjustment_cursor(conn)

    for record in req_cur:
        a_id = record['id']
        reason_id = record['reasonid']
        facility_id = record['facilityid']
        program = record['programid']

        facility_type = facility_type_map[facility_id]
        
        print 'Processing adjustment {}. Facility type: {}, program: {}, current reason id: {}'\
            .format(a_id, facility_type, program, reason_id)

        if reason_id in vra_ids:
            print 'Reason points to a stock management UUID already: ' + reason_id
        else:
            mapping_key = reason_utils.build_mapping_key(reason_id, facility_type)
            new_reason_id = ref_stock_mapping[mapping_key]

            print 'Changing reason ID to: ' + new_reason_id

            db.update_adjustment(cur, a_id, new_reason_id)

            updated_adjustments_count += 1

    print 'Updated {} adjustments'.format(updated_adjustments_count)
