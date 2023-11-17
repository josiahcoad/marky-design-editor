from copy import deepcopy
import os
from typing import Dict, List, Literal
import pandas as pd
from pydantic import BaseModel
import streamlit as st
import boto3
import requests
from io import BytesIO
from PIL import Image

import db_utils as db
import dto


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

SB_TEMPLATE_EDTOR_URL_PREFIX = "https://www.switchboard.ai/s/canvas/editor/"
S3_URL_PREFIX = 'https://marky-image-posts.s3.amazonaws.com/'

SB_TOKEN_ST_KEY = 'sb_token'
SB_COOKIE_ST_KEY = 'sb_cookie'
FILL_VALUES_ST_KEY = 'fill_values'

DEV_URL = 'https://psuf5gocxc.execute-api.us-east-1.amazonaws.com/api'
DEV_API_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNTI1YzdmNC00ZTM5LTQ0N2ItODRlMy0xZWE5OWI3ZjA5MGYiLCJpYXQiOjE2OTUwOTQ0ODYsIm5iZiI6MTY5NTA5NDQ4NiwiZXhwIjoxNzI2NjMwNDg2fQ.G-e-NnDenhLs6HsM6ymLfQz_lTHTo8RX4oZB9I5hJI0' # admin@admin.com



if not st.session_state.get(FILL_VALUES_ST_KEY):
    st.session_state[FILL_VALUES_ST_KEY] = db.get_storage(FILL_VALUES_ST_KEY) or {
        'background_image_url': list(background_urls.values())[0],
        'logo_url': list(logo_urls.values())[0],
        'background_color': "#ecc9bf",
        'accent_color': "#cf3a72", # pink
        'text_color': "#064e84", # blue
        'text_content': text_content,
    }
    db.put_storage(FILL_VALUES_ST_KEY, st.session_state[FILL_VALUES_ST_KEY])


@st.cache_data
def get_db_templates():
    templates = db.list_canvases()
    return {
        'components': {x['name']: get_db_template(x['components']) for x in templates},
        'themes': {x['name']: x['theme'] for x in templates},
        'approved': {x['name']: x.get('approved') for x in templates},
        'notes': {x['name']: x.get('notes') for x in templates},
    }

def extract_meta(db_text_component):
    return {
        'max_characters': int(db_text_component['max_characters']),
        'all_caps': db_text_component.get('all_caps', False),
        'text_color_type': db_text_component.get('text_color_type', 'DONT_CHANGE'),
        'optional': db_text_component.get('optional', False),
    }

@st.cache_data
def get_themes():
    return {x['name']: x for x in db.list_themes()}


@st.cache_data(experimental_allow_widgets=True)
def get_sb_templates():
    # see if we have a token in persistent storage
    token = db.get_storage(SB_TOKEN_ST_KEY)
    cookie = db.get_storage(SB_COOKIE_ST_KEY)

    headers = {
        'authority': 'www.switchboard.ai',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': f"Bearer {token}",
        'Cookie': cookie,
    }

    try:
        response = requests.get('https://www.switchboard.ai/api/canvas/templates', headers=headers, timeout=10)
        success = response.status_code == 200
    except requests.exceptions.Timeout:
        st.markdown("Get new cookie [from switchboard](https://www.switchboard.ai/s/canvas)")
        text = st.text_input('cookie')
        if st.button('Submit'):
            db.put_storage(SB_COOKIE_ST_KEY, text)
            st.rerun()
        st.stop()

    if not success:
        st.markdown(f"Get new token [from switchboard](https://www.switchboard.ai/s/canvas)")
        text = st.text_input('token')
        if st.button('Submit'):
            db.put_storage(SB_TOKEN_ST_KEY, text)
            st.rerun()
        st.stop()

    templates = response.json()

    my_thumbnails = list_s3_objects()
    return {
        'components': {x['apiName']: switchboard_template(x['apiName'], x['configuration'])
                       for x in templates if x['configuration']},
        'thumbnails': {x['apiName']: my_thumbnails.get(x['apiName'], x['thumbnailUrl'])  for x in templates},
        'template_id': {x['apiName']: x['id'] for x in templates},
    }


