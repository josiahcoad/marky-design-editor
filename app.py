from copy import deepcopy
import os
from typing import Dict
import pandas as pd
import streamlit as st
import boto3
import requests
from io import BytesIO
from PIL import Image


os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

st.set_page_config(layout='wide')


cookies = {
    '_ga': 'GA1.1.519206553.1682785335',
    'intercom-id-dtjeof09': '93f2077c-f6e0-4bab-bca1-4c50d9fa7579',
    'intercom-device-id-dtjeof09': '1102363e-9c4c-4f9f-aad7-c3a8eec015f8',
    '__stripe_mid': 'c6024ef6-7631-4951-8b45-b85ed94615a27b2ff9',
    'csrf_token': '51a95e43-064f-4565-8d12-d80d578c12d6',
    '_ga_HT90M3YVTX': 'GS1.1.1699403411.66.0.1699403413.0.0.0',
    '__stripe_sid': 'ef4d18b8-0ad4-4c9e-a4f3-ac740e03b36cef248a',
    'connect.sid': 's%3A-GWlPUhxM3oDf488VZ6lPN_8ZhEzQ-Yn.oA7jF18HZXB7ABfXwgJ3KUsDkG6n5PiI6LEKImG%2Fh5w',
    'intercom-session-dtjeof09': 'QWJLSVBRcHlubnRpWDlQemFRSEFWWlhCY3Zxa2prOEcxVjBBMnpUSjhFZWMrai9JNkNiUGcrbUFSODNRb1RPcS0tMnJsYVdwS3ExZW04SXkyMkMrQWNzQT09--2f1a8482b4daf4d53980db62cee2003fa8f1b315',
    'fs_lua': '1.1699407654260',
    'fs_uid': '#15F16C#f9454a6a-f127-4d00-b217-518b0417d000:e4076e56-059c-49f5-bb8a-096420be7d9f:1699405261770::3#bea14a1f#/1714321356',
    'AWSALBTG': 'jUOk9f30U1/VdwAcY3px+W1WXimHC1ETq2zyedMxmBeea9AuxMoYUXM5GKMYJiXQmJYq+bAXoEHWeruoa8t/vhTBj4O3giP7W2BgBJlQDcSIzsIN2vZz0J/MVeX8mC8oJjQfg6sUnk3nf+zSwzLchMQlWbJv9+mmfuBTk87IQwY3',
    'AWSALBTGCORS': 'jUOk9f30U1/VdwAcY3px+W1WXimHC1ETq2zyedMxmBeea9AuxMoYUXM5GKMYJiXQmJYq+bAXoEHWeruoa8t/vhTBj4O3giP7W2BgBJlQDcSIzsIN2vZz0J/MVeX8mC8oJjQfg6sUnk3nf+zSwzLchMQlWbJv9+mmfuBTk87IQwY3',
}

ipsem = "This Python package runs a Markov chain algorithm over the surviving works of the Roman historian Tacitus to generate naturalistic-looking pseudo-Latin gibberish. Useful when you need to generate dummy text as a placeholder in templates, etc. Brigantes femina duce exurere coloniam, expugnare castra, ac nisi felicitas in tali"

switchboard_template_url_prefix = "https://www.switchboard.ai/s/canvas/editor/"

sb_token_st_key = 'sb_token'
headers = {
    'authority': 'www.switchboard.ai',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'authorization': f"Bearer {st.session_state.get(sb_token_st_key)}",
}


dev_url = 'https://psuf5gocxc.execute-api.us-east-1.amazonaws.com/api'
dev_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNTI1YzdmNC00ZTM5LTQ0N2ItODRlMy0xZWE5OWI3ZjA5MGYiLCJpYXQiOjE2OTUwOTQ0ODYsIm5iZiI6MTY5NTA5NDQ4NiwiZXhwIjoxNzI2NjMwNDg2fQ.G-e-NnDenhLs6HsM6ymLfQz_lTHTo8RX4oZB9I5hJI0' # admin@admin.com
canvas_table = boto3.resource('dynamodb').Table('switchboard-dev')
themes_table = boto3.resource('dynamodb').Table('themes-dev')

