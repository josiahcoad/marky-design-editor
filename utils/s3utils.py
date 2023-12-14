from typing import Dict
import boto3
import requests
from io import BytesIO
from PIL import Image

import requests



S3_URL_PREFIX = 'https://marky-image-posts.s3.amazonaws.com/'



def upload_image_to_s3(image_url, object_name, bucket_name='marky-image-posts', prefix='thumbnails'):
    object_name = f'{prefix}/{object_name}'
    # Download the image from the URL
    s3_client = boto3.client('s3')
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))
    # Resize the image to 500x500 pixels
    image = image.resize((500, 500))
    # Convert image to PNG
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)  # Compress the image
    buffer.seek(0)
    # Upload the image to S3
    s3_client = boto3.client('s3')
    s3_client.upload_fileobj(buffer, bucket_name, object_name)
    return S3_URL_PREFIX + object_name


def list_s3_objects(bucket_name='marky-image-posts', prefix='thumbnails') -> Dict[str, str]:
    s3_client = boto3.client('s3')
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    return {x['Key'].removeprefix(prefix + '/').split('.')[0]: (S3_URL_PREFIX + x['Key']) for x in response.get('Contents', [])}