def switchboard_template(name, components):
    del components['template']
    components = components.values()
    return dto.Canvas.from_sb(name, components)


def sb_template_to_db_components(dto.MarkyCanvas):

def sync_sb_to_db():
    st.session_state['sb_data'] = None
    st.session_state['db_data'] = None
    st.cache_data.clear()

    sb_templates: Dict[str, dto.Canvas] = sb_data['components']
    db_templates: Dict[str, dto.MarkyCanvas] = db_data['components'].values()
    all_templates: 

    for name, sb_template in sb_templates.items():
        if name not in db_templates:
            db.put_canvas(dto.MarkyCanvas.from_canvas(sb_template).as_db_item)
        elif sb_template.editable_components != db_templates[name].editable_components:
            new_canvas = dto.MarkyCanvas.from_canvas_and_partial_meta(sb_template,
                                                                      db_template,
                                                                      db_template.text_meta)
            st.session_state['db_data']['components'][template] = sb_templates[template]

    for template in db_templates:
        if template not in sb_templates:
            CANVAS_TABLE.delete_item(Key={'name': template})
            st.session_state['db_data']['components'].pop(template)



def clickable_image(image_url, target_url, image_size=100):
    markdown = f'<a href="{target_url}" target="_blank"><img src="{image_url}" width="{image_size}" height="{image_size}"></a>'
    st.markdown(markdown, unsafe_allow_html=True)
    st.image(image_url, width=image_size)


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


def list_s3_objects(bucket_name='marky-image-posts', prefix='thumbnails'):
    s3_client = boto3.client('s3')
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    return {x['Key'].removeprefix(prefix + '/').split('.')[0]: (S3_URL_PREFIX + x['Key']) for x in response.get('Contents', [])}


def get_filler_text(value, meta):
    max_characters = meta['max_characters']
    value = value[:max_characters]
    if len(value) < max_characters:
        value += IPSEM_TEXT[:max_characters - len(value)]
    return value


def display_text_containers(template_name: str, sb_template: dict, db_template: dict | None):
    st.subheader('Text Containers')
    new_meta = {}
    old_meta = db_template['text_meta'] if db_template else {}
    for key in sb_template['text_keys']:
        old_field_meta = old_meta.get(key, {}) if db_template else {}
        cols = st.columns(5)
        with cols[0]:
            st.text(key)
        with cols[1]:
            char_count = st.number_input('max characters',
                                         value=int(old_field_meta.get('max_characters', 100)),
                                         key=f'{key}_char_count-{template_name}',
                                         step=10)
        with cols[2]:
            all_caps = st.checkbox('ALL CAPS', value=old_field_meta.get('all_caps', False), key=f'{key}_all_caps-{template_name}')
        with cols[3]:
            options = ('DONT_CHANGE', 'ON_BACKGROUND', 'ON_ACCENT', 'ACCENT')
            try:
                index = options.index(old_field_meta.get('text_color_type'))
            except ValueError:
                index = 0
            text_color_type = st.selectbox('color type',
                                           options,
                                           index=index,
                                           key=f'{key}_text_color_type-{template_name}')
        with cols[4]:
            optional = st.checkbox('optional', value=old_field_meta.get('optional', False), key=f'{key}_optional-{template_name}')
    
        new_meta[key] = {
            'max_characters': char_count,
            'all_caps': all_caps,
            'text_color_type': text_color_type,
            'optional': optional,
        }

    if old_meta != new_meta:
        reload_image(template_name, sb_template, new_meta)


def reload_image(template_name, sb_template, meta):
    CANVAS_TABLE.update_item(
        Key={'name': template_name},
        UpdateExpression='SET components = :components',
        ExpressionAttributeValues={':components': sb_template_to_db_components(sb_template, meta)},
    )
    st.session_state['db_data']['components'][template_name] = \
        get_db_template(sb_template_to_db_components(sb_template, meta))
    st.text('Loading...')
    fill_canvas_and_update_thumbnail(template_name, meta)
    st.text('Done')