@st.cache_data
def get_db_templates():
    scan_response = canvas_table.scan()
    templates = scan_response['Items']
    return {
        'components': {x['name']: db_template(x['components']) for x in templates},
        'themes': {x['name']: x['theme'] for x in templates},
        'approved': {x['name']: x.get('approved') for x in templates},
        'notes': {x['name']: x.get('notes') for x in templates},
    }

@st.cache_data
def get_themes():
    scan_response = themes_table.scan()
    themes = scan_response['Items']
    return {x['name']: x for x in themes}


@st.cache_data(experimental_allow_widgets=True)
def get_sb_templates():
    response = requests.get('https://www.switchboard.ai/api/canvas/templates', cookies=cookies, headers=headers)
    success = response.status_code == 200
    if not success:
        st.markdown(f"Get new token [from switchboard](https://www.switchboard.ai/s/canvas)")
        st.session_state[sb_token_st_key] = st.text_input('token')
        if st.session_state[sb_token_st_key]:
            refresh()
        st.stop()

    templates = response.json()

    my_thumbnails = list_s3_objects()
    return {
        'components': {x['apiName']: switchboard_template(x['configuration']) for x in templates if x['configuration']},
        'thumbnails': {x['apiName']: my_thumbnails.get(x['apiName']) or x['thumbnailUrl']  for x in templates},
    }


def db_template(components):
    def has_image_named(name):
        return any((x['type'] == 'IMAGE' and x['key'] == name) for x in components)

    def has_shape_named(name):
        return any((x['type'] == 'SHAPE' and x['key'] == name) for x in components)

    return {
        'has_background_image': has_image_named('image1'),
        'has_background_shape': has_shape_named('object1'),
        'has_logo': has_image_named('logo'),
        'has_logo_bg': has_image_named('logo-bg'),
        'has_background_color': has_image_named('colored-layer-background'),
        'has_accent_color': has_image_named('colored-layer'),
        'text_meta': {x['key']: x for x in components if x['type'] == 'TEXT'},
    }


def clickable_image(image_url, target_url, image_size=100):
    markdown = f'<a href="{target_url}" target="_blank"><img src="{image_url}" width="{image_size}" height="{image_size}"></a>'
    st.markdown(markdown, unsafe_allow_html=True)


def switchboard_template(components):
    del components['template']
    components = components.values()

    def has_image_named(name, require_svg=False):
        if require_svg:
            return any((x['type'] == 'image'
                        and x['name'] == name
                        and x['imageSvgFill']
                        and x['url']['file']['filename'].endswith('svg'))
                        for x in components)

        return any((x['type'] == 'image' and x['name'] == name) for x in components)

    def has_shape_named(name):
        return any((x['type'] == 'rectangle' and x['name'] == name) for x in components)

    return {
        'has_background_image': has_image_named('image1'),
        'has_background_shape': has_shape_named('object1'),
        'has_logo': has_image_named('logo'),
        'has_logo_bg': has_image_named('logo-bg'),
        'has_background_color': has_image_named('colored-layer-background', require_svg=True),
        'has_accent_color': has_image_named('colored-layer', require_svg=True),
        'text_keys': sorted([x['name'] for x in components if x['type'] == 'text']),
    }


def get_json_diff(a: dict, b: dict):
    missing = set(a.keys()) - set(b.keys())
    extra = set(b.keys()) - set(a.keys())
    difference = {o: (a[o], b[o]) for o in set(a.keys()) & set(b.keys()) if a[o] != b[o]}
    payload = {}
    if missing:
        payload['missing'] = missing
    if extra:
        payload['extra'] = extra
    if difference:
        payload['diff'] = difference
    return payload


