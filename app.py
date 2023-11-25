from copy import deepcopy
import os
from typing import Dict
import pandas as pd

from requests import HTTPError
import streamlit as st
import requests
from utils.dto import Canvas
import utils.db as db
from utils.get_canvas_data import get_canvas_data
from utils.s3utils import upload_image_to_s3


os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

st.set_page_config(layout='wide')


logo_urls = {
    'Logo 1': 'https://marky-image-posts.s3.amazonaws.com/IMG_0526.jpeg',
    'Logo 2': 'https://marky-image-posts.s3.amazonaws.com/380106565_1398612124371856_5370535347247435473_n.png',
    'Logo 3': 'https://marky-image-posts.s3.amazonaws.com/pearlite%20emporium%20logo.jpg',
    'Logo 4': 'https://marky-image-posts.s3.amazonaws.com/OAO_OFFICIAL_LOGO_v2.png',
    'Logo 5': 'https://marky-image-posts.s3.amazonaws.com/wowbrow%20logo.png',
}

background_urls = {
    'Image 1': "https://images.unsplash.com/photo-1694459471238-6e55eb657848?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwyfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
    'Image 2': "https://images.unsplash.com/photo-1695331453337-d5f95078f78e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwxfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
    'Image 3': "https://images.unsplash.com/photo-1694472655814-71e6c5a7ade8?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwzfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
}

text_content = {
    'title': "I wish I knew this when I started! It would have saved me a lot of time and money.",
    'content': "Start with the minimum viable product. Don't try to build the perfect product from the start. If you do, you'll waste a lot of time and money.",
    'cta': "Get started today! It's free to sign up and you can cancel anytime.",
    'content1': "Start with the minimum viable product. Don't try to build the perfect product from the start. If you do, you'll waste a lot of time and money.",
    'content2': "Start with the minimum viable product. Don't try to build the perfect product from the start. If you do, you'll waste a lot of time and money.",
}

IPSEM_TEXT = "This Python package runs a Markov chain algorithm over the surviving works of the Roman historian Tacitus to generate naturalistic-looking pseudo-Latin gibberish. Useful when you need to generate dummy text as a placeholder in templates, etc. Brigantes femina duce exurere coloniam, expugnare castra, ac nisi felicitas in tali"

SB_TOKEN_ST_KEY = 'sb_token'
SB_COOKIE_ST_KEY = 'sb_cookie'
FILL_VALUES_ST_KEY = 'fill_values'
THEME_CHOICE_ST_KEY = 'theme_choice'
GLOBAL_NOTES_ST_KEY = 'global_notes'

DEV_URL = 'https://psuf5gocxc.execute-api.us-east-1.amazonaws.com/api'
DEV_API_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNTI1YzdmNC00ZTM5LTQ0N2ItODRlMy0xZWE5OWI3ZjA5MGYiLCJpYXQiOjE2OTUwOTQ0ODYsIm5iZiI6MTY5NTA5NDQ4NiwiZXhwIjoxNzI2NjMwNDg2fQ.G-e-NnDenhLs6HsM6ymLfQz_lTHTo8RX4oZB9I5hJI0' # admin@admin.com

SB_TEMPLATE_EDITOR_URL_PREFIX = "https://www.switchboard.ai/s/canvas/editor/"

if not st.session_state.get(FILL_VALUES_ST_KEY):
    st.session_state[FILL_VALUES_ST_KEY] = (db.get_storage(FILL_VALUES_ST_KEY) or {
        'background_image_url': list(background_urls.values())[0],
        'logo_url': list(logo_urls.values())[0],
        'background_color': "#ecc9bf",
        'accent_color': "#cf3a72", # pink
        'text_color': "#064e84", # blue
        'text_content': text_content,
        'font_url': None,
    })
    db.put_storage(FILL_VALUES_ST_KEY, st.session_state[FILL_VALUES_ST_KEY])


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
            st.markdown(f"Get new token [from switchboard](https://www.switchboard.ai/s/canvas)")
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
            new_component.optional = st.checkbox('optional', value=old_component.optional, key=f'{old_component.name}_optional-{canvas.name}')

    if new_canvas != canvas:
        reload_image(new_canvas)


def reload_image(canvas: Canvas):
    st.session_state['canvases'][canvas.name] = canvas
    db.put_canvas(canvas)

    with st.spinner("Wait for it..."):
        fill_canvas_and_update_thumbnail(canvas)


fill_canvas_error = st.session_state.get('fill_canvas_error')
if fill_canvas_error:
    st.error(fill_canvas_error)
    st.stop()


def fill_canvas_and_update_thumbnail(canvas: Canvas):
    st.toast(f"Requesting new image for {canvas.name}...")
    image_url = fill_canvas(canvas, st.session_state[FILL_VALUES_ST_KEY])
    if image_url:
        upload_image_to_s3(image_url, canvas.name + '.png')
        canvas.thumbnail_url = image_url
        st.session_state['canvases'][canvas.name] = canvas
        st.rerun()
    else:
        st.error("Error filling canvas!")


def fill_canvas(canvas: Canvas, fill_values: Dict[str, str]):
    # TODO
    text_content = {x.name: get_filler_text(fill_values['text_content'][x.name], x.max_characters)
                    for x in canvas.text_components}
    payload = {
        'canvas_name': canvas.name,
        **fill_values,
        'text_content': text_content,
    }

    response = requests.post(DEV_URL + '/v1/posts/fill-canvas',
                             json=payload,
                             headers={'Authorization': f'Bearer {DEV_API_TOKEN}'})
    if not response.ok:
        st.session_state['fill_canvas_error'] = response.text
        st.rerun()
        return None
    return response.json()['image_url']


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
            if st.button('Save', key=f'save-{template_name}'):
                canvas.notes = edited_notes
                db.put_canvas(canvas)
                st.session_state['canvases'][template_name] = canvas
                # Update the session state to reflect the new notes and exit edit mode
                st.session_state[edit_key] = False
                st.toast(f'Updated notes for {template_name}', icon='🤖')
                st.rerun()
        # Display notes if not in edit mode and notes exist
        elif notes:
            st.text(f'Notes: {notes}')