fill_canvas_error = st.session_state.get('fill_canvas_error')
if fill_canvas_error:
    st.error(fill_canvas_error)
    st.stop()

def fill_canvas_and_update_thumbnail(template_name, meta):
    st.toast(f"Requesting new image for {template_name}...")
    image_url = fill_canvas(template_name, st.session_state[FILL_VALUES_ST_KEY], meta)
    if image_url:
        upload_image_to_s3(image_url, template_name + '.png')
        st.session_state['sb_data']['thumbnails'][template_name] = image_url
        st.rerun()
    else:
        st.error("Error filling canvas!")


def fill_canvas(template_name, fill_values, meta):
    text_content = {field_name: get_filler_text(fill_values['text_content'][field_name], field_meta)
                    for field_name, field_meta in meta.items()}
    payload = {
        'template_name': template_name,
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


def refresh():
    st.session_state['sb_data'] = None
    st.session_state['db_data'] = None
    st.cache_data.clear()
    st.rerun()


def display_action_bar(template_name, sb_template, text_meta):
    # Unique keys for session state
    edit_key = f'edit-{template_name}'
    notes = db_data['notes'].get(template_name, '')
    col1, col2, col3, col4 = st.columns([1, 1, 2, 8])

    with col1:
        st.markdown(
            f"[Open]({SB_TEMPLATE_EDTOR_URL_PREFIX + sb_data['template_id'][template_name]})",
            unsafe_allow_html=True,
        )

    with col2:
        if st.button('🔄', key=f'optn-{template_name}'):
            reload_image(template_name, sb_template, text_meta)

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
                # Perform the update operation
                CANVAS_TABLE.update_item(
                    Key={'name': template_name},
                    UpdateExpression='SET notes = :notes',
                    ExpressionAttributeValues={':notes': edited_notes},
                )
                st.session_state['db_data']['notes'][template_name] = edited_notes
                # Update the session state to reflect the new notes and exit edit mode
                st.session_state[edit_key] = False
                # Display a toast notification
                st.toast(f'Updated notes for {template_name}', icon='🤖')
                st.rerun()
        # Display notes if not in edit mode and notes exist
        elif notes:
            st.text(f'Notes: {notes}')


def change_approval_status(template_name, approval_status):
    CANVAS_TABLE.update_item(
        Key={'name': template_name},
        UpdateExpression='SET approved = :approved',
        ExpressionAttributeValues={':approved': approval_status},
    )
    st.session_state['db_data']['approved'][template_name] = approval_status


sb_data = st.session_state.get('sb_data')
if not sb_data:
    st.session_state['sb_data'] = get_sb_templates()
    sb_data = st.session_state['sb_data'] # read copy (write to st.session_state['sb_data'])

db_data = st.session_state.get('db_data')
if not db_data:
    st.session_state['db_data'] = get_db_templates()
    db_data = st.session_state['db_data']

db_templates_for_diff = deepcopy(db_data['components'])
for template_name, template in db_templates_for_diff.items():
    db_templates_for_diff[template_name]['text_keys'] = list(sorted(template['text_meta'].keys()))
    del db_templates_for_diff[template_name]['text_meta']


template_names = list(set(sb_data['components'].keys()).union(db_data['components'].keys()))
data = {
    'name': template_names,
    'thumbnail': [sb_data['thumbnails'].get(x) for x in template_names],
    'theme': [db_data['themes'].get(x) for x in template_names],
    'approved': [db_data['approved'].get(x, False) for x in template_names],
    'notes': [db_data['notes'].get(x, '') for x in template_names],
    'in_db': [x in db_data['components'] for x in template_names],
    'in_sb': [x in sb_data['components'] for x in template_names],
    'matches': [sb_data['components'].get(x) == db_templates_for_diff.get(x) for x in template_names],
    'sb': [sb_data['components'].get(x) for x in template_names],
    'db': [db_data['components'].get(x) for x in template_names],
}


df = pd.DataFrame(data).sort_values('theme').set_index('name')
df['name'] = df.index

if not st.session_state.get('theme-choice'):
    theme_choice = st.session_state['theme-choice'] = get_storage('theme-choice')

# add filters in a  sidebar
with st.sidebar:
    theme_names = list(df.theme.unique()) + [None]
    color_editable = {name: get_themes().get(name, {}).get('color_editable', False) for name in theme_names}
    theme = st.selectbox('Theme',
                         options=theme_names,
                         index=theme_names.index(theme_choice),
                         format_func=lambda x: f'{x} {"(color)" if color_editable[x] else ""}')
    if theme != st.session_state['theme-choice']:
        st.session_state['theme-choice'] = theme
        put_storage('theme-choice', theme)

    if theme:
        df = df[df.theme == theme]
    with st.expander('More Filters'):
        template_name = st.text_input('Search Template Name')
        if template_name:
            df = df[df.name.str.contains(template_name, case=False)]
        filter_matched = st.selectbox('Matching', options=[None, True, False], index=0)
        if filter_matched is not None:
            df = df[df.matches == filter_matched]
        filter_in_db = st.selectbox('In DB', options=[None, True, False], index=0)
        if filter_in_db is not None:
            df = df[df.in_db == filter_in_db]
        filter_in_sb = st.selectbox('In SB', options=[None, True, False], index=0)
        if filter_in_sb is not None:
            df = df[df.in_sb == filter_in_sb]
        filter_has_background_image = st.selectbox('Has Background Image', options=[None, True, False], index=0)
        if filter_has_background_image is not None:
            df = df[df.has_background_image == filter_has_background_image]
        filter_has_logo = st.selectbox('Has Logo', options=[None, True, False], index=0)
        if filter_has_logo is not None:
            df = df[df.has_logo == filter_has_logo]
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
                                    key=f'background_choice-{template_name}')
        assert background_choice is not None
        new_fill_values['background_image_url'] = background_urls[background_choice]
        st.image(new_fill_values['background_image_url'], width=300)

        old_index = list(logo_urls.values()).index(fill_values['logo_url']) if 'logo_url' in fill_values else 0
        logo_choice = st.radio('Select a logo:', ('Logo 1', 'Logo 2', 'Logo 3'), index=old_index, key=f'logo_choice-{template_name}')
        assert logo_choice is not None
        new_fill_values['logo_url'] = logo_urls[logo_choice]
        st.image(new_fill_values['logo_url'], width=100)

        col1, col2, col3 = st.columns(3)
        with col1:
            new_fill_values['background_color'] = st.color_picker('Background', value=fill_values['background_color'], key=f'background_color-{template_name}')
        with col2:
            new_fill_values['accent_color'] = st.color_picker('Accent', value=fill_values['accent_color'], key=f'accent_color-{template_name}')
        with col3:
            new_fill_values['text_color'] = st.color_picker('Text', value=fill_values['text_color'], key=f'text_color-{template_name}')

        new_fill_values['text_content'] = {key: st.text_area(key, value=value, key=key)
                                           for key, value in fill_values['text_content'].items()}

        values_changed = new_fill_values != fill_values
        if values_changed:
            put_storage(FILL_VALUES_ST_KEY, new_fill_values)
            st.session_state[FILL_VALUES_ST_KEY] = new_fill_values

    if theme:
        if st.button(f"Mark '{theme}' {'uncolored' if color_editable[theme] else 'colored'}", key=f"mark-{theme}"):
            THEMES_TABLE.update_item(
                Key={'name': theme},
                UpdateExpression='SET color_editable = :colored',
                ExpressionAttributeValues={':colored': not color_editable[theme]},
            )
            refresh()

    if st.button("Pull Switchboard Changes"):
        refresh()

    st.info("⬆️ Run whenever you add a component or change it's name")

    if st.button('Push to Prod'):
        prod_themes_table = boto3.resource('dynamodb').Table('themes-prod')
        prod_canvas_table = boto3.resource('dynamodb').Table('switchboard-prod')
        delete_all(prod_themes_table, 'name')
        put_all(prod_themes_table, THEMES_TABLE.scan()['Items'])
        delete_all(prod_canvas_table, 'name')
        put_all(prod_canvas_table, CANVAS_TABLE.scan()['Items'])

    global_notes = st.session_state.get('global_notes') or get_storage('global_notes')
    new_global_notes = st.text_area('Global Notes', value=global_notes, height=500)
    if new_global_notes != global_notes:
        put_storage('global_notes', new_global_notes)
        st.session_state['global_notes'] = new_global_notes


