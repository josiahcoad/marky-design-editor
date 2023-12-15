from typing import Dict
import streamlit as st
from utils.s3utils import list_s3_objects, upload_image_to_s3

THUMBNAILS_ST_KEY = '__canvas_thumbnail_urls'

def list_thumbnails(force_cache_refresh=False) -> Dict[str, str]:
    if force_cache_refresh or THUMBNAILS_ST_KEY not in st.session_state:
        with st.spinner("Getting thumbnails from S3..."):
            st.session_state[THUMBNAILS_ST_KEY] = list_s3_objects()
    return st.session_state[THUMBNAILS_ST_KEY]


def get_thumbnail(canvas_name: str, first=True):
    thumbnail_key = canvas_name + ('' if first else '_2')
    thumbnails = list_thumbnails()
    return thumbnails.get(thumbnail_key)


def save_thumbnail(canvas_name: str, url: str, first=True, upload_to_s3=True):
    thumbnail_key = canvas_name + ('' if first else '_2')
    if upload_to_s3:
        with st.spinner(f"Uploading thumbnail '{thumbnail_key}' to S3..."):
            upload_image_to_s3(url, thumbnail_key + '.png')
    if THUMBNAILS_ST_KEY not in st.session_state:
        list_thumbnails()
    st.session_state[THUMBNAILS_ST_KEY][thumbnail_key] = url