def format_diff(diff):
    if not diff:
        return ''
    payload = []
    if missing := diff.get('missing'):
        payload.append(f'Missing in db: {missing}')
    if extra := diff.get('extra'):
        payload.append(f'Extra in db: {extra}')
    if diff := diff.get('diff'):
        for key, (sb, db) in diff.items():
            payload.append(f'{key}: sb={sb}, db={db}')
    return '\n'.join(payload)


def sb_template_to_db_components(sb_template: dict, text_meta: dict):
    def image_component(name):
        return {
            'type': 'IMAGE',
            'key': name,
        }
    
    def shape_component(name):
        return {
            'type': 'SHAPE',
            'key': name,
        }
    
    def text_component(name, meta):
        return {
            'type': 'TEXT',
            'key': name,
            **meta,
        }

    def background_image_component():
        return image_component('image1')
    
    def background_shape_component():
        return shape_component('object1')
    
    def logo_component():
        return image_component('logo')
    
    def logo_bg_component():
        return image_component('logo-bg')
    
    def background_color_component():
        return image_component('colored-layer-background')

    def accent_color_component():
        return image_component('colored-layer')

    def text_components(text_meta: Dict[str, dict]):
        return [text_component(key, value) for key, value in text_meta.items()]

    inserts = {
        'has_background_image': background_image_component,
        'has_background_shape': background_shape_component,
        'has_logo': logo_component,
        'has_logo_bg': logo_bg_component,
        'has_background_color': background_color_component,
        'has_accent_color': accent_color_component,
    }
    components = [f() for k, f in inserts.items() if sb_template[k]]
    components.extend(text_components(text_meta))
    return components


s3_url_prefix = 'https://marky-image-posts.s3.amazonaws.com/'

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
    return s3_url_prefix + object_name


def list_s3_objects(bucket_name='marky-image-posts', prefix='thumbnails'):
    s3_client = boto3.client('s3')
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    return {x['Key'].split('.')[0]: (s3_url_prefix + x['Key']) for x in response.get('Contents', [])}


def get_filler_text(key, meta):
    if meta['optional']:
        return ''
    if key == 'title':
        s = "I wish I knew this when I started! It would have saved me a lot of time and money."
        return s[:meta['max_characters']] if len(s) > meta['max_characters'] else s + ipsem[:meta['max_characters'] - len(s)]
    if key in ['content', 'content1', 'content2']:
        s = "Start with the minimum viable product. Don't try to build the perfect product from the start. If you do, you'll waste a lot of time and money."
        return s[:meta['max_characters']] if len(s) > meta['max_characters'] else s + ipsem[:meta['max_characters'] - len(s)]
    if key == 'cta':
        s = "Get started today! It's free to sign up and you can cancel anytime."
        return s[:meta['max_characters']] if len(s) > meta['max_characters'] else s + ipsem[:meta['max_characters'] - len(s)]
    return ipsem[:meta['max_characters']]


