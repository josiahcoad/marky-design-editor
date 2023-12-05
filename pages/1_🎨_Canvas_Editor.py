from copy import deepcopy
from datetime import datetime
import uuid
import pandas as pd

from requests import HTTPError
import streamlit as st
from utils.api import fill_canvases, SELECTED_PROMPT_ST_KEY
from utils.dto import Canvas
import utils.db as db
from utils.get_canvas_data import get_canvas_data
from utils.s3utils import upload_image_to_s3
from utils.db import list_businesses, list_prompts, list_users
from utils.business_formaters import format_business_context, format_facts


st.set_page_config(layout='wide', page_title="Canvas Editor", page_icon="🎨")

NUM_BUSINESSES = 2

SB_TOKEN_ST_KEY = 'sb_token'
SB_COOKIE_ST_KEY = 'sb_cookie'
BUSINESS_ST_KEY = 'selected_businesses'
THEME_CHOICE_ST_KEY = 'theme_choice'
GLOBAL_NOTES_ST_KEY = 'global_notes'
AVATAR_URL_ST_KEY = 'avatar_url'

SB_TEMPLATE_EDITOR_URL_PREFIX = "https://www.switchboard.ai/s/canvas/editor/"

def refresh():
    st.session_state['canvases'] = None
    st.cache_data.clear()
    st.rerun()


@st.cache_data
def get_themes():
    return {x['name']: x for x in db.list_themes()}


@st.cache_data
def get_users():
    users = list_users()
    return {x['id']: x for x in users}

users = get_users()

@st.cache_data
def get_businesses():
    businesses = list_businesses()
    businesses = {x['title']: {'brand': users[x['user_id']]['brand'], **x} for x in businesses if x['user_id'] in users}
    return businesses



@st.cache_data
def get_prompts():
    prompts = list_prompts()
    return [x['prompt'] for x in prompts]




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
        old_instructions = [x.instructions for x in canvas.text_components]
        new_instructions = [x.instructions for x in new_canvas.text_components]
        reload_image(new_canvas, use_dummy_data=old_instructions == new_instructions)


def reload_image(canvas: Canvas, use_dummy_data):
    st.session_state['canvases'][canvas.name] = canvas
    db.put_canvas(canvas)

    assert NUM_BUSINESSES == 2
    businesses = [st.session_state[f"{BUSINESS_ST_KEY}-{i}"] for i in range(NUM_BUSINESSES)]
    canvases = [canvas for _ in range(NUM_BUSINESSES)]
    st.toast(f"Requesting {NUM_BUSINESSES} new images for {canvas.name}...")
    with st.spinner("Wait for it..."):
        image_urls = fill_canvases(canvases, businesses, use_dummy_data=use_dummy_data)

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


fill_canvas_error = st.session_state.get('fill_canvas_error')
if fill_canvas_error:
    st.error(fill_canvas_error)
    st.stop()


def display_action_bar(canvas: Canvas):
    template_name = canvas.name
    # Unique keys for session state
    edit_key = f'edit-{template_name}'
    notes = canvas.notes
    col1, col2, col3, col4 = st.columns([1, 1, 2, 8])

    with col1:
        if st.button('🔄', key=f'open-{template_name}', help="Regenerate using dummy data"):
            reload_image(canvas, use_dummy_data=True)

    with col2:
        if st.button('🦄', key=f'open-{template_name}-smart', help="Regenerate using prompt"):
            reload_image(canvas, use_dummy_data=False)

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


