import os
import boto3
from utils.dto import Canvas

CANVAS_TABLE_NAME = 'canvas-dev'
THEMES_TABLE_NAME = 'themes-dev'
STORAGE_TABLE_NAME = 'internal-design-editor'

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
DDB_RESOURCE = boto3.resource('dynamodb')

def put_canvas(canvas: Canvas):
    put(CANVAS_TABLE_NAME, canvas.model_dump())

def list_canvases():
    return [Canvas(**x) for x in list_all(CANVAS_TABLE_NAME)]

def list_themes():
    return list_all(THEMES_TABLE_NAME)

def put_storage(key, value):
    put(STORAGE_TABLE_NAME, {'key': key, 'value': value})


def put_theme(item):
    put(THEMES_TABLE_NAME, item)


def get_storage(key):
    obj = get(STORAGE_TABLE_NAME, {'key': key})
    return obj['value'] if obj else None


def put(table_name, item):
    table = DDB_RESOURCE.Table(table_name)
    table.put_item(Item=item)


def get(table_name, key):
    table = DDB_RESOURCE.Table(table_name)
    response = table.get_item(Key=key)
    return response.get('Item')


def list_all(table_name):
    table = DDB_RESOURCE.Table(table_name)
    return table.scan()['Items']


def put_all(table_name, items):
    with DDB_RESOURCE.Table(table_name).batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)


def delete_all(table_name, key_name):
    items = list_all(table_name)
    table = DDB_RESOURCE.Table(table_name)
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={key_name: item[key_name]})
