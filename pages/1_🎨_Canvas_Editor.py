from copy import deepcopy
from datetime import datetime
from typing import Dict, List
import uuid
import pandas as pd

from requests import HTTPError
import streamlit as st
import requests
from utils.dto import Canvas
import utils.db as db
from utils.get_canvas_data import get_canvas_data
from utils.s3utils import upload_image_to_s3

import aiohttp
import asyncio

st.set_page_config(layout='wide', page_title="Canvas Editor", page_icon="🎨")

LOGO_URLS = {
    'Logo 1': 'https://marky-image-posts.s3.amazonaws.com/IMG_0526.jpeg',
    'Logo 2': 'https://marky-image-posts.s3.amazonaws.com/380106565_1398612124371856_5370535347247435473_n.png',
    'Logo 3': 'https://marky-image-posts.s3.amazonaws.com/pearlite%20emporium%20logo.jpg',
    'Logo 4': 'https://marky-image-posts.s3.amazonaws.com/OAO_OFFICIAL_LOGO_v2.png',
    'Logo 5': 'https://marky-image-posts.s3.amazonaws.com/wowbrow%20logo.png',
}

BACKGROUND_URLS = {
    'Image 1': "https://images.unsplash.com/photo-1694459471238-6e55eb657848?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwyfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
    'Image 2': "https://images.unsplash.com/photo-1695331453337-d5f95078f78e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwxfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
    'Image 3': "https://images.unsplash.com/photo-1694472655814-71e6c5a7ade8?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwzfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
}

TEXT_CONTENT = {
    'title': "I wish I knew this when I started! It would have saved me a lot of time and money.",
    'content': "Start with the minimum viable product. Don't try to build the perfect product from the start. If you do, you'll waste a lot of time and money.",
    'cta': "Get started today! It's free to sign up and you can cancel anytime.",
    'content1': "Start with the minimum viable product. Don't try to build the perfect product from the start. If you do, you'll waste a lot of time and money.",
    'content2': "Start with the minimum viable product. Don't try to build the perfect product from the start. If you do, you'll waste a lot of time and money.",
}

IPSEM_TEXT = "This Python package runs a Markov chain algorithm over the surviving works of the Roman historian Tacitus to generate naturalistic-looking pseudo-Latin gibberish. Useful when you need to generate dummy text as a placeholder in templates, etc. Brigantes femina duce exurere coloniam, expugnare castra, ac nisi felicitas in tali"

BUSINESS_NAMES = ['Business 1', 'Business 2']

SB_TOKEN_ST_KEY = 'sb_token'
SB_COOKIE_ST_KEY = 'sb_cookie'
FILL_VALUES_ST_KEY = 'fill_values'
THEME_CHOICE_ST_KEY = 'theme_choice'
GLOBAL_NOTES_ST_KEY = 'global_notes'

DEV_URL = 'https://psuf5gocxc.execute-api.us-east-1.amazonaws.com/api'
DEV_API_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNTI1YzdmNC00ZTM5LTQ0N2ItODRlMy0xZWE5OWI3ZjA5MGYiLCJpYXQiOjE2OTUwOTQ0ODYsIm5iZiI6MTY5NTA5NDQ4NiwiZXhwIjoxNzI2NjMwNDg2fQ.G-e-NnDenhLs6HsM6ymLfQz_lTHTo8RX4oZB9I5hJI0' # admin@admin.com

SB_TEMPLATE_EDITOR_URL_PREFIX = "https://www.switchboard.ai/s/canvas/editor/"


def refresh():
    st.session_state['canvases'] = None
    st.cache_data.clear()
    st.rerun()


@st.cache_data
def get_themes():
    return {x['name']: x for x in db.list_themes()}


