#!/usr/bin/python

import psycopg2
import psycopg2.extras
import reason_checks
import uuid

def insert_valid_reason(cur, vra_id, facilitytypeid, programid, reasonid):
    cur.execute( """INSERT INTO stockmanagement.valid_reason_assignments (id, facilitytypeid, programid, reasonid)
                          VALUES (%s, %s, %s, %s);""", (vra_id, facilitytypeid, programid, reasonid))

def insert_stock_reason(cur, r_id, name, description, isfreetextallowed, reasoncategory, reasontype):
    cur.execute("""INSERT INTO stockmanagement.stock_card_line_item_reasons (id, name, description, isfreetextallowed, reasoncategory, reasontype)
                          VALUES (%s, %s, %s, %s, %s, %s)""", (r_id, name, description, isfreetextallowed, reasoncategory, reasontype))

def reason_entry(r_id, v_id, name, description, facilitytypeid, programid, reasontype):
    return { 0: r_id, 1: v_id, 'name': name, 'description': description, 'programid': programid, 'facilitytypeid': facilitytypeid, 'reasontype': reasontype }

def print_stock_reason(r_id, name):
    return 'Stock Reason, id: ' + r_id + ', name: ' + name

def update_adjustment(cur, a_id, new_reason_id):
    cur.execute("""UPDATE requisition.stock_adjustments SET reasonid = %s WHERE ID = %s""", (new_reason_id, a_id))
    

with psycopg2.connect("dbname='open_lmis' user='postgres' host='192.168.1.6' password='p@ssw0rd'") as conn:
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""SELECT * FROM referencedata.facility_types""")
    facility_types = cur.fetchall()

    cur.execute("""SELECT * FROM referencedata.stock_adjustment_reasons""")
    refdata_reasons = cur.fetchall()

    cur.execute("""SELECT r.id, v.id, r.name, r.description, r.reasontype, v.programid, v.facilitytypeid FROM 
            stockmanagement.stock_card_line_item_reasons r LEFT JOIN 
            stockmanagement.valid_reason_assignments v on r.id = v.reasonid;""")
    stock_reasons = cur.fetchall()
    print len(stock_reasons)

    ref_stock_mapping = { }
    new_items = []

    new_reason_count = 0
    new_valid_reason_count = 0

    # We go through ref data resons, mapping them to valid reasons, creating missing reasons in the process
    for refdata_reason in refdata_reasons:
        print "Reference data reason: "
        print refdata_reason

        for facility_type in facility_types:
            print 'Checking facility type: ' + facility_type['name']
            mapping_key = reason_checks.build_mapping_key(refdata_reason['id'], facility_type['id'])

            programid = refdata_reason['programid']
            facilitytypeid = facility_type['id']
            name = refdata_reason['name']
            description = refdata_reason['name']
            reasontype = 'CREDIT' if refdata_reason['additive'] else 'DEBIT'

            stock_reason = reason_checks.find_full_stock_reason(refdata_reason, stock_reasons, facility_type)

            if stock_reason is not None:
                # We have found a reason/valid reason combo that matches
                print 'Found exact existing valid reason. id: ' + stock_reason[1] + ', name: ' + stock_reason['name']

                ref_stock_mapping[mapping_key] = stock_reason[1]
            else:
                stock_reason = reason_checks.find_stock_reason(refdata_reason, stock_reasons)
                if stock_reason is not None:
                    # We found the reason, but not for the program/facility type combo
                    print 'Found existing reason in stock, but not for this program/facility type. Id: ' + stock_reason[0] + ', name: ' + stock_reason['name']
                    print 'Need to create valid reason for program & facility type'
                    
                    vra_id = str(uuid.uuid4())
                    r_id = stock_reason[0]
                
                    insert_valid_reason(cur, vra_id, facilitytypeid, programid, r_id)
                    
                    entry = reason_entry(r_id, vra_id, name, description, facilitytypeid, programid, reasontype)
                    stock_reasons.append(entry)
                    new_items.append(entry)

                    ref_stock_mapping[mapping_key] = vra_id

                    new_valid_reason_count += 1
                else:
                    # We didn't find anything
                    print 'Need to create new stock reason and valid reason'

                    r_id = str(uuid.uuid4())
                    reasontype = 'CREDIT' if refdata_reason['additive'] else 'DEBIT'

                    insert_stock_reason(cur, r_id, refdata_reason['name'], refdata_reason['description'], True, 'Adjustment', reasontype)
                    
                    vra_id = str(uuid.uuid4())

                    insert_valid_reason(cur, vra_id, facility_type['id'], refdata_reason['programid'], r_id)
                
                    entry = reason_entry(r_id, vra_id, name, description, facilitytypeid, programid, reasontype)
                    stock_reasons.append(entry)
                    new_items.append(entry)

                    ref_stock_mapping[mapping_key] = vra_id

                    new_reason_count += 1
                    new_valid_reason_count += 1

    print "Done migrating Reference Data reasons to Stock Management. Added " + str(new_reason_count) + " new reasons, and " + str(new_valid_reason_count) + " valid reason assignments."
    print "Migrating Requisition adjustments to use Stock Reason IDs"

    cur.execute("""SELECT id FROM stockmanagement.valid_reason_assignments""")
    vra_ids_res = cur.fetchall()
    vra_ids = [(v['id']) for v in vra_ids_res]

    cur.execute("""SELECT id, typeid FROM referencedata.facilities""")
    facilities_types = cur.fetchall()

    facility_type_map = dict([(f['id'], f['typeid']) for f in facilities_types])

    updated_adjustments_count = 0

    req_cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor, name='req_cursor')
    req_cur.itersize = 2000;

    req_cur.execute("""SELECT a.id, a.reasonid, req.facilityid, req.programid FROM requisition.stock_adjustments a
                          LEFT JOIN requisition.requisition_line_items item ON a.requisitionlineitemid = item.id
                          LEFT JOIN requisition.requisitions req ON item.requisitionid = req.id""")
    for record in req_cur:
        a_id = record['id']
        reason_id = record['reasonid']
        facility_id = record['facilityid']
        program = record['programid']

        facility_type = facility_type_map[facility_id]
        
        print 'Processing adjustment {}. Facility type: {}, program: {}, current reason id: {}'.format(a_id, facility_type, program, reason_id)

        if reason_id in vra_ids:
            print 'Reason points to a stock management UUID already: ' + reason_id
        else:
            mapping_key = reason_checks.build_mapping_key(reason_id, facility_type)
            new_reason_id = ref_stock_mapping[mapping_key]

            print 'Chaging reason ID to: ' + new_reason_id;

            update_adjustment(cur, a_id, new_reason_id)

            updated_adjustments_count += 1

    print 'Updated {} adjustments'.format(updated_adjustments_count)