# Function to display row details and handle the demo button functionality
def display_template_components(template_name: str, sb_template: dict, db_template: dict | None):
    st.subheader('Text Containers')
    new_meta = {}
    old_meta = db_template['text_meta'] if db_template else {}
    old_meta = {k: {**v, 'max_characters': int(v['max_characters'])} for k, v in old_meta.items()} if old_meta else {}
    old_meta_subset = {}
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
        old_meta_subset[key] = {
            'max_characters': old_field_meta.get('max_characters'),
            'all_caps': old_field_meta.get('all_caps', False),
            'text_color_type': old_field_meta.get('text_color_type', 'DONT_CHANGE'),
            'optional': old_field_meta.get('optional', False),
        }


    # set defaults
    background_url = default_background_url =  "https://images.unsplash.com/photo-1695331453337-d5f95078f78e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwxfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85"
    logo_url = default_logo_url = 'https://marky-image-posts.s3.amazonaws.com/IMG_0526.jpeg'
    background_color = default_background_color = "#ecc9bf"
    accent_color = default_accent_color = "#cf3a72" # pink
    text_color = default_text_color = "#064e84" # blue
    text_values = default_text_values = {key: get_filler_text(key, meta) for key, meta in new_meta.items()}
    values_changed = False

    # Configuration for values
    if st.checkbox('Adjust Fill Values', key=f'adjust-values-{template_name}'):

        selectors = len([sb_template[key]
                        for key in ('has_background_image', 'has_background_shape', 'has_logo', 'has_background_color', 'has_accent_color')
                        if sb_template[key]])
        if any(field_meta['text_color_type'] not in ('ACCENT', 'DONT_CHANGE') for field_meta in new_meta.values()):
            selectors += 1
        cols = st.columns(selectors) if selectors > 0 else []

        col = 0
        if sb_template['has_background_image']:
            with cols[0]:
                background_choice = st.radio('Select a background image:',
                                            ('Image 1', 'Image 2', 'Image 3'),
                                            index=0,
                                            key=f'background_choice-{template_name}')
                # Mapping choice to URL
                background_urls = {
                    'Image 1': "https://images.unsplash.com/photo-1695331453337-d5f95078f78e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwxfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
                    'Image 2': "https://images.unsplash.com/photo-1694459471238-6e55eb657848?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwyfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
                    'Image 3': "https://images.unsplash.com/photo-1694472655814-71e6c5a7ade8?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwzfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
                }
                assert background_choice is not None
                background_url = background_urls[background_choice]
                st.image(background_url, width=300)
            col += 1

        if sb_template['has_logo']:
            with cols[col]:
                logo_choice = st.radio('Select a logo:', ('Logo 1', 'Logo 2', 'Logo 3'), index=0, key=f'logo_choice-{template_name}')
                assert logo_choice is not None
                logo_urls = {
                    'Logo 1': 'https://marky-image-posts.s3.amazonaws.com/380106565_1398612124371856_5370535347247435473_n.png',
                    'Logo 2': 'https://marky-image-posts.s3.amazonaws.com/pearlite%20emporium%20logo.jpg',
                    'Logo 3': 'https://marky-image-posts.s3.amazonaws.com/IMG_0526.jpeg',
                }
                logo_url = logo_urls[logo_choice]
                st.image(logo_url, width=100)
            col += 1

        if sb_template['has_accent_color']:
            with cols[col]:
                accent_color = st.color_picker('Accent Color', value=default_accent_color, key=f'accent_color-{template_name}')
            col += 1

        if sb_template['has_background_color']:
            with cols[col]:
                background_color = st.color_picker('Background Color', value=default_background_color, key=f'background_color-{template_name}')
            col += 1

        if any(field_meta['text_color_type'] not in ('ACCENT', 'DONT_CHANGE') for field_meta in new_meta.values()):
            with cols[col]:
                text_color = st.color_picker('Text Color', value=default_text_color, key=f'text_color-{template_name}')
            col += 1

        text_values = {key: st.text_area(key, value=value, key=f'{key}-{template_name}')
                        for key, value in default_text_values.items()}
        
        values_changed = (background_url != default_background_url
                          or logo_url != default_logo_url
                          or background_color != default_background_color
                          or accent_color != default_accent_color
                          or text_color != default_text_color
                          or any(text_values[key] != get_filler_text(key, meta) for key, meta in new_meta.items()))

    if st.button("Update DB & Demo", key=f'demo-{template_name}') or (old_meta_subset != new_meta) or values_changed:
        canvas_table.update_item(
            Key={'name': template_name},
            UpdateExpression='SET components = :components',
            ExpressionAttributeValues={':components': sb_template_to_db_components(sb_template, new_meta)},
        )
        st.toast("Requesting new image...")
        image_url = fill_canvas(template_name, background_color, accent_color, text_color, background_url, logo_url, text_values)
        if image_url:
            clickable_image(image_url, switchboard_template_url_prefix + template_id, image_size=300)
            upload_image_to_s3(image_url, template_name + '.png')
        else:
            st.error("Error filling canvas!")