def get_canvases():
    # see if we have a token in persistent storage
    token = db.get_storage(SB_TOKEN_ST_KEY)
    cookie = db.get_storage(SB_COOKIE_ST_KEY)

    try:
        canvases = get_canvas_data(token, cookie)
    except HTTPError as e:
        if e.response.status_code == 401:
            st.markdown("Get new token [from switchboard](https://www.switchboard.ai/s/canvas)")
            text = st.text_input('token')
            if st.button('Submit'):
                print("text", text)
                db.put_storage(SB_TOKEN_ST_KEY, text)
                st.rerun()
            st.stop()
        else:
            st.markdown("Get new cookie [from switchboard](https://www.switchboard.ai/s/canvas)")
            text = st.text_input('cookie')
            if st.button('Submit'):
                db.put_storage(SB_COOKIE_ST_KEY, text)
                st.rerun()
            st.stop()
    
    return canvases


def clickable_image(image_url, target_url, image_size=100):
    markdown = f'<a href="{target_url}" target="_blank"><img src="{image_url}" width="{image_size}" height="{image_size}"></a>'
    st.markdown(markdown, unsafe_allow_html=True)
    st.image(image_url, width=image_size)


def get_filler_text(value, max_characters):
    if value is None:
        return IPSEM_TEXT[:max_characters]
    value = value[:max_characters]
    if len(value) < max_characters:
        value += IPSEM_TEXT[:max_characters - len(value)]
    return value


def display_text_containers(canvas: Canvas):
    st.subheader('Text Containers')

    new_canvas = deepcopy(canvas)
    for old_component, new_component in zip(canvas.text_components, new_canvas.text_components):
        cols = st.columns(5)
        with cols[0]:
            st.text(old_component.name)
        with cols[1]:
            new_component.max_characters = st.number_input('max characters',
                                             value=old_component.max_characters,
                                             key=f'{old_component.name}_char_count-{canvas.name}',
                                             step=10)
        with cols[2]:
            new_component.all_caps = st.checkbox('ALL CAPS', value=old_component.all_caps, key=f'{old_component.name}_all_caps-{canvas.name}')
        with cols[3]:
            options = ('DONT_CHANGE', 'ON_BACKGROUND', 'ON_ACCENT', 'ACCENT')
            try:
                index = options.index(old_component.color_type)
            except ValueError:
                index = 0
            new_component.color_type = st.selectbox('color type',
                                      options,
                                      index=index,
                                      key=f'{old_component.name}_text_color_type-{canvas.name}')
        with cols[4]:
            new_component.instructions = st.text_input('custom instructions',
                                                       value=old_component.instructions,
                                                       key=f'{old_component.name}_instructions-{canvas.name}')

    if new_canvas != canvas:
        reload_image(new_canvas)


def reload_image(canvas: Canvas):
    st.session_state['canvases'][canvas.name] = canvas
    db.put_canvas(canvas)

    with st.spinner("Wait for it..."):
        if any(x.instructions for x in canvas.text_components):
            regenerate_meme(canvas)
        else:
            fill_canvas_and_update_thumbnail(canvas)


fill_canvas_error = st.session_state.get('fill_canvas_error')
if fill_canvas_error:
    st.error(fill_canvas_error)
    st.stop()


def fill_canvas_and_update_thumbnail(canvas: Canvas):
    st.toast(f"Requesting new image for {canvas.name}...")
    fill_values_list = [st.session_state[f"{FILL_VALUES_ST_KEY}-{name}"] for name in BUSINESS_NAMES]
    canvases = [canvas, canvas]
    image_urls = asyncio.run(fill_canvases_async(canvases, fill_values_list))
    image_url, image_url_2 = image_urls
    if image_url:
        upload_image_to_s3(image_url, canvas.name + '.png')
        canvas.thumbnail_url = image_url
        st.session_state['canvases'][canvas.name] = canvas
    else:
        st.session_state['fill_canvas_error'] = "Error filling canvas!"

    if image_url_2:
        upload_image_to_s3(image_url_2, canvas.name + "_2" + '.png')
        canvas.thumbnail_url_2 = image_url_2
        st.session_state['canvases'][canvas.name] = canvas
    else:
        st.session_state['fill_canvas_error'] = "Error filling canvas 2!"
    st.rerun()


