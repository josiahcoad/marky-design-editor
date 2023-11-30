import random
import requests
import streamlit as st

from utils.db import list_businesses, list_canvases, list_prompts

DEV_URL = 'https://psuf5gocxc.execute-api.us-east-1.amazonaws.com/api'
DEV_API_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNTI1YzdmNC00ZTM5LTQ0N2ItODRlMy0xZWE5OWI3ZjA5MGYiLCJpYXQiOjE2OTUwOTQ0ODYsIm5iZiI6MTY5NTA5NDQ4NiwiZXhwIjoxNzI2NjMwNDg2fQ.G-e-NnDenhLs6HsM6ymLfQz_lTHTo8RX4oZB9I5hJI0' # admin@admin.com
SB_TEMPLATE_EDITOR_URL_PREFIX = "https://www.switchboard.ai/s/canvas/editor/"

st.set_page_config(layout='wide', page_title="Demo", page_icon="🤖")


@st.cache_data
def get_businesses():
    businesses = list_businesses()
    return {x['title']: x for x in businesses}


@st.cache_data
def get_canvases():
    canvases = list_canvases()
    return {x.name: x for x in canvases}


@st.cache_data
def get_prompts():
    prompts = list_prompts()
    return [x['prompt'] for x in prompts]


def clickable_image(image_url, target_url, image_size=100):
    markdown = f'<a href="{target_url}" target="_blank"><img src="{image_url}" width="{image_size}" height="{image_size}"></a>'
    st.markdown(markdown, unsafe_allow_html=True)
    st.image(image_url, width=image_size)


def generate_post(business_context, knowledge, language, canvas_name, prompt, topic, cta, intention, caption_length, color_pallete):
    payload = {
        # template settings
        'canvas_names': [canvas_name],
        # content settings
        'business_context': business_context,
        'topic': topic,
        'knowledge': knowledge,
        'prompt': prompt,
        'intention': intention,
        'cta': cta,
        'approximate_caption_length_chars': caption_length,
        'language': language,
        'caption_suffix': "",
        # brand_settings
        'brand_color_hex': color_pallete['brand'],
        'background_color_hex': color_pallete['background'],
        'text_color_hex': color_pallete['text'],
        'logo_url': None,
        'font_url': None
    }
    response = requests.post(f"{DEV_URL}/v1/posts/controlled",
                             json=payload,
                             headers={'Authorization': f'Bearer {DEV_API_TOKEN}'},
                             ).json()
    print(response)
    media_urls, caption, components = response['media_urls'], response['caption'], response['components']
    image_url = list(media_urls.values())[0]
    return image_url, caption, components




def permutate(business_context, knowledge, language, canvases, prompts, topics, ctas, intentions, caption_length_min, caption_length_max, color_palletes):
    for canvas in canvases:
        for prompt in prompts:
            for topic in topics:
                for cta in ctas:
                    for intention in intentions:
                        for color_pallete in color_palletes:
                            caption_length = random.randint(caption_length_min, caption_length_max)
                            with st.spinner("Generating..."):
                                image_url, caption, canvas_components = generate_post(business_context, knowledge, language, canvas, prompt, topic, cta, intention, caption_length, color_pallete)
                            yield {
                                "canvas": canvas,
                                "prompt": prompt,
                                "topic": topic,
                                "cta": cta,
                                "intention": intention,
                                "caption_length": caption_length,
                                "color_pallete": color_pallete,
                                "image_url": image_url,
                                "caption": caption,
                                "canvas_components": canvas_components,
                            }

def pallete_picker(pallete_name, init_background, init_accent, init_text):
    st.subheader(pallete_name)
    col1, col2, col3 = st.columns(3)
    with col1:
        background = st.color_picker("Background", init_background, key=f"{pallete_name}-background")
    with col2:
        accent = st.color_picker("Accent", init_accent, key=f"{pallete_name}-accent")
    with col3:
        text = st.color_picker("Text", init_text, key=f"{pallete_name}-text")
    return {'background': background, 'brand': accent, 'text': text}


def pallete_generator():
    pallets = {
        'Pallete 1': pallete_picker("Pallete 1", "#000000", "#ffffff", "#ffffff"),
        'Pallete 2': pallete_picker("Pallete 2", "#ffffff", "#000000", "#000000"),
        'Pallete 3': pallete_picker("Pallete 3", "#ffffff", "#000000", "#ffffff"),
    }
    return pallets