def refresh():
    st.session_state['canvases'] = None
    st.cache_data.clear()
    st.rerun()


canvases = st.session_state.get('canvases')
if not canvases:
    canvases = get_canvases()
    st.session_state['canvases'] = canvases


data = {x.name: x.model_dump(exclude='components') for x in canvases.values()}
df = pd.DataFrame(data).T
df = df.sort_values('theme').set_index('name')
df['name'] = df.index

if not (theme_choice := st.session_state.get(THEME_CHOICE_ST_KEY)):
    theme_choice = st.session_state[THEME_CHOICE_ST_KEY] = db.get_storage(THEME_CHOICE_ST_KEY)

themes = get_themes()

# add filters in a  sidebar
with st.sidebar:
    theme_names = list(df.theme.unique()) + ['All']
    color_editable = {name: get_themes().get(name, {}).get('color_editable', False) for name in theme_names}
    theme = st.selectbox('Theme',
                         options=theme_names,
                         index=theme_names.index(theme_choice),
                         format_func=lambda x: f'{x} {"(color)" if color_editable[x] else ""}')
    if theme != st.session_state[THEME_CHOICE_ST_KEY]:
        st.session_state[THEME_CHOICE_ST_KEY] = theme
        db.put_storage(THEME_CHOICE_ST_KEY, theme)

    if theme != 'All':
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

    # Configuration for values
    with st.expander('Change Fill Values'):
        fill_values = st.session_state[FILL_VALUES_ST_KEY]
        new_fill_values = {}
        old_index = list(background_urls.values()).index(fill_values['background_image_url'])
        background_choice = st.radio('Select a background image:',
                                    ('Image 1', 'Image 2', 'Image 3'),
                                    index=old_index,
                                    key='background_choice')
        assert background_choice is not None
        new_fill_values['background_image_url'] = background_urls[background_choice]
        st.image(new_fill_values['background_image_url'], width=300)

        old_index = list(logo_urls.values()).index(fill_values['logo_url']) if 'logo_url' in fill_values else 0
        logo_choice = st.radio('Select a logo:', ('Logo 1', 'Logo 2', 'Logo 3'), index=old_index, key='logo_choice')
        assert logo_choice is not None
        new_fill_values['logo_url'] = logo_urls[logo_choice]
        st.image(new_fill_values['logo_url'], width=100)

        col1, col2, col3 = st.columns(3)
        with col1:
            new_fill_values['background_color'] = st.color_picker('Background', value=fill_values['background_color'], key='background_color')
        with col2:
            new_fill_values['accent_color'] = st.color_picker('Accent', value=fill_values['accent_color'], key='accent_color')
        with col3:
            new_fill_values['text_color'] = st.color_picker('Text', value=fill_values['text_color'], key='text_color')

        new_fill_values['text_content'] = {key: st.text_area(key, value=value, key=key)
                                           for key, value in fill_values['text_content'].items()}

        values_changed = new_fill_values != fill_values
        if values_changed:
            db.put_storage(FILL_VALUES_ST_KEY, new_fill_values)
            st.session_state[FILL_VALUES_ST_KEY] = new_fill_values

    if theme:
        if st.button(f"Mark '{theme}' {'uncolored' if color_editable[theme] else 'colored'}", key=f"mark-{theme}"):
            theme['color_editable'] = not color_editable[theme]
            db.put_theme(theme)
            refresh()

    if st.button("Pull Switchboard Changes"):
        refresh()

    st.info("⬆️ Run whenever you add a component or change it's name")

    # if st.button("Push to Prod"):
    #     db.delete_all('themes-prod', 'name')
    #     db.put_all('themes-prod', db.list_themes())
    #     db.delete_all('canvas-prod', 'name')
    #     db.put_all('canvas-prod', db.list_canvases())

    global_notes = st.session_state.get(GLOBAL_NOTES_ST_KEY) or db.get_storage(GLOBAL_NOTES_ST_KEY)
    new_global_notes = st.text_area('Global Notes', value=global_notes, height=500)
    if new_global_notes != global_notes:
        db.put_storage(GLOBAL_NOTES_ST_KEY, new_global_notes)
        st.session_state[GLOBAL_NOTES_ST_KEY] = new_global_notes


load = 50
if len(df) == 0:
    st.write('No templates found matching filters')
for name in df.head(load).sort_index().index:
    canvas = canvases[name]
    cols = st.columns(4)
    with cols[0]:
        st.image(canvas.thumbnail_url, width=image_size)
    with cols[1]:
        approval_status = st.checkbox('Approved', value=canvas.approved, key=f'approval_status-{canvas.name}')
        if bool(approval_status) != bool(canvas.approved): # ie status changed
            canvas.approved = approval_status
            db.put_canvas(canvas)
            st.session_state['canvases'][canvas.name] = canvas
    with cols[2]:
        theme = st.selectbox('theme', options=theme_names, index=theme_names.index(canvas.theme), key=f'theme-{canvas.name}')
        if theme != canvas.theme:
            canvas.theme = theme
            db.put_canvas(canvas)
            st.session_state['canvases'][canvas.name] = canvas
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