def edit_business_pane(business_index):
    with st.expander(f"Pick Business {business_index+1}"):
        def full_brand(brand):
            return all([brand['logo'], brand['background_color'], brand['color'], brand['text_color']])

        storage_key = f"{BUSINESS_ST_KEY}-{business_index}"
        businesses = get_businesses()
        businesses = {k: x for k, x in businesses.items() if full_brand(x['brand'])}
        old_selected_business = st.session_state.get(storage_key)
        if not old_selected_business:
            old_selected_business = db.get_storage(storage_key)
        business_names = list(businesses.keys())
        index = (business_names.index(old_selected_business['title'])
                 if (old_selected_business and old_selected_business['title'] in business_names) else 0)
        selected_business_name = st.selectbox("Business", businesses, key=f"select-business-{business_index}", index=index)
        business = businesses[selected_business_name]
        if not old_selected_business or selected_business_name != old_selected_business['title']:
            db.put_storage(storage_key, business)
        
        st.session_state[storage_key] = business
        st.session_state[storage_key]['brand']['avatar'] = st.session_state[AVATAR_URL_ST_KEY]

        logo = business['brand']['logo']
        st.image(logo, width=100)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.color_picker('Background', value=business['brand']['background_color'],
                            key=f'background_color-{business_index}', disabled=True)
        with col2:
            st.color_picker('Accent', value=business['brand']['color'],
                            key=f'accent_color-{business_index}', disabled=True)
        with col3:
            st.color_picker('Text', value=business['brand']['text_color'],
                            key=f'text_color-{business_index}', disabled=True)

        context = format_business_context(business)
        st.text(f"Business: {context}")

        facts = format_facts(business)
        st.text(f"Facts: {facts}")

        topic = business['topics'][0]['body']
        st.text(f"Topic: {topic}")


def sidebar():
    data = {x.name: x.model_dump(exclude='components') for x in canvases.values()}
    df = pd.DataFrame(data).T
    df = df.sort_values('theme').set_index('name')
    df['name'] = df.index

    if not (theme_choice := st.session_state.get(THEME_CHOICE_ST_KEY)):
        theme_choice = st.session_state[THEME_CHOICE_ST_KEY] = db.get_storage(THEME_CHOICE_ST_KEY)

    with st.sidebar:
        theme_names = ['All'] + list(df.theme.unique())
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

        if st.button("Pull Switchboard Changes"):
            refresh()
        st.info("⬆️ Run whenever you add a component or change it's name")

        st.session_state[SELECTED_PROMPT_ST_KEY] = st.selectbox('Prompt', options=get_prompts())

        for i in range(NUM_BUSINESSES):
            edit_business_pane(i)

        avatar_url = st.text_input('Avatar URL',
                                   value=st.session_state.get(AVATAR_URL_ST_KEY) or db.get_storage(AVATAR_URL_ST_KEY))
        if avatar_url:
            st.image(avatar_url, width=100)
        if avatar_url != st.session_state.get(AVATAR_URL_ST_KEY):
            st.session_state[AVATAR_URL_ST_KEY] = avatar_url
            db.put_storage(AVATAR_URL_ST_KEY, avatar_url)

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
    theme_names = [None] + list(get_themes().keys())
    load = 50
    if len(df) == 0:
        st.write('No templates found matching filters')
    for name in df.head(load).sort_index().index:
        canvas = canvases[name]
        cols = st.columns(4)
        with cols[0]:
            clickable_image(canvas.thumbnail_url, SB_TEMPLATE_EDITOR_URL_PREFIX + canvas.id, image_size=image_size)
        with cols[1]:
            if thumbnail_url := canvas.thumbnail_url_2:
                clickable_image(thumbnail_url, SB_TEMPLATE_EDITOR_URL_PREFIX + canvas.id, image_size=image_size)
            else:
                st.write("click refresh")
        with cols[2]:
            approval_status = st.checkbox('Approved', value=canvas.approved, key=f'approval_status-{canvas.name}')
            if bool(approval_status) != bool(canvas.approved): # ie status changed
                canvas.approved = approval_status
                db.put_canvas(canvas)
                st.session_state['canvases'][canvas.name] = canvas
            if canvas.theme not in theme_names:
                canvas.theme = None
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
            st.markdown(f'- avatar: {"✅" if canvas.has_avatar else "❌"}')

        display_action_bar(canvas)
        with st.expander(canvas.name):
            display_text_containers(canvas)


    if load < len(df):
        if st.button('Load More'):
            load += 50
            st.rerun()


df, image_size = sidebar()
main_table(df, image_size)