def regenerate_meme(canvas: Canvas):
    payload = {
        # template settings
        'canvas_names': [canvas.name],
        # content settings
        'business_context': ("Business name: Joes Mugs.\n"
                            "Summary: We create custom mugs using a process that only takes 5 minutes."),
        'topic': "5 minute mugs",
        'knowledge': "phone: 125-6767-1716",
        'prompt': "",
        'intention': "entertain",
        'cta': "buy mug",
        'approximate_caption_length_chars': 300,
        'language': "English",
        'caption_suffix': "",
        # brand_settings
        'brand_color_hex': '#FFFFFF',
        'background_color_hex': '#FFFFFF',
        'text_color_hex': '#FFFFFF',
        'logo_url': None,
        'font_url': None
    }
    response = requests.post(f"{DEV_URL}/v1/posts/controlled",
                             json=payload,
                             headers={'Authorization': f'Bearer {DEV_API_TOKEN}'},
                             ).json()
    media_urls = response['media_urls']
    image_url = list(media_urls.values())[0]

    upload_image_to_s3(image_url, canvas.name + '.png')
    canvas.thumbnail_url = image_url
    st.session_state['canvases'][canvas.name] = canvas

    st.rerun()


async def fill_canvases_async(canvases: List[Canvas], fill_values_list: List[Dict[str, str]]):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for canvas, fill_values in zip(canvases, fill_values_list):
            payload = fill_canvas_prepare_payload(canvas, fill_values)
            task = asyncio.ensure_future(fill_canvas_make_request_async(session, payload))
            tasks.append(task)
        image_urls = await asyncio.gather(*tasks)
    return image_urls


async def fill_canvas_make_request_async(session, payload):
    async with session.post(DEV_URL + '/v1/posts/fill-canvas',
                            json=payload,
                            headers={'Authorization': f'Bearer {DEV_API_TOKEN}'}) as response:
        return (await response.json())['image_url']


def fill_canvas_prepare_payload(canvas: Canvas, fill_values: Dict[str, str]):
    text_content = {x.name: get_filler_text(fill_values['text_content'].get(x.name), x.max_characters)
                    for x in canvas.text_components}
    payload = {
        'canvas_name': canvas.name,
        **fill_values,
        'text_content': text_content,
    }
    return payload


def fill_canvas_make_request(payload):
    response = requests.post(DEV_URL + '/v1/posts/fill-canvas',
                             json=payload,
                             headers={'Authorization': f'Bearer {DEV_API_TOKEN}'})
    return response


def display_action_bar(canvas: Canvas):
    template_name = canvas.name
    # Unique keys for session state
    edit_key = f'edit-{template_name}'
    notes = canvas.notes
    col1, col2, col3, col4 = st.columns([1, 1, 2, 8])

    with col1:
        st.markdown(
            f"[Open]({SB_TEMPLATE_EDITOR_URL_PREFIX + st.session_state['canvases'][template_name].id})",
            unsafe_allow_html=True,
        )

    with col2:
        if st.button('🔄', key=f'open-{template_name}'):
            reload_image(canvas)

    with col3:
        edit_button_label = 'Edit Notes' if notes else 'Add Notes'
        if st.button(edit_button_label, key=f'edit-notes-{template_name}'):
            # Toggle the edit state
            st.session_state[edit_key] = not st.session_state.get(edit_key, False)

    with col4:
        # If in edit mode, display the text area
        if st.session_state.get(edit_key, False):
            edited_notes = st.text_area('Notes', value=notes, key=f'notes-{template_name}')
            if notes != edited_notes:
                canvas.notes = edited_notes
                db.put_canvas(canvas)
                st.session_state['canvases'][template_name] = canvas
                # Update the session state to reflect the new notes and exit edit mode
                st.session_state[edit_key] = False
                st.toast(f'Updated notes for {template_name}', icon='🤖')
                st.rerun()
        # Display notes if not in edit mode and notes exist
        elif notes:
            st.text(notes)


canvases = st.session_state.get('canvases')
if not canvases:
    canvases = get_canvases()
    st.session_state['canvases'] = canvases