def fill_canvas(template_name, background_color, accent_color, text_color, background_url, logo_url, text_fields):
    payload = {
        'template_name': template_name,
        'background_color': background_color,
        'accent_color': accent_color,
        'text_color': text_color,
        'background_image_url': background_url,
        'logo_url': logo_url,
        'text_fields': text_fields,
    }

    response = requests.post(dev_url + '/v1/posts/fill-canvas',
                             json=payload,
                             headers={'Authorization': f'Bearer {dev_token}'}).json()
    return response.get('image_url')


def refresh():
    st.cache_data.clear()
    st.rerun()


def display_notes(template_name, notes_from_db):
    # Unique keys for session state
    edit_key = f'edit-{template_name}'
    notes_key = f'notes-{template_name}'
    notes = st.session_state.get(notes_key, notes_from_db)

    col1, col2 = st.columns([1, 9])

    with col1:
        edit_button_label = 'Edit Notes' if notes else 'Add Notes'
        if st.button(edit_button_label, key=f'edit-notes-{template_name}'):
            # Toggle the edit state
            st.session_state[edit_key] = not st.session_state.get(edit_key, False)

    with col2:
        # If in edit mode, display the text area
        if st.session_state.get(edit_key, False):
            edited_notes = st.text_area('Notes', value=notes, key=notes_key)
            if st.button('Save', key=f'save-{template_name}'):
                # Perform the update operation
                canvas_table.update_item(
                    Key={'name': template_name},
                    UpdateExpression='SET notes = :notes',
                    ExpressionAttributeValues={':notes': edited_notes},
                )
                # Update the session state to reflect the new notes and exit edit mode
                st.session_state[edit_key] = False
                # Display a toast notification
                st.toast(f'Updated notes for {template_name}', icon='🤖')
        # Display notes if not in edit mode and notes exist
        elif notes:
            st.text(f'Notes: {notes}')


def change_approval_status(template_name, approval_status):
    print(f'changing approval status for {template_name} to {approval_status}')
    canvas_table.update_item(
        Key={'name': template_name},
        UpdateExpression='SET approved = :approved',
        ExpressionAttributeValues={':approved': approval_status},
    )
    refresh()


sb_data = get_sb_templates() # we want to update this later
db_data = get_db_templates()
db_templates_for_diff = deepcopy(db_data['components'])
for k, v in db_templates_for_diff.items():
    db_templates_for_diff[k]['text_keys'] = list(sorted(v['text_meta'].keys()))
    del db_templates_for_diff[k]['text_meta']


