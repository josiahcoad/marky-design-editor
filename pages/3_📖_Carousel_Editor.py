from copy import deepcopy
import time
import streamlit as st
from utils import db, marky
from utils.business_formaters import format_business_context, format_facts
from utils.dto import Canvas
from utils.thumbnail import save_thumbnail, get_thumbnail

st.set_page_config(layout='wide', page_title="Prompt", page_icon="📖")

AVATAR_URL_ST_KEY = 'avatar_url'

carousels = db.list_carousels()
canvases = db.list_canvases()
themes = db.list_themes()
prompts = db.list_prompts()
businesses = db.list_users_joined_businesses(only_full_businesses=True)

st.session_state['loading_post_start_time'] = st.session_state.get('loading_post_start_time')
st.session_state['lambda_is_cold'] = st.session_state.get('lambda_is_cold', True)

with st.sidebar:
    carousel_selected = st.selectbox("Carousel",
                                     carousels,
                                     format_func=lambda x: x['display_name'],
                                     index=0)
    if not carousel_selected:
        st.error("No carousel made. Please make one first in the canvas editor.")
        st.stop()
    if carousel_selected:
        theme_options = [None] + [x['name'] for x in themes]
        theme = st.selectbox("Theme",
                             theme_options,
                             index=theme_options.index(carousel_selected['theme_name']))

        if theme != carousel_selected['theme_name']:
            carousel_selected['theme_name'] = theme
            db.save_carousel(carousel_selected)

        approved = st.checkbox("Approved", carousel_selected.get('approved', False))
        if approved != carousel_selected.get('approved', False):
            carousel_selected['approved'] = approved
            db.save_carousel(carousel_selected)

        display_name = st.text_input("Display Name", carousel_selected['display_name'])
        if display_name != carousel_selected['display_name']:
            carousel_selected['display_name'] = display_name
            db.save_carousel(carousel_selected)

        notes = st.text_area("Notes", carousel_selected.get('notes'))
        if notes != carousel_selected.get('notes'):
            carousel_selected['notes'] = notes
            db.save_carousel(carousel_selected)

        st.markdown("---")
        with st.expander("Choose Business"):
            business = st.selectbox("Business",
                                    businesses,
                                    format_func=lambda x: x['title'])
            if business:
                if logo_url := business['brand']['logo']:
                    st.image(logo_url, "Logo", 100)
                else:
                    st.write("No logo")

                if avatar_url := db.get_storage(AVATAR_URL_ST_KEY):
                    st.image(avatar_url, "Avatar", 100)
                else:
                    st.write("No avatar")

                topic = st.selectbox("Topic",  [x['body'] for x in business['topics']])
                cta = st.selectbox("CTA", business['ctas'])

                cols = st.columns(3)
                cols[0].color_picker("Brand Color", value=business['brand']['color'], disabled=True)
                cols[1].color_picker("Background Color", value=business['brand']['background_color'], disabled=True)
                cols[2].color_picker("Text Color", value=business['brand']['text_color'], disabled=True)

        prompt = st.selectbox("Prompt", prompts, format_func=lambda x: x['prompt'])
        new_prompt = st.text_area("Prompt", prompt['prompt'], label_visibility='collapsed')
        if new_prompt != prompt:
            prompt['prompt'] = new_prompt
            db.save_prompt(prompt)
            st.toast("Saved Prompt!")

        if st.button("Try It!"):
            with st.spinner("Loading..."):
                post_id = marky.init_create_carousel_post(
                    canvas_names=carousel_selected['canvas_names'],
                    business_context=format_business_context(business),
                    topic=topic,
                    knowledge=format_facts(business),
                    prompt=prompt['prompt'],
                    intention="informational",
                    cta=cta,
                    approximate_caption_length_chars=100,
                    language="English",
                    caption_suffix="",
                    brand_color_hex=business['brand']['color'],
                    background_color_hex=business['brand']['background_color'],
                    text_color_hex=business['brand']['text_color'],
                    logo_url=logo_url,
                    avatar_url=avatar_url
                )
                st.session_state['post_id'] = post_id
                st.session_state['loading_post_start_time'] = time.time()

cols = st.columns([4, 1])
timer = cols[0].empty()
loader = cols[1].empty()
estimated_time = 30 + (30 if st.session_state['lambda_is_cold'] else 0)
post_id = ''
while (start_time := st.session_state['loading_post_start_time']):
    time_waiting = time.time() - start_time
    timer.text(f"Loading (takes 30-60 seconds)... {time_waiting:.1f} seconds")
    loader.progress(min(time_waiting / estimated_time, 1.0))
    time.sleep(.1)
    if int(time_waiting) % 3 == 0:
        post = marky.get_post(st.session_state['post_id'])
        if post:
            st.session_state['loading_post_start_time'] = None
            st.markdown("**Caption: **" + post['caption'])
            for x in post['media']:
                save_thumbnail(x['canvas_name'], x['url'])
            st.session_state['lambda_is_cold'] = False
            post_id = post['id']

ncols = len(carousel_selected['canvas_names'])
cols = st.columns(ncols)
for i, canvas_name in enumerate(carousel_selected['canvas_names']):
    with cols[i]:
        st.image(get_thumbnail(canvas_name) + f"?pid={post_id}", caption=canvas_name, use_column_width=True)
        if st.button("🗑️", key=f'delete-{canvas_name}'):
            carousel_selected['canvas_names'].remove(canvas_name)
            db.save_carousel(carousel_selected)
            st.rerun()


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
        db.save_canvas(new_canvas)

canvas_map = {x.name: x for x in canvases}
for canvas_name in carousel_selected['canvas_names']:
    with st.expander(canvas_name):
        display_text_containers(canvas_map[canvas_name])