def get_fill_values(business_name):
    storage_key = f"{FILL_VALUES_ST_KEY}-{business_name}"
    if not st.session_state.get(storage_key):
        st.session_state[storage_key] = (db.get_storage(storage_key) or {
            'background_image_url': list(BACKGROUND_URLS.values())[0],
            'logo_url': list(LOGO_URLS.values())[0],
            'background_color': "#ecc9bf",
            'accent_color': "#cf3a72", # pink
            'text_color': "#064e84", # blue
            'text_content': TEXT_CONTENT,
            'font_url': None,
        })
        db.put_storage(storage_key, st.session_state[storage_key])
    return st.session_state[storage_key]


def edit_business_pane(business_name):
    with st.expander(f"Edit {business_name}"):
        storage_key = f"{FILL_VALUES_ST_KEY}-{business_name}"
        fill_values = get_fill_values(business_name)
        new_fill_values = {}
        old_index = list(BACKGROUND_URLS.values()).index(fill_values['background_image_url'])
        background_choice = st.radio('Select a background image:',
                                    ('Image 1', 'Image 2', 'Image 3'),
                                    index=old_index,
                                    key=f'background_choice-{business_name}')
        assert background_choice is not None
        new_fill_values['background_image_url'] = BACKGROUND_URLS[background_choice]
        st.image(new_fill_values['background_image_url'], width=300)

        old_index = list(LOGO_URLS.values()).index(fill_values['logo_url']) if 'logo_url' in fill_values else 0
        logo_choice = st.radio('Select a logo:', ('Logo 1', 'Logo 2', 'Logo 3'), index=old_index,
                               key=f'logo_choice-{business_name}')
        assert logo_choice is not None
        new_fill_values['logo_url'] = LOGO_URLS[logo_choice]
        st.image(new_fill_values['logo_url'], width=100)

        col1, col2, col3 = st.columns(3)
        with col1:
            new_fill_values['background_color'] = st.color_picker('Background', value=fill_values['background_color'],
                                                                  key=f'background_color-{business_name}')
        with col2:
            new_fill_values['accent_color'] = st.color_picker('Accent', value=fill_values['accent_color'],
                                                                  key=f'accent_color-{business_name}')
        with col3:
            new_fill_values['text_color'] = st.color_picker('Text', value=fill_values['text_color'],
                                                                  key=f'text_color-{business_name}')

        new_fill_values['text_content'] = {key: st.text_area(key, value=value, key=f'{key}-{business_name}')
                                        for key, value in fill_values['text_content'].items()}

        values_changed = new_fill_values != fill_values
        if values_changed:
            db.put_storage(storage_key, new_fill_values)
            st.session_state[storage_key] = new_fill_values