template_names = list(set(sb_data['components'].keys()).union(db_data['components'].keys()))
data = {
    'name': template_names,
    'thumbnail': [sb_data['thumbnails'].get(x) for x in template_names],
    'has_background_image': [sb_data['components'].get(x, {}).get('has_background_image') for x in template_names],
    'has_background_shape': [sb_data['components'].get(x, {}).get('has_background_shape') for x in template_names],
    'has_logo': [sb_data['components'].get(x, {}).get('has_logo') for x in template_names],
    'has_background_color': [sb_data['components'].get(x, {}).get('has_background_color') for x in template_names],
    'has_accent_color':  [sb_data['components'].get(x, {}).get('has_accent_color') for x in template_names],
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

# add filters in a  sidebar
with st.sidebar:
    with st.expander('Filters'):
        theme_names = [None] + list(df.theme.unique())
        color_editable = {name: get_themes().get(name, {}).get('color_editable', False) for name in theme_names}
        template_name = st.text_input('Template Name')
        if template_name:
            df = df[df.name.str.contains(template_name, case=False)]
        theme = st.selectbox('Theme',
                            options=[None] + list(df.theme.unique()),
                            index=0,
                            format_func=lambda x: f'{x} {"(color)" if color_editable[x] else ""}')
        if theme:
            df = df[df.theme == theme]
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
        filter_has_background_shape = st.selectbox('Has Background Shape', options=[None, True, False], index=0)
        if filter_has_background_shape is not None:
            df = df[df.has_background_shape == filter_has_background_shape]
        filter_has_logo = st.selectbox('Has Logo', options=[None, True, False], index=0)
        if filter_has_logo is not None:
            df = df[df.has_logo == filter_has_logo]
        filter_has_background_color = st.selectbox('Has Background Color', options=[None, True, False], index=0)
        if filter_has_background_color is not None:
            df = df[df['has_background_color'] == filter_has_background_color]
        filter_has_accent_color = st.selectbox('Has Accent Color', options=[None, True, False], index=0)
        if filter_has_accent_color is not None:
            df = df[df['has_accent_color'] == filter_has_accent_color]
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

    if theme:
        if st.button(f"Mark '{theme}' {'uncolored' if color_editable[theme] else 'colored'}", key=f"mark-{theme}"):
            themes_table.update_item(
                Key={'name': theme},
                UpdateExpression='SET color_editable = :colored',
                ExpressionAttributeValues={':colored': not color_editable[theme]},
            )
            st.text('Done')
            refresh()

    if st.button('Pull Data'):
        refresh()

    if st.button('Push to Prod'):
        prod_themes_table = boto3.resource('dynamodb').Table('themes-prod')
        prod_canvas_table = boto3.resource('dynamodb').Table('switchboard-prod')
        for name, theme in get_themes().items():
            prod_themes_table.put_item(Item=theme)
        st.toast("Pushed themes to prod")
        for name, template in get_db_templates().items():
            prod_canvas_table.put_item(Item=template)
        st.toast("Pushed templates to prod")

# if (~df.matches).any():
#     st.error('Mismatched Templates! Please Fix by deleting from DB or updating in SB then syncing to db.')
# if theme and color_editable[theme] and sb_data['components'].get(theme) != db_data['components'].get(theme):
#     st.error('Theme is not colored')

load = 50
if len(df) == 0:
    st.write('No templates found matching filters')
for row in df.head(load).itertuples():
    cols = st.columns(6)
    with cols[0]:
        if row.thumbnail:
            template_id = row.thumbnail.split('/')[-1].split('.')[0]
            clickable_image(row.thumbnail, switchboard_template_url_prefix + template_id, image_size=image_size)
    with cols[1]:
        approval_status = st.checkbox('Approved', value=row.approved, key=f'approval_status-{row.name}')
        if bool(approval_status) != bool(row.approved): # ie status changed
            change_approval_status(row.name, approval_status)
    with cols[2]:
        st.text(row.theme)
    with cols[3]:
        st.markdown(f'- bg-color: {"✅" if row.has_background_color else "❌"}')
        st.markdown(f'- accent: {"✅" if row.has_accent_color else "❌"}')
    with cols[4]:
        st.markdown(f'- bg-photo: {"✅" if row.has_background_image else "❌"}')
        st.markdown(f'- bg-shape: {"✅" if row.has_background_shape else "❌"}')
        st.markdown(f'- logo: {"✅" if row.has_logo else "❌"}')
    with cols[5]:
        st.markdown(f'- in-db: {"✅" if row.in_db else "❌"}')
        st.markdown(f'- in-sb: {"✅" if row.in_sb else "❌"}')
        st.markdown(f'- match: {"✅" if row.matches else "❌"}',
                    help=format_diff(get_json_diff(row.sb, db_templates_for_diff[row.name]))
                         if (row.sb and row.name in db_templates_for_diff) else None)


    if row.in_sb:
        display_notes(row.name, row.notes)
        with st.expander(row.name):
            display_template_components(row.name, row.sb, row.db)
    if row.in_db and not row.in_sb:
        st.text(row.name)
        if st.button('Delete from DB', key=f'{row.name}_delete'):
            canvas_table.delete_item(Key={'name': row.name})
            df.drop(row.name, inplace=True)
            st.cache_data.clear()
            st.rerun()

if load < len(df):
    if st.button('Load More'):
        load += 50
        st.rerun()