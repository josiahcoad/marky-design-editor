from decimal import Decimal
import os
import boto3
from utils.dto import Canvas
import streamlit as st
from typing import Dict, List

CANVAS_TABLE_NAME = 'canvas-prod'
THEMES_TABLE_NAME = 'themes-prod'
STORAGE_TABLE_NAME = 'internal-design-editor'
PROMPT_TABLE_NAME = 'prompts-prod'
BUSINESS_TABLE_NAME = 'books-prod'
USER_TABLE_NAME = 'users2-prod'
CAROUSEL_TABLE_NAME = 'carousels-prod'

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
DDB_RESOURCE = boto3.resource('dynamodb')


def list_canvases() -> List[Canvas]:
    if '__canvases' not in st.session_state:
        with st.spinner("Getting canvases from db..."):
            canvases = [Canvas.parse_obj(x) for x in list_all(CANVAS_TABLE_NAME)]
        st.session_state['__canvases'] = {x.id: x for x in canvases}
    return list(st.session_state['__canvases'].values())


def clear_canvas_cache():
    del st.session_state['__canvases']


def list_prompts():
    if '__prompts' not in st.session_state:
        with st.spinner("Getting prompts from db..."):
            prompts = list_all(PROMPT_TABLE_NAME)
        st.session_state['__prompts'] = {x['id']: x for x in prompts}
    return list(st.session_state['__prompts'].values())


def list_users():
    if '__users' not in st.session_state:
        with st.spinner("Getting users from db..."):
            users = list_all(USER_TABLE_NAME)
            for user in users:
                del user['password']
        st.session_state['__users'] = {x['id']: x for x in users}
    return list(st.session_state['__users'].values())


def list_businesses():
    if '__businesses' not in st.session_state:
        with st.spinner("Getting businesses from db..."):
            businesses = list_all(BUSINESS_TABLE_NAME)
        st.session_state['__businesses'] = {x['id']: x for x in businesses}
    return list(st.session_state['__businesses'].values())


def list_users_joined_businesses(only_full_businesses=False):
    if only_full_businesses:
        return list_users_joined_businesses_full()
    
    if '__users_joined_businesses' not in st.session_state:
        businesses = list_businesses()
        for x in businesses:
            x['business_id'] = x['id']
            del x['id']

        users = list_users()
        for x in users:
            x['user_id'] = x['id']
            del x['id']
        
        business_map = {x['user_id']: x for x in businesses}
        users_joined_businesses = [{**x, **business_map.get(x['user_id'], {})} for x in users]
        st.session_state['__users_joined_businesses'] = users_joined_businesses
    return st.session_state['__users_joined_businesses']


def list_users_joined_businesses_full():
    if '__users_joined_businesses_full' not in st.session_state:
        users_joined_businesses = list_users_joined_businesses()
        users_joined_businesses = [x for x in users_joined_businesses
                                    if all((x.get('brand', {}).get('logo'),
                                            x.get('brand', {}).get('color'),
                                            x.get('brand', {}).get('background_color'),
                                            x.get('brand', {}).get('text_color'),
                                            x.get('website'),
                                            x.get('topics'),
                                            x.get('ctas')))]
        st.session_state['__users_joined_businesses_full'] = users_joined_businesses
    return st.session_state['__users_joined_businesses_full']


def list_themes():
    if '__themes' not in st.session_state:
        with st.spinner("Getting themes from db..."):
            themes = list_all(THEMES_TABLE_NAME)
        st.session_state['__themes'] = {x['id']: x for x in themes}
    return list(st.session_state['__themes'].values())


def list_carousels():
    if '__carousels' not in st.session_state:
        with st.spinner("Getting carousels from db..."):
            carousels = list_all(CAROUSEL_TABLE_NAME)
        st.session_state['__carousels'] = {x['name']: x for x in carousels}
    return list(st.session_state['__carousels'].values())


def save_business(_):
    raise NotImplementedError("Don't do this!")


def save_user(_):
    raise NotImplementedError("Don't do this!")


