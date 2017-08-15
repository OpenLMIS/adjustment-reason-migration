#!/usr/bin/python

import psycopg2.extras


def insert_valid_reason(cursor, v_id, facility_type_id, program_id, reason_id):
    cursor.execute("""INSERT INTO stockmanagement.valid_reason_assignments (id, facilitytypeid, programid, reasonid)
                          VALUES (%s, %s, %s, %s);""", (v_id, facility_type_id, program_id, reason_id))


def insert_stock_reason(cursor, r_id, name, description, isfreetextallowed, reason_category, reason_type):
    cursor.execute("""INSERT INTO stockmanagement.stock_card_line_item_reasons (id, name, description, isfreetextallowed, 
                    reasoncategory, reasontype) VALUES (%s, %s, %s, %s, %s, %s)""",
                   (r_id, name, description, isfreetextallowed, reason_category, reason_type))


def update_adjustment(cur, a_id, new_reason_id):
    cur.execute("""UPDATE requisition.stock_adjustments SET reasonid = %s WHERE ID = %s""", (new_reason_id, a_id))


def create_req_adjustment_cursor(conn):
    req_cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor, name='req_cursor')
    req_cur.itersize = 2000

    req_cur.execute("""SELECT a.id, a.reasonid, req.facilityid, req.programid FROM requisition.stock_adjustments a
                          LEFT JOIN requisition.requisition_line_items item ON a.requisitionlineitemid = item.id
                          LEFT JOIN requisition.requisitions req ON item.requisitionid = req.id""")

    return req_cur


def fetch_facility_types(cursor):
    cursor.execute("""SELECT * FROM referencedata.facility_types""")
    return cursor.fetchall()


def fetch_refdata_reasons(cursor):
    cursor.execute("""SELECT * FROM referencedata.stock_adjustment_reasons""")
    return cursor.fetchall()


def fetch_stock_reasons_with_valid_assignments(cursor):
    cursor.execute("""SELECT r.id, v.id, r.name, r.description, r.reasontype, v.programid, v.facilitytypeid FROM 
            stockmanagement.stock_card_line_item_reasons r LEFT JOIN 
            stockmanagement.valid_reason_assignments v on r.id = v.reasonid;""")
    return cursor.fetchall()


def fetch_valid_reason_assignment_ids(cursor):
    cursor.execute("""SELECT id FROM stockmanagement.valid_reason_assignments""")
    vra_ids = cursor.fetchall()
    return [(v['id']) for v in vra_ids]


def fetch_facility_type_map(cursor):
    cursor.execute("""SELECT id, typeid FROM referencedata.facilities""")
    facilities_types = cursor.fetchall()
    return dict([(f['id'], f['typeid']) for f in facilities_types])
