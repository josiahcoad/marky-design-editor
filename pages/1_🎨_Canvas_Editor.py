from copy import deepcopy
from datetime import datetime
import uuid
import pandas as pd
from slugify import slugify
from typing import List

from requests import HTTPError
import streamlit as st
from utils.clickable_image import clickable_image
from utils.instructions import fill_section_instructions
from utils.marky import fill_canvases, SELECTED_PROMPT_ST_KEY
from utils.dto import Canvas
import utils.db as db
from utils.switchboard import update_canvases_with_switchboard
from utils.business_formaters import format_business_context, format_facts
from utils.thumbnail import get_thumbnail, save_thumbnail


st.set_page_config(layout='wide', page_title="Canvas Editor", page_icon="🎨")

SB_TOKEN_ST_KEY = 'sb_token'
SB_COOKIE_ST_KEY = 'sb_cookie'
BUSINESS1_ST_KEY = 'selected_business_1'
BUSINESS2_ST_KEY = 'selected_business_2'
THEME_CHOICE_ST_KEY = 'theme_choice'
GLOBAL_NOTES_ST_KEY = 'global_notes'
AVATAR_URL_ST_KEY = 'avatar_url'

SB_TEMPLATE_EDITOR_URL_PREFIX = "https://www.switchboard.ai/s/canvas/editor/"


themes = db.list_themes()
businesses = db.list_users_joined_businesses(only_full_businesses=True)
prompts = db.list_prompts()
canvases = db.list_canvases()
carousels = db.list_carousels()
canvas_map = {x.name: x for x in canvases}


def fetch_canvases_from_switchboard():
    token = db.get_storage(SB_TOKEN_ST_KEY)
    cookie = db.get_storage(SB_COOKIE_ST_KEY)

    try:
        with st.spinner("Pulling data from switchboard..."):
            updated = update_canvases_with_switchboard(token, cookie)
            st.toast(f"Updated {len(updated)} canvases from switchboard: {[x.name for x in updated]}", icon='🤖')
        db.clear_canvas_cache()
        db.list_canvases() # refills cache
        return True
    except HTTPError as e:
        if e.response.status_code == 401:
            st.markdown("Get new token [from switchboard](https://www.switchboard.ai/s/canvas)")
            if (text := st.text_input('token', key='sb_token_input')):
                db.save_storage(SB_TOKEN_ST_KEY, text)
            st.stop()
        else:
            st.markdown("Get new cookie [from switchboard](https://www.switchboard.ai/s/canvas)")
            if (text := st.text_input('cookie', key='sb_cookie_input')):
                db.save_storage(SB_COOKIE_ST_KEY, text)
            st.stop()
        return False


st.session_state['need_fetch_from_switchboard'] = st.session_state.get('need_fetch_from_switchboard', False)
if st.session_state['need_fetch_from_switchboard']:
    # see if we have a token in persistent storage
    success = fetch_canvases_from_switchboard()
    if success:
        st.session_state['need_fetch_from_switchboard'] = False


def display_text_containers(canvas: Canvas):
    st.subheader('Text Containers')

    new_canvas = deepcopy(canvas)
    for old_component, new_component in zip(canvas.text_components, new_canvas.text_components):
        cols = st.columns([1, 1, 1, 1, 2])
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
                                                       value=old_component.instructions or fill_section_instructions(old_component.name),
                                                       key=f'{old_component.name}_instructions-{canvas.name}')

    if new_canvas != canvas:
        old_instructions = [x.instructions for x in canvas.text_components]
        new_instructions = [x.instructions for x in new_canvas.text_components]
        db.save_canvas(new_canvas)
        reload_image(new_canvas, use_dummy_data=True)


def reload_image(canvas: Canvas, use_dummy_data):
    businesses = [st.session_state.get(BUSINESS1_ST_KEY), st.session_state.get(BUSINESS2_ST_KEY)]
    canvases = [canvas, canvas]
    st.toast(f"Requesting 2 new images for {canvas.name}...")
    with st.spinner("Wait for it..."):
        image_urls = fill_canvases(canvases, businesses, use_dummy_data=use_dummy_data)

    image_url, image_url_2 = image_urls
    if image_url:
        save_thumbnail(canvas.name, image_url)
    else:
        st.session_state['fill_canvas_error'] = "Error filling canvas!"

    if image_url_2:
        save_thumbnail(canvas.name, image_url_2, first=False)
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
                db.save_canvas(canvas)
                # Update the session state to reflect the new notes and exit edit mode
                st.session_state[edit_key] = False
                st.toast(f'Updated notes for {template_name}', icon='🤖')
                st.rerun()
        # Display notes if not in edit mode and notes exist
        elif notes:
            st.text(notes)


def edit_business_pane(business_st_key):
    old_business = st.session_state.get(business_st_key)
    with st.expander(f"Pick Business {business_st_key}"):
        index = businesses.index(old_business) if old_business in businesses else 0
        business = st.selectbox("Business",
                                businesses,
                                key=f"select-business-{business_st_key}",
                                format_func=lambda x: x['title'],
                                index=index)
        business['avatar'] = db.get_storage(AVATAR_URL_ST_KEY)
        if not old_business or business != old_business['title']:
            db.save_storage(business_st_key, business)

        logo = business['brand']['logo']
        st.image(logo, width=100)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.color_picker('Background', value=business['brand']['background_color'],
                            key=f'background_color-{business_st_key}', disabled=True)
        with col2:
            st.color_picker('Accent', value=business['brand']['color'],
                            key=f'accent_color-{business_st_key}', disabled=True)
        with col3:
            st.color_picker('Text', value=business['brand']['text_color'],
                            key=f'text_color-{business_st_key}', disabled=True)

        context = format_business_context(business)
        st.text(f"Business: {context}")

        facts = format_facts(business)
        st.text(f"Facts: {facts}")

        topic = business['topics'][0]['body']
        st.text(f"Topic: {topic}")


