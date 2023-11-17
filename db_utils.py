import boto3

CANVAS_TABLE_NAME = 'switchboard-dev'
THEMES_TABLE_NAME = 'themes-dev'
STORAGE_TABLE_NAME = 'internal-design-editor'
DDB_RESOURCE = boto3.resource('dynamodb')

def put_canvas(item):
    put(CANVAS_TABLE_NAME, item)

def list_canvases():
    return list_all(CANVAS_TABLE_NAME)

def list_themes():
    return list_all(THEMES_TABLE_NAME)

def put_storage(key, value):
    put(STORAGE_TABLE_NAME, {'key': key, 'value': value})


def get_storage(key):
    return get(STORAGE_TABLE_NAME, key)


def put(table_name, item):
    table = DDB_RESOURCE.Table(table_name)
    table.put_item(Item=item)


def get(table_name, key):
    table = DDB_RESOURCE.Table(table_name)
    return table.get_item(Key=key)['Item']


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