def format_business_context(business: dict):
    context = ""
    if title := business.get('title'):
        context += f"- Business: {title}\n"
    if industry := business.get('industry'):
        context += f"- Industry: {industry}\n"
    if niche := business.get('niche'):
        context += f"- Niche: {niche}\n"
    if tone := business.get('tone'):
        context += f"- Tone: {tone}\n"
    if core_values := business.get('core_values'):
        context += f"- Core values: {core_values}\n"
    if audience := business.get('audience'):
        context += f"- Customers: {audience}\n"
    if pain_points := business.get('pain_points'):
        context += f"- Customers pain points: {pain_points}\n"
    if objectives := business.get('objectives'):
        context += f"- Customers objectives: {objectives}\n"

    return context

def format_knowledge(business: dict):
    knowledge = ""
    if testimonials := business.get('testimonials'):
        knowledge += f"- testimonials: {random.choice(testimonials)}\n"
    if events := business.get('events'):
        knowledge += f"- events: {random.choice(events)}\n"
    if contact_phone := business.get('contact_phone'):
        knowledge += f"- contact phone: {contact_phone}\n"
    if contact_email := business.get('contact_email'):
        knowledge += f"- contact email: {contact_email}\n"
    if website := business.get('website'):
        knowledge += f"- website: {website}\n"

    return knowledge


def format_topic(content_topic: dict):
    return f"{content_topic.get('title')} -- {content_topic.get('summary')}"

businesses = get_businesses()
canvases = get_canvases()
prompts = get_prompts()

business = st.selectbox("Business", businesses.keys())
topic_entered = st.text_input(f"Welcome {business}, what do you want to post about today?")
topic_chosen = st.selectbox(label="Or choose one of the AI generated topics",
                            options=[""] + [format_topic(x) for x in businesses[business].get('chapters', [])])
topic = topic_entered or topic_chosen
topics = [topic]


with st.expander("⚙️ Generation Settings"):
    business_context = st.text_area("Business Context", value=format_business_context(businesses[business]))
    knowledge = st.text_area("Knowledge", value=format_knowledge(businesses[business]))
    language = st.selectbox("Language", ["English", "Spanish"], index=0)
    canvas_names = st.multiselect("Canvas", canvases.keys(), default=random.choice(list(canvases.keys())))
    # img = image_select("Label", ["image1.png", "image2.png", "image3.png"])
    prompts = st.multiselect("Template", prompts, default=random.choice(prompts))
    cta_options = businesses[business].get('ctas') or ["Call", "Visit", "Buy"]
    ctas = st.multiselect("CTA", cta_options, default=random.choice(cta_options))
    intentions = st.multiselect("Post Intention", ["Sell", "Inform", "Entertain"], default="Entertain")
    caption_length_min = st.slider("Caption Length Min", 100, 1000, 200, 100)
    caption_length_max = st.slider("Caption Length Max", 100, 1000, 500, 100)
    pallets = pallete_generator()
    pallete_names = list(pallets.keys())
    selected_pallete_names = st.multiselect("Color Pallete", pallete_names, default=pallete_names[0])
    selected_pallets = [pallets[name] for name in selected_pallete_names]


generate_enabled = all([business_context, language, canvas_names, prompts, topics, ctas, intentions, selected_pallets])
if st.button("Generate", disabled=not generate_enabled):
    batch = 10
    for i, post in enumerate(permutate(business_context, knowledge, language, canvas_names, prompts, topics, ctas, intentions, caption_length_min, caption_length_max, selected_pallets)):
        cols = st.columns([4, 6])
        with cols[0]:
            clickable_image(post['image_url'], SB_TEMPLATE_EDITOR_URL_PREFIX + canvases[post['canvas']]['id'])
            st.write(post['caption'])
        with cols[1]:
            st.write("caption_length: ", post['caption_length'])
            st.write("intention: ", post['intention'])
            st.write("canvas: ", post['canvas'])
            st.write("cta: ", post['cta'])
            st.write("topic: ", post['topic'])
            st.write("prompt: ", post['prompt'])

        if i >= batch:
            break
