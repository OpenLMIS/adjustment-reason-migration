#!/usr/bin/python
# coding=utf-8

"""
This program is part of the OpenLMIS logistics management information system platform software.
Copyright © 2017 VillageReach

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU Affero General Public License as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Affero General Public License for more details. You should have received a copy of
the GNU Affero General Public License along with this program. If not, see
http://www.gnu.org/licenses.  For additional information contact info@OpenLMIS.org.
"""

import datetime
import psycopg2.extras
import uuid
import reason_utils


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


def update_adjustments(cur, old_reason_id, new_reason_id):
    cur.execute("""UPDATE requisition.stock_adjustments SET reasonid = %s WHERE reasonid = %s""", (new_reason_id,
                                                                                                   old_reason_id))


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


def insert_requisition_snapshots(cur, data):
    batch = 'INSERT INTO requisition.stock_adjustment_reasons (id, requisitionid, reasonid, name, description, ' \
            'reasontype, reasoncategory, isfreetextallowed) VALUES '

    inserts = []

    for (req_id, entry) in data:
        reason_id = entry[reason_utils.REASON_ID_INDEX]
        name = entry['name']
        description = entry['description']
        reason_type = entry['reasontype']
        reason_category = entry['reasoncategory']
        is_free_text_allowed = entry['isfreetextallowed']

        inserts.append(
            "('{}', '{}', '{}', '{}', '{}', '{}', '{}', {})".format(str(uuid.uuid4()), req_id, reason_id, name,
                                                                    description, reason_type, reason_category,
                                                                    is_free_text_allowed))

    batch += ','.join(inserts)

    cur.execute(batch)


def update_all_requisitions_date_modified(cur):
    now = datetime.datetime.utcnow()
    cur.execute("""UPDATE requisition.requisitions SET modifieddate = %s""", [now])


def clear_snapshots(cur):
    cur.execute("DELETE FROM requisition.stock_adjustment_reasons")


def count_bad_adjustments(cur, valid_reason_ids):
    id_string = ','.join("'{}'".format(r_id) for r_id in valid_reason_ids)
    cur.execute("""SELECT COUNT(*) FROM requisition.stock_adjustments WHERE reasonid NOT IN ({})""".format(id_string))
    return cur.fetchone()[0]
