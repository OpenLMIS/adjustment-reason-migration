#!/usr/bin/python
import sys


REASON_ID_INDEX = 0
VRA_ID_INDEX = 1


def find_full_stock_reason(refdata_reason, stock_reasons, facility_type):
    for stock_reason in stock_reasons:
        if name_equal(refdata_reason, stock_reason) and \
                reason_relations_match(refdata_reason, stock_reason, facility_type):
            return stock_reason
    return None


def find_stock_reason(refdata_reason, stock_reasons):
    for stock_reason in stock_reasons:
        if name_equal(refdata_reason, stock_reason):
            return stock_reason
    return None


def reason_properties_equal(refdata_reason, stock_reason):
    return name_equal(refdata_reason, stock_reason) and \
           to_lower(refdata_reason['description']) == to_lower(stock_reason['description']) and \
           reason_type_equal(refdata_reason, stock_reason)


def name_equal(refdata_reason, stock_reason):
    return to_lower(refdata_reason['name']) == to_lower(stock_reason['name'])


def reason_relations_match(refdata_reason, stock_reason, facility_type):
    return stock_reason['programid'] == refdata_reason['programid'] and stock_reason[1] is not None \
           and stock_reason['facilitytypeid'] == facility_type['id']


def reason_type_equal(refdata_reason, stock_reason):
    return (refdata_reason['additive'] and stock_reason['reasontype'] == 'CREDIT') or \
           (not refdata_reason['additive'] and stock_reason['reasontype'] == 'DEBIT')


def build_mapping_key(left, right):
    return left + '_' + right


def to_lower(string):
    return string.lower() if string else None


def reason_entry(r_id, v_id, name, description, facility_type_id, program_id, reason_type, reason_category,
                 is_free_text_allowed):
    return {REASON_ID_INDEX: r_id, VRA_ID_INDEX: v_id, 'name': name, 'description': description,
            'programid': program_id, 'facilitytypeid': facility_type_id, 'reasontype': reason_type,
            'reasoncategory': reason_category, 'isfreetextallowed': is_free_text_allowed}


def print_and_debug(debug, msg):
    debug.write(msg)
    debug.write('\n')
    print(msg)


def print_percentage(completed, total):
    percentage = int((float(completed) / total) * 100)

    sys.stdout.write("\rMigration progress: {}/{} ({}%)".format(completed, total, percentage))
    sys.stdout.flush()
