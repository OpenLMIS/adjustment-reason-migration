#!/usr/bin/python


def find_full_stock_reason(refdata_reason, stock_reasons, facility_type):
    for stock_reason in stock_reasons:
        if reason_properties_equal(refdata_reason, stock_reason) and \
                reason_relations_match(refdata_reason, stock_reason, facility_type):
            return stock_reason
    return None


def find_stock_reason(refdata_reason, stock_reasons):
    for stock_reason in stock_reasons:
        if reason_properties_equal(refdata_reason, stock_reason):
            return stock_reason
    return None


def reason_properties_equal(refdata_reason, stock_reason):
    return to_lower(refdata_reason['name']) == to_lower(stock_reason['name']) and \
           to_lower(refdata_reason['description']) == to_lower(stock_reason['description'])


def reason_relations_match(refdata_reason, stock_reason, facility_type):
    return stock_reason['programid'] == refdata_reason['programid'] and stock_reason[1] is not None \
           and stock_reason['facilitytypeid'] == facility_type['id']


def reason_type_equal(refdata_reason, stock_reason):
    return (refdata_reason['additive'] and stock_reason['reasontype'] == 'CREDIT') or \
           (not refdata_reason['additive'] and stock_reason['reasontype'] == 'DEBIT')


def build_reason_mapping_key(refdata_reason_id, facility_type_id):
    return refdata_reason_id + '_' + facility_type_id


def build_program_ftype_mapping_reason(program_id, facility_type_id):
    return program_id + '_' + facility_type_id


def to_lower(string):
    return string.lower() if string else None


def reason_entry(r_id, v_id, name, description, facility_type_id, program_id, reason_type, reason_category,
                 is_free_text_allowed):
    return {0: r_id, 1: v_id, 'name': name, 'description': description, 'programid': program_id,
            'facilitytypeid': facility_type_id, 'reasontype': reason_type, 'reasoncategory': reason_category,
            'isfreetextallowed': is_free_text_allowed}


def print_and_debug(debug, msg):
    debug.write(msg)
    debug.write('\n')
    print msg
