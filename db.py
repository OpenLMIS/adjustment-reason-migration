#!/usr/bin/python
import datetime
import psycopg2.extras
import uuid


def connect(host, port, db_name, user, password):
    return psycopg2.connect("dbname='{}' user='{}' host='{}' password='{}' port='{}'"
                            .format(db_name, user, host, password, port))


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
    adj_cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor, name='adj_cursor')
    adj_cur.itersize = 2000

    adj_cur.execute("""SELECT id, reasonid FROM requisition.stock_adjustments""")

    return adj_cur


def count_adjustments(cur):
    cur.execute("""SELECT COUNT(*) FROM requisition.stock_adjustments""")
    return cur.fetchone()[0]


def fetch_facility_types(cursor):
    cursor.execute("""SELECT * FROM referencedata.facility_types""")
    return cursor.fetchall()


def fetch_refdata_reasons(cursor):
    cursor.execute("""SELECT * FROM referencedata.stock_adjustment_reasons""")
    return cursor.fetchall()


def fetch_stock_reasons_with_valid_assignments(cursor):
    cursor.execute("""SELECT r.id, v.id, r.name, r.description, r.reasontype, r.reasoncategory, r.isfreetextallowed, 
                    v.programid, v.facilitytypeid FROM stockmanagement.stock_card_line_item_reasons r LEFT JOIN 
                    stockmanagement.valid_reason_assignments v on r.id = v.reasonid;""")
    return cursor.fetchall()


def fetch_stock_reason_ids(cursor):
    cursor.execute("""SELECT id FROM stockmanagement.stock_card_line_item_reasons""")
    stock_ids = cursor.fetchall()
    return [(s['id']) for s in stock_ids]


def fetch_facility_type_map(cursor):
    cursor.execute("""SELECT id, typeid FROM referencedata.facilities""")
    facilities_types = cursor.fetchall()
    return dict([(f['id'], f['typeid']) for f in facilities_types])


def count_requisitions(cursor):
    cursor.execute("""SELECT COUNT(*) FROM requisition.requisitions""")
    return cursor.fetchone()[0]


def create_requisitions_cursor(conn):
    req_cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor, name='req_cursor')
    req_cur.itersize = 2000

    req_cur.execute("""SELECT id, facilityid, programid FROM requisition.requisitions""")

    return req_cur


def check_if_snapshot_reason_exists(cur, req_id, reason_id):
    cur.execute("""SELECT COUNT(*) FROM requisition.stock_adjustment_reasons WHERE requisitionid = %s 
                AND reasonid = %s""", (req_id, reason_id))
    count = cur.fetchone()[0]
    return count > 0


def insert_requisition_snapshot_reason(cur, req_id, entry):
    reason_id = entry[0]
    name = entry['name']
    description = entry['description']
    reason_type = entry['reasontype']
    reason_category = entry['reasoncategory']
    is_free_text_allowed = entry['isfreetextallowed']

    cur.execute("""INSERT INTO requisition.stock_adjustment_reasons (id, requisitionid, reasonid, name, description,
                reasontype, reasoncategory, isfreetextallowed) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)""",
                (str(uuid.uuid4()), req_id, reason_id, name, description, reason_type, reason_category,
                 is_free_text_allowed))


def update_all_requisitions_date_modified(cur):
    now = datetime.datetime.utcnow()
    cur.execute("""UPDATE requisition.requisitions SET modifiedDate = %s""", [now])


def clear_snapshots(cur):
    cur.execute("DELETE FROM requisition.stock_adjustment_reasons")
