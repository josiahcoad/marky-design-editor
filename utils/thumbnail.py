from typing import Dict
import streamlit as st
from utils.s3utils import list_s3_objects, upload_image_to_s3

THUMBNAILS_ST_KEY = '__canvas_thumbnail_urls'

def list_thumbnails(force_cache_refresh=True) -> Dict[str, str]:
    if force_cache_refresh or THUMBNAILS_ST_KEY not in st.session_state:
        st.session_state[THUMBNAILS_ST_KEY] = list_s3_objects()
    return st.session_state[THUMBNAILS_ST_KEY]

thumbnails = list_thumbnails()

def get_thumbnail(canvas_name: str, first=True):
    return thumbnails.get(canvas_name + ('' if first else '_2'))


def save_thumbnail(canvas_name: str, url: str, first=True):
    upload_image_to_s3(url, canvas_name + ('' if first else '_2') + '.png')
    st.session_state[THUMBNAILS_ST_KEY] = url