def sidebar():
    data = {x.name: x.model_dump(exclude='components') for x in canvases.values()}
    df = pd.DataFrame(data).T
    df = df.sort_values('theme').set_index('name')
    df['name'] = df.index

    if not (theme_choice := st.session_state.get(THEME_CHOICE_ST_KEY)):
        theme_choice = st.session_state[THEME_CHOICE_ST_KEY] = db.get_storage(THEME_CHOICE_ST_KEY)

    with st.sidebar:
        theme_names = list(df.theme.unique()) + ['All']
        index_choice_index = theme_names.index(theme_choice) if theme_choice in theme_names else 0
        theme = st.selectbox('Theme', options=theme_names, index=index_choice_index)
        if theme != st.session_state[THEME_CHOICE_ST_KEY]:
            st.session_state[THEME_CHOICE_ST_KEY] = theme
            db.put_storage(THEME_CHOICE_ST_KEY, theme)

        if theme != 'All':
            if theme is None:
                df = df[df.theme.isna()]
            else:
                df = df[df.theme == theme]
        with st.expander('More Filters'):
            search_template_name = st.text_input('Search Template Name')
            if search_template_name:
                df = df[df.name.str.contains(search_template_name, case=False)]
            filter_has_logo = st.selectbox('Has Logo', options=[None, True, False], index=0)
            if filter_has_logo is not None:
                df = df[canvases[df.name].has_logo == filter_has_logo]
            filter_approved = st.selectbox('Approved', options=[None, True, False], index=0)
            if filter_approved is not None:
                df = df[df['approved'] == filter_approved]
            filter_notes = st.selectbox('Notes', options=[None, True, False], index=0)
            if filter_notes is not None:
                if filter_notes:
                    df = df[df['notes'].apply(lambda x: x is not None and len(x) > 0)]
                else:
                    df = df[(df['notes'] == '') | (df['notes'].isna())]

        image_size = st.slider('Image Size', min_value=100, max_value=300, value=150, step=50)

        edit_business_pane(BUSINESS_NAMES[0])
        edit_business_pane(BUSINESS_NAMES[1])

        if st.button("Pull Switchboard Changes"):
            refresh()

        st.info("⬆️ Run whenever you add a component or change it's name")

        with st.expander('Create Theme'):
            name = st.text_input('Name')
            theme_canvases_chosen = st.multiselect('Canvases',
                                                   options=[x.name for x in canvases.values() if x.theme is None])
            if st.button('Create', disabled=not (name and theme_canvases_chosen)):
                with st.spinner("Wait for it..."):
                    for c in theme_canvases_chosen:
                        canvases[c].theme = name
                        db.put_canvas(canvases[c])
                        st.session_state['canvases'][c] = canvases[c]
                    db.put_theme({'id': str(uuid.uuid4()), 'created_at': datetime.utcnow().isoformat(), 'name': name})
                    refresh()

        global_notes = st.session_state.get(GLOBAL_NOTES_ST_KEY) or db.get_storage(GLOBAL_NOTES_ST_KEY)
        new_global_notes = st.text_area('Global Notes', value=global_notes, height=500)
        if new_global_notes != global_notes:
            db.put_storage(GLOBAL_NOTES_ST_KEY, new_global_notes)
            st.session_state[GLOBAL_NOTES_ST_KEY] = new_global_notes

    return df, image_size


def main_table(df, image_size):
    theme_names = list(get_themes().keys()) + [None]
    load = 50
    if len(df) == 0:
        st.write('No templates found matching filters')
    for name in df.head(load).sort_index().index:
        canvas = canvases[name]
        cols = st.columns(4)
        with cols[0]:
            st.image(canvas.thumbnail_url, width=image_size)
        with cols[1]:
            if canvas.theme != 'meme':
                if thumbnail_url := canvas.thumbnail_url_2:
                    st.image(thumbnail_url, width=image_size)
                else:
                    st.write("click refresh")
        with cols[2]:
            approval_status = st.checkbox('Approved', value=canvas.approved, key=f'approval_status-{canvas.name}')
            if bool(approval_status) != bool(canvas.approved): # ie status changed
                canvas.approved = approval_status
                db.put_canvas(canvas)
                st.session_state['canvases'][canvas.name] = canvas
            theme = st.selectbox('theme', options=theme_names, index=theme_names.index(canvas.theme), key=f'theme-{canvas.name}')
            if theme != canvas.theme:
                canvas.theme = theme
                db.put_canvas(canvas)
                st.session_state['canvases'][canvas.name] = canvas
                st.rerun()
        with cols[3]:
            st.markdown(f'Switchboard Components')
            st.markdown(f"- bg-color: {[x.name for x in canvas.background_colored_layer]}")
            st.markdown(f"- accent: {[x.name for x in canvas.accent_colored_layer]}")
            st.markdown(f'- bg-photo: {"✅" if canvas.has_background_photo else "❌"}')
            st.markdown(f'- logo: {"✅" if canvas.has_logo else "❌"}')

        display_action_bar(canvas)
        with st.expander(canvas.name):
            display_text_containers(canvas)


    if load < len(df):
        if st.button('Load More'):
            load += 50
            st.rerun()


df, image_size = sidebar()
main_table(df, image_size)
