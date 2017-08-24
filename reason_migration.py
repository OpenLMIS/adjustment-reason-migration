#!/usr/bin/python

import psycopg2.extras
import reason_utils
import db
import uuid
import os


db_host = os.environ['DB_HOST']
db_port = os.environ['DB_PORT']
db_name = os.environ['DB_NAME']
db_pass = os.environ['DB_PASS']
db_user = os.environ['DB_USER']

batch_size = int(os.getenv('BATCH_SIZE', 2000))

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

        # We go through ref data reasons, mapping them to valid reasons, creating missing reasons in the process

        different_reason_props_count = 0
        for refdata_reason in refdata_reasons:
            debug.write("Reference data reason: ")
            debug.write(str(refdata_reason))
            debug.write('\n')

            for facility_type in facility_types:
                debug.write('Checking facility type: ' + facility_type['name'] + '\n')

                program_id = refdata_reason['programid']
                facility_type_id = facility_type['id']
                name = refdata_reason['name']
                description = refdata_reason['description']
                reason_type = 'CREDIT' if refdata_reason['additive'] else 'DEBIT'
                refdata_reason_id = refdata_reason['id']

                stock_reason = reason_utils.find_full_stock_reason(refdata_reason, stock_reasons, facility_type)

                if stock_reason is not None:
                    # We have found a reason/valid reason combo that matches
                    debug.write('Found exact existing valid reason. id: {}, name: {}\n'
                                .format(stock_reason[reason_utils.VRA_ID_INDEX], stock_reason['name']))

                    ref_stock_mapping[refdata_reason_id] = stock_reason[reason_utils.REASON_ID_INDEX]

                else:
                    stock_reason = reason_utils.find_stock_reason(refdata_reason, stock_reasons)
                    if stock_reason is not None:
                        # We found the reason, but not for the program/facility type combo
                        debug.write(
                            'Found existing reason in stock, but not for this program/facility type. Id: {}, name: {}\n'
                            .format(stock_reason[0], stock_reason['name']))
                        debug.write('Need to create valid reason for program & facility type\n')

                        vra_id = str(uuid.uuid4())
                        r_id = stock_reason[reason_utils.REASON_ID_INDEX]

                        db.insert_valid_reason(cur, vra_id, facility_type_id, program_id, r_id)

                        entry = reason_utils.reason_entry(r_id, vra_id, name, description, facility_type_id,
                                                          program_id, reason_type, stock_reason['reasoncategory'],
                                                          stock_reason['isfreetextallowed'])
                        stock_reasons.append(entry)

                        ref_stock_mapping[refdata_reason_id] = r_id

                        new_valid_reason_count += 1
                    else:
                        # We didn't find anything
                        debug.write('Need to create new stock reason and valid reason\n')

                        r_id = str(uuid.uuid4())

                        db.insert_stock_reason(cur, r_id, name, description, True, 'ADJUSTMENT', reason_type)

                        vra_id = str(uuid.uuid4())

                        db.insert_valid_reason(cur, vra_id, facility_type_id, program_id, r_id)

                        entry = reason_utils.reason_entry(r_id, vra_id, name, description, facility_type_id, program_id,
                                                          reason_type, 'ADJUSTMENT', True)
                        stock_reasons.append(entry)

                        ref_stock_mapping[refdata_reason_id] = r_id

                        new_reason_count += 1
                        new_valid_reason_count += 1

                if stock_reason is not None and not reason_utils.reason_properties_equal(refdata_reason,
                                                                                         stock_reason):
                    different_reason_props_count += 1
                    debug.write("WARN: ref data reason {} and stock management reason {} have the same name[{}]"
                                " but different type and description\n"
                                .format(refdata_reason_id, stock_reason[reason_utils.REASON_ID_INDEX], name))
                    debug.write("Inconsistent RefData reason - {}\n".format(str(refdata_reason)))
                    debug.write("Inconsistent Stock reason - {}\n".format(str(stock_reason)))

        reason_utils.print_and_debug(debug, "Done migrating Reference Data reasons to Stock Management. Added {} new "
                                            "reasons, and {} valid reason assignments.\n"
                                     .format(str(new_reason_count), str(new_valid_reason_count)))

        if different_reason_props_count > 0:
            reason_utils.print_and_debug(debug, "WARNING! {} valid reason assignments have different descriptions or "
                                                "types between Reference Data and Stock Management\n"
                                         .format(different_reason_props_count))

        stock_ids = db.fetch_stock_reason_ids(cur)

        facility_type_map = db.fetch_facility_type_map(cur)

        # Build mappings for snapshot assignment
        program_type_reason_mapping = {}
        for entry in stock_reasons:
            # Entries for reasons without valid assignments should get ignored
            if entry[reason_utils.VRA_ID_INDEX] is not None:
                key = reason_utils.build_mapping_key(entry['facilitytypeid'], entry['programid'])
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
        nonexistent_facs = list()
        batch_data = list()
        for req in req_cur:
            req_id = req['id']
            program_id = req['programid']
            facility_id = req['facilityid']

            facility_type_id = facility_type_map.get(facility_id)
            if facility_type_id is None:
                i += 1
                debug.write('WARN: facility does not exist: {}\n'.format(facility_id))
                nonexistent_facs.append(facility_id)
                continue

            debug.write('Processing requisition {}. Facility type: {}, program: {}\n'
                        .format(req_id, facility_type_id, program_id))

            mapping_key = reason_utils.build_mapping_key(facility_type_id, program_id)

            entry_list = program_type_reason_mapping.get(mapping_key)
            if entry_list is not None:
                debug.write('Creating snapshots for requisition: {}. Facility type: {} program :{}\n'
                            .format(req_id, facility_type_id, program_id))
                for entry in entry_list:
                    reason_id = entry[reason_utils.REASON_ID_INDEX]
                    debug.write("Creating a snapshot for requisition {} and reason {}\n".format(req_id, reason_id))

                    batch_data.append((req_id, entry))

                    new_snapshot_count += 1

            else:
                debug.write('No snapshots will be created for requisition: {}. Facility type: {} program :{}\n'
                            .format(req_id, facility_type_id, program_id))

            i += 1

            batch_len = len(batch_data)
            is_batch_exec_time = batch_len >= batch_size
            is_last_iter = i == req_count

            debug.write('Current Batch Size: {}. Will execute at {}. Should exec now?: {}. Last iteration?: {}\n'
                        .format(batch_len, batch_size, is_batch_exec_time, is_last_iter))

            if is_batch_exec_time or is_last_iter:
                debug.write("Executing batch insert of {}\n".format(len(batch_data)))
                db.insert_requisition_snapshots(cur, batch_data)
                del batch_data[:]

            reason_utils.print_percentage(i, req_count)

        # We want to mark all requisitions as updated
        db.update_all_requisitions_date_modified(cur)

        reason_utils.print_and_debug(debug, "\nFinished creating snapshot adjustment reasons for {} "
                                            "requisitions. Created {} snapshots.\n".format(req_count,
                                                                                           new_snapshot_count))

        if len(nonexistent_facs) > 0:
            reason_utils.print_and_debug(debug, 'WARNING! {} facilities from Requisition do not exist in '
                                                'Reference Data: {}\n'.format(len(nonexistent_facs),
                                                                              str(nonexistent_facs)))

        adjustment_count = db.count_adjustments(cur)
        updates_to_exec = len(ref_stock_mapping)

        reason_utils.print_and_debug(debug, "Migrating {} Requisition Adjustments to use Stock Reason IDs. "
                                     "Executing updates for {} reason IDs."
                                     .format(adjustment_count, updates_to_exec))

        updated_adjustments_count = 0

        i = 0
        for old_id, new_id in ref_stock_mapping.iteritems():

            debug.write('Updating reason id {} to: {}\n'.format(old_id, new_id))

            if old_id != new_id:
                db.update_adjustments(cur, old_id, new_id)
                updated_adjustments_count += cur.rowcount
            else:
                debug.write('{} is the same reason id both in Reference Data and Stock Management\n'.format(old_id))

            debug.write('Updated {} adjustments\n'.format(cur.rowcount))

            i += 1
            reason_utils.print_percentage(i, updates_to_exec)

        reason_utils.print_and_debug(debug, "\nMigration finished. Had to update {} out of {} Requisition Adjustments\n"
                                     .format(updated_adjustments_count, adjustment_count))

        bad_reason_id_count = db.count_bad_adjustments(cur, stock_ids)

        if bad_reason_id_count > 0:
            reason_utils.print_and_debug(debug, "WARN: {} adjustments have non-existent reason ids assigned"
                                         .format(bad_reason_id_count))

    reason_utils.print_and_debug(debug, 'Migration finished successfully')