def sidebar():
    data = {x.name: x.model_dump(exclude='components') for x in canvases}
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
            db.save_storage(THEME_CHOICE_ST_KEY, theme)

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
            st.session_state['need_fetch_from_switchboard'] = True
            st.rerun()

        st.info("⬆️ Run whenever you add a component or change it's name")

        st.session_state[SELECTED_PROMPT_ST_KEY] = st.selectbox('Prompt',
                                                                options=[x['prompt'] for x in prompts],
                                                                index=0)

        edit_business_pane(BUSINESS1_ST_KEY)
        edit_business_pane(BUSINESS2_ST_KEY)

        avatar_url = st.text_input('Avatar URL', value=db.get_storage(AVATAR_URL_ST_KEY))
        if avatar_url:
            st.image(avatar_url, width=100)
        if avatar_url != db.get_storage(AVATAR_URL_ST_KEY):
            db.save_storage(AVATAR_URL_ST_KEY, avatar_url)

        with st.expander('Create Theme'):
            display_name = st.text_input('Name', key='theme_name')
            name = slugify(display_name)
            theme_canvases_chosen = st.multiselect('Canvases',
                                                   options=[x for x in canvases if x.theme is None],
                                                   format_func=lambda x: x.name)
            theme_carousels_chosen = st.multiselect('Carousels', options=carousels, format_func=lambda x: x['name'])

            if st.button('Create', disabled=not (display_name and (theme_canvases_chosen or theme_carousels_chosen))):
                with st.spinner("Wait for it..."):
                    for canvas in theme_canvases_chosen:
                        canvas.theme = name
                        db.save_canvas(canvas)
                    for carousel in theme_carousels_chosen:
                        carousel['theme_name'] = name
                        db.save_carousel(carousel)
                    db.save_theme({'id': str(uuid.uuid4()),
                                   'created_at': datetime.utcnow().isoformat(),
                                   'name': name,
                                   'display_name': display_name})
                st.success(f"Created theme '{display_name}'", icon='🤖')

        with st.expander('Create Carousel'):
            display_name = st.text_input('Name', key='carousel_name')
            name = slugify(display_name)
            theme = st.selectbox('Theme', options=[None] + [x['name'] for x in themes])
            carousel_canvases_chosen = st.multiselect('Graphics', options=[x.name for x in canvases])
            if st.button('Create', disabled=not (display_name and carousel_canvases_chosen), key='create_carousel'):
                with st.spinner("Wait for it..."):
                    db.save_carousel({'id': str(uuid.uuid4()),
                                     'created_at': datetime.utcnow().isoformat(),
                                     'display_name': display_name,
                                     'name': name,
                                     'canvas_names': carousel_canvases_chosen,
                                     'theme_name': theme,
                                     'approved': False,
                                     'notes': "",
                                     })
                st.success(f"Created carousel '{display_name}'", icon='🤖')

        global_notes = db.get_storage(GLOBAL_NOTES_ST_KEY)
        new_global_notes = st.text_area('Global Notes', value=global_notes, height=500)
        if new_global_notes != global_notes:
            db.save_storage(GLOBAL_NOTES_ST_KEY, new_global_notes)

    return df, image_size


def main_table(df, image_size):
    theme_names = [None] + [x['name'] for x in themes]
    load = 50
    if len(df) == 0:
        st.write('No templates found matching filters')
    for name in df.head(load).sort_index().index:
        cols = st.columns(4)
        canvas = canvas_map[name]
        with cols[0]:
            clickable_image(get_thumbnail(canvas.name), SB_TEMPLATE_EDITOR_URL_PREFIX + canvas.id, image_size=image_size)
        with cols[1]:
            if thumbnail_url := get_thumbnail(canvas.name, first=False):
                clickable_image(thumbnail_url, SB_TEMPLATE_EDITOR_URL_PREFIX + canvas.id, image_size=image_size)
            else:
                st.write("click refresh")
        with cols[2]:
            approval_status = st.checkbox('Approved', value=canvas.approved, key=f'approval_status-{canvas.name}')
            if bool(approval_status) != bool(canvas.approved): # ie status changed
                canvas.approved = approval_status
                db.save_canvas(canvas)
            standalone_status = st.checkbox('Standalone', value=canvas.standalone, key=f'standalone_status-{canvas.name}')
            if bool(standalone_status) != bool(canvas.standalone): # ie status changed
                canvas.standalone = standalone_status
                db.save_canvas(canvas)

            if canvas.theme not in theme_names:
                canvas.theme = None
                db.save_canvas(canvas)
            theme = st.selectbox('theme', options=theme_names, index=theme_names.index(canvas.theme), key=f'theme-{canvas.name}')
            if theme != canvas.theme:
                canvas.theme = theme
                db.save_canvas(canvas)
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
