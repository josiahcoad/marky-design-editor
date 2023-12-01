import json
import requests
import streamlit as st

from utils import db
import aiohttp
import asyncio
import random
import streamlit as st
from streamlit_image_select import image_select
from utils.business_formaters import format_business_context, format_topic, format_facts

from utils.db import list_businesses, list_canvases, list_prompts
from utils.prompt_gpt import prompt_gpt_json

DEV_URL = 'https://psuf5gocxc.execute-api.us-east-1.amazonaws.com/api'
DEV_API_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNTI1YzdmNC00ZTM5LTQ0N2ItODRlMy0xZWE5OWI3ZjA5MGYiLCJpYXQiOjE2OTUwOTQ0ODYsIm5iZiI6MTY5NTA5NDQ4NiwiZXhwIjoxNzI2NjMwNDg2fQ.G-e-NnDenhLs6HsM6ymLfQz_lTHTo8RX4oZB9I5hJI0' # admin@admin.com
SB_TEMPLATE_EDITOR_URL_PREFIX = "https://www.switchboard.ai/s/canvas/editor/"

st.set_page_config(layout='wide', page_title="Prompt", page_icon="")


@st.cache_data
def get_businesses():
    businesses = list_businesses()
    return {x['title']: x for x in businesses if x.get('testimonials')}


@st.cache_data
def get_prompts():
    prompts = list_prompts()
    return [x['prompt'] for x in prompts]


MASTER_PROMPT_KEY = 'master-prompt'
CAPTION_PROMPT_KEY = 'caption-prompt'

CAPTION_INSTRUCTIONS = (
    "I want you to create a caption to go along with the graphic. "
    "Start by with a hook to my audience. "
    "Then provide real value to them in the way of inspiration, information or entertainment. "
    "Finish with a call to action to engage with the post (eg share or comment if...) (and/or my company cta). "
    "Also add a hashtag or two that is relevant to the post. ")


MASTER_PROMPT = """You are a social media manager for a brand. Below is everything you need to know about it.

Business Context:
{context}

---------------
I am creating a post that will have a post format to follow broken into several sections, and a caption.
Use the business context for making the content.
Output your response in json format. ie a Dict[str, str].
It is very important that you do not exceed the max length for each section.
Write the section values in the {language} language.

Create me a post about {topic}. The purpose of this post is to be {intention}. My cta is to {cta}.

These are some facts that you can use if needed:
{knowledge}

---------------
I want the text to *carefully* follow the following post template (between the #~#~)
(fill in the bracketed text) (include the newlines that the template has):
#~#~
{post_template}
#~#~

Give your output in the following sections
{sections}

---------------
Remember, you must
1) follow the format of the post template
2) stay within character/word limits
3) provide your output in json as a Dict[str, str]
"""


master_prompt = st.session_state.get(MASTER_PROMPT_KEY) or db.get_storage(MASTER_PROMPT_KEY) or MASTER_PROMPT
new_master_prompt = st.text_area('Master Prompt', value=master_prompt, height=800)
if new_master_prompt != master_prompt:
    db.put_storage(MASTER_PROMPT_KEY, new_master_prompt)
    st.session_state[MASTER_PROMPT_KEY] = new_master_prompt


caption_prompt = st.session_state.get(CAPTION_PROMPT_KEY) or db.get_storage(CAPTION_PROMPT_KEY) or CAPTION_INSTRUCTIONS
new_caption_prompt = st.text_area('Caption Instructions', value=caption_prompt)
if new_caption_prompt != caption_prompt:
    db.put_storage(CAPTION_PROMPT_KEY, new_caption_prompt)
    st.session_state[CAPTION_PROMPT_KEY] = new_caption_prompt


language = "English"

businesses = get_businesses()
business_names = list(businesses.keys())
business_name = st.selectbox('Business', business_names)
facts = st.text_area('Facts', value=format_facts(businesses[business_name]))
context = st.text_area('Business Context', value=format_business_context(businesses[business_name]))
cta = st.selectbox('CTA', businesses[business_name].get('ctas') or ["Call", "Visit", "Buy"])

intention = st.selectbox('Intention', ['Inspire', 'Inform', 'Entertain', 'Sell'])

topic = st.selectbox('Topic', [format_topic(x) for x in businesses[business_name].get('chapters', [])])

post_template = st.selectbox('Post Template', get_prompts())

col1, col2 = st.columns([7, 3])
with col1:
    new_template = st.text_area('(Optional) Edit Template', value=post_template)

# with col2:
#     if st.button('Update'):
#         db.put_prompt(new_template)

#     if st.button('Add'):
#         db.put_prompt(new_template)

#     if st.button('Delete'):
#         db.put_prompt(new_template)


CANVAS_COMPONENTS_KEY = 'canvas-components'
default_components = [
    {'name': 'title', 'max_characters': 50, 'instructions': "{title of the post}"},
    {'name': 'content', 'max_characters': 150, 'instructions': "{body of the post}"},
    {'name': 'cta', 'max_characters': 20, 'instructions': "{Call to action}"},
]
caption_component = {'name': 'caption', 'max_characters': 500, 'instructions': new_caption_prompt}
# canvas_components = st.session_state.get(CANVAS_COMPONENTS_KEY, [])
# if st.button("Add canvas component"):
#     canvas_components.append({'title': '', 'instructions': ''})

def format_section(component):
    return (f"Section:\n"
            f"  json key: \"{component['name']}\"\n"
            f"  max words: {int(component['max_characters'] / 5)}\n"
            f"  section instructions: {component['instructions']}\n")


sections = '\n'.join(map(format_section, default_components + [caption_component]))


final_prompt = new_master_prompt.format(
    context=context,
    topic=topic,
    intention=intention,
    cta=cta,
    knowledge=facts,
    post_template=post_template,
    sections=sections,
    language=language
)
st.subheader("Filled in Prompt")
st.text(final_prompt)


import aiohttp
import asyncio


payload = {
    'components': default_components,
    'business_context': context,
    'topic': topic,
    'knowledge': facts,
    'prompt': post_template,
    'intention': intention,
    'cta': cta,
    'approximate_caption_length_chars': 500,
    'language': language,
    'caption_suffix': "",
}

if st.button('Run Prompt'):
    with st.spinner('Wait for it...'):
        response = prompt_gpt_json(final_prompt, creativity=0.9, model=4)
    st.text_area(json.dumps(response, indent=4, ensure_ascii=False), height=800, disabled=True)