def save_canvas(canvas: Canvas):
    put(CANVAS_TABLE_NAME, canvas.model_dump())
    put('canvas-dev', canvas.model_dump())
    st.session_state['__canvases'][canvas.id] = canvas


def save_all_canvases(canvases: List[Canvas]):
    put_all(CANVAS_TABLE_NAME, [x.model_dump() for x in canvases])
    put_all('canvas-dev', [x.model_dump() for x in canvases])
    st.session_state['__canvases'] = canvases


def delete_canvas(canvas: Canvas):
    delete(CANVAS_TABLE_NAME, 'id', canvas.id)
    delete('canvas-dev', 'id', canvas.id)
    del st.session_state['__canvases'][canvas.id]


def save_prompt(item):
    put(PROMPT_TABLE_NAME, item)
    put('prompts-dev', item)
    st.session_state['__prompts'][item['id']] = item


def delete_prompt(item):
    delete(PROMPT_TABLE_NAME, 'id', item['id'])
    delete('prompts-dev', 'id', item['id'])
    del st.session_state['__prompts'][item['id']]


def save_storage(key, value):
    put(STORAGE_TABLE_NAME, {'key': key, 'value': value})
    st.session_state[key] = value


def get_storage(key):
    if key not in st.session_state:
        obj = get(STORAGE_TABLE_NAME, {'key': key})
        st.session_state[key] = obj['value'] if obj else None
    return st.session_state[key]


def save_theme(item):
    put(THEMES_TABLE_NAME, item)
    put('themes-dev', item)
    st.session_state['__themes'][item['name']] = item


def save_carousel(item):
    put(CAROUSEL_TABLE_NAME, item)
    put('carousels-dev', item)
    st.session_state['__carousels'][item['name']] = item


def put(table_name, item):
    item = float_to_decimal(item)
    table = DDB_RESOURCE.Table(table_name)
    table.put_item(Item=item)


def get(table_name, key):
    table = DDB_RESOURCE.Table(table_name)
    response = table.get_item(Key=key)
    item = response.get('Item')
    item = decimal_to_float(item)
    return item


def list_all(table_name):
    table = DDB_RESOURCE.Table(table_name)
    items = scan_all(table)
    items = decimal_to_float(items)
    return items


def put_all(table_name, items):
    items = float_to_decimal(items)
    with DDB_RESOURCE.Table(table_name).batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

def delete(table_name, key_name, key_value):
    table = DDB_RESOURCE.Table(table_name)
    table.delete_item(Key={key_name: key_value})


def scan_all(table, **fields):
    # Initialize an empty list to hold all items
    all_items = []

    # If there are no filtering fields, scan the entire table
    if not fields:
        filter_exp = None
    # If there are fields, construct the filter expression
    else:
        key, value = fields.popitem()
        filter_exp = boto3.dynamodb.conditions.Attr(key).eq(value)
        for key, value in fields.items():
            filter_exp &= boto3.dynamodb.conditions.Attr(key).eq(value)

    # Perform the initial scan with the filter expression
    response = table.scan(FilterExpression=filter_exp) if filter_exp else table.scan()
    all_items.extend(response["Items"])

    # Handle pagination for filtered results
    while 'LastEvaluatedKey' in response:
        response = (table.scan(FilterExpression=filter_exp, ExclusiveStartKey=response['LastEvaluatedKey'])
                    if filter_exp else table.scan(ExclusiveStartKey=response['LastEvaluatedKey']))
        all_items.extend(response["Items"])

    return all_items


def float_to_decimal(data):
    if isinstance(data, list):
        return [float_to_decimal(item) for item in data]
    elif isinstance(data, dict):
        return {key: float_to_decimal(value) for key, value in data.items()}
    elif isinstance(data, float):
        return Decimal(str(data))
    else:
        return data


def decimal_to_float(data):
    if isinstance(data, list):
        return [decimal_to_float(item) for item in data]
    elif isinstance(data, dict):
        return {key: decimal_to_float(value) for key, value in data.items()}
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return data