load = 50
if len(df) == 0:
    st.write('No templates found matching filters')
for row in df.head(load).sort_index().itertuples():
    cols = st.columns(6)
    with cols[0]:
        if row.thumbnail:
            template_id = st.session_state['sb_data']['template_id'][row.name]
            st.image(st.session_state['sb_data']['thumbnails'][row.name], width=image_size)
    with cols[1]:
        approval_status = st.checkbox('Approved', value=row.approved, key=f'approval_status-{row.name}')
        if bool(approval_status) != bool(row.approved): # ie status changed
            change_approval_status(row.name, approval_status)
    with cols[2]:
        theme = st.selectbox('theme', options=theme_names, index=theme_names.index(row.theme), key=f'theme-{row.name}')
        if theme != row.theme:
            CANVAS_TABLE.update_item(
                Key={'name': row.name},
                UpdateExpression='SET theme = :theme',
                ExpressionAttributeValues={':theme': theme},
            )
            st.session_state['db_data']['themes'][row.name] = theme
            st.rerun()
    with cols[3]:
        st.markdown(f'Switchboard')
        st.markdown(f"- bg-color: {[x['name'] for x in row.sb.get('background_color_layer', [])]}")
        st.markdown(f"- accent: {[x['name'] for x in row.sb.get('accent_color_layer', [])]}")
        st.markdown(f'- bg-photo: {"✅" if row.sb.get("has_background_image") else "❌"}')
        st.markdown(f'- logo: {"✅" if row.sb.get("has_logo") else "❌"}')
    with cols[4]:
        st.markdown(f'Database')
        st.markdown(f"- bg-color: {[x['key'] for x in row.db.get('background_color_layer', [])]}")
        st.markdown(f"- accent: {[x['key'] for x in row.db.get('accent_color_layer', [])]}")
        st.markdown(f'- bg-photo: {"✅" if row.db.get("has_background_image") else "❌"}')
        st.markdown(f'- logo: {"✅" if row.db.get("has_logo") else "❌"}')
    with cols[5]:
        st.markdown(f'- in-db: {"✅" if row.in_db else "❌"}')
        st.markdown(f'- in-sb: {"✅" if row.in_sb else "❌"}')
        # st.markdown(f'- match: {"✅" if row.matches else "❌"}',
        #             help=format_diff(get_json_diff(row.sb, db_templates_for_diff[row.name]))
        #                  if (row.sb and row.name in db_templates_for_diff) else None)


    if row.in_sb:
        display_action_bar(row.name, row.sb, db_data['components'].get(row.name, {}).get('text_meta'))
        with st.expander(row.name):
            display_text_containers(row.name, row.sb, row.db)
    if row.in_db and not row.in_sb:
        st.text(row.name)
        if st.button('Delete from DB', key=f'{row.name}_delete'):
            CANVAS_TABLE.delete_item(Key={'name': row.name})
            if template_name in st.session_state['db_data']['components']:
                del st.session_state['db_data']['components'][template_name]
            st.rerun()

if load < len(df):
    if st.button('Load More'):
        load += 50
        st.rerun()
