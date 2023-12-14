from datetime import datetime
import json
import uuid
import streamlit as st

from utils import db
import streamlit as st
from streamlit_image_select import image_select
from utils.business_formaters import format_business_context, format_facts

from utils import db
from utils.dto import TextComponent
from utils.prompt_gpt import prompt_gpt_json

DEV_URL = 'https://psuf5gocxc.execute-api.us-east-1.amazonaws.com/api'
DEV_API_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNTI1YzdmNC00ZTM5LTQ0N2ItODRlMy0xZWE5OWI3ZjA5MGYiLCJpYXQiOjE2OTUwOTQ0ODYsIm5iZiI6MTY5NTA5NDQ4NiwiZXhwIjoxNzI2NjMwNDg2fQ.G-e-NnDenhLs6HsM6ymLfQz_lTHTo8RX4oZB9I5hJI0' # admin@admin.com
SB_TEMPLATE_EDITOR_URL_PREFIX = "https://www.switchboard.ai/s/canvas/editor/"

st.set_page_config(layout='wide', page_title="Prompt", page_icon="✏️")

prompts = db.list_prompts()
businesses = db.list_users_joined_businesses(only_full_businesses=True)


MASTER_PROMPT_KEY = 'master-prompt'
CAPTION_PROMPT_KEY = 'caption-prompt'
CHOSEN_PROMPT_ST_KEY = 'chosen-prompt'

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


master_prompt = db.get_storage(MASTER_PROMPT_KEY) or MASTER_PROMPT
with st.expander("Master Prompt"):
    new_master_prompt = st.text_area('', value=master_prompt, height=800, label_visibility='collapsed')
    if new_master_prompt != master_prompt:
        db.save_storage(MASTER_PROMPT_KEY, new_master_prompt)


caption_prompt = db.get_storage(CAPTION_PROMPT_KEY) or CAPTION_INSTRUCTIONS
new_caption_prompt = st.text_area('Caption Instructions', value=caption_prompt)
if new_caption_prompt != caption_prompt:
    db.save_storage(CAPTION_PROMPT_KEY, new_caption_prompt)


language = "English"

with st.expander("Select Test Business"):
    business = st.selectbox('Business', list(businesses), format_func=lambda x: x['title'])
    if business:
        facts = st.text_area('Facts', value=format_facts(business))
        context = st.text_area('Business Context', value=format_business_context(business))
        cta = st.selectbox('CTA', business['ctas'])
        intention = st.selectbox('Intention', ['Inspire', 'Inform', 'Entertain', 'Sell'])
        topic = st.selectbox('Topic', [x['body'] for x in business['topics']])


with st.sidebar:
    counts = {
        'Approved': len([prompt for prompt in prompts if prompt.get('approved', False)]),
        'Unapproved': len([prompt for prompt in prompts if not prompt.get('approved', False)]),
        'All': len(prompts),
    }
    approval_filter = st.selectbox('Filter by Approval', ['All', 'Approved', 'Unapproved'], format_func=lambda x: f"{x} ({counts[x]})")
    text_filter = st.text_input('Search', key='text_filter')
    for prompt in prompts:
        if approval_filter == 'Approved' and not prompt.get('approved', False):
            continue
        if approval_filter == 'Unapproved' and prompt.get('approved', False):
            continue
        if text_filter and text_filter.lower() not in prompt['prompt'].lower():
            continue
        st.text(prompt['prompt'])
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if prompt.get('approved', False):
                if st.button("❌ Unapprove", key=f'{prompt["id"]}_unapprove'):
                    prompt['approved'] = False
                    db.save_prompt(prompt)
            else:
                if st.button("✅ Approve", key=f'{prompt["id"]}_approve'):
                    prompt['approved'] = True
                    db.save_prompt(prompt)
        with col2:
            if st.button("🗑️ Delete", key=f'{prompt["id"]}_delete'):
                db.delete_prompt(prompt)
        with col3:
            if st.button("Try It ➡️", key=prompt["id"]):
                db.save_storage(CHOSEN_PROMPT_ST_KEY, prompt)
        st.markdown('---')

chosen_prompt = db.get_storage(CHOSEN_PROMPT_ST_KEY) or prompts[0]

col1, col2 = st.columns([7, 3])
with col1:
    edited_prompt = st.text_area('Post Prompt', value=chosen_prompt['prompt'], height=200)
    if edited_prompt != chosen_prompt['prompt']:
        chosen_prompt['prompt'] = edited_prompt
        db.save_prompt(chosen_prompt)
        st.rerun()

with col2:
    if st.button('Save As New Prompt'):
        new_prompt_obj = {'id': str(uuid.uuid4()), 'created_at': datetime.now().isoformat(), 'prompt': edited_prompt}
        db.save_prompt(new_prompt_obj)
    if st.button('Delete'):
        db.delete_prompt(chosen_prompt)


components = st.session_state.get('text_components') or [
    TextComponent(name='title', max_characters=50, instructions="{post-template starts here}"),
    TextComponent(name='content', max_characters=150, instructions="{post-template continues here}"),
    TextComponent(name='cta', max_characters=20, instructions="{Call to action}"),
]

with st.expander('Text Components'):
    for component in components:
        cols = st.columns(4)
        with cols[0]:
            st.text(component.name)
        with cols[1]:
            component.max_characters = st.number_input('max characters',
                                                value=component.max_characters,
                                                key=f'{component.name}_char_count',
                                                step=10)
        with cols[2]:
            component.instructions = st.text_input('custom instructions',
                                                        value=component.instructions,
                                                        key=f'{component.name}_instructions')
        with cols[3]:
            if st.button('Delete', key=f'{component.name}_delete'):
                components.remove(component)
                st.session_state['text_components'] = components

    if st.button('Add Component'):
        components.append(TextComponent(name=f'new_component-{len(components)}', max_characters=50, instructions=""))
        st.session_state['text_components'] = components

    st.session_state['text_components'] = components

cols = st.columns(2)
with cols[0]:
    caption_length = st.slider('Caption Length', min_value=0, max_value=1000, value=500, step=50)
caption_component = TextComponent(name='caption', max_characters=caption_length, instructions=new_caption_prompt)

def format_section(component: TextComponent):
    return (f"Section:\n"
            f"  json key: \"{component.name}\"\n"
            f"  max words: {int(component.max_characters / 5)}\n"
            f"  section instructions: {component.instructions}\n")


sections = '\n'.join(map(format_section, st.session_state['text_components'] + [caption_component]))


final_prompt = new_master_prompt.format(
    context=context,
    topic=topic,
    intention=intention,
    cta=cta,
    knowledge=facts,
    post_template=edited_prompt,
    sections=sections,
    language=language
)
with st.expander("Filled in Prompt"):
    st.text(final_prompt)


payload = {
    'components': st.session_state['text_components'],
    'business_context': context,
    'topic': topic,
    'knowledge': facts,
    'prompt': edited_prompt,
    'intention': intention,
    'cta': cta,
    'approximate_caption_length_chars': 500,
    'language': language,
    'caption_suffix': "",
}

if st.button('Run Prompt'):
    st.text(f"Request Price: {(len(final_prompt.split())*1.3) / 1000:.1f} cents")
    with st.spinner('Wait for it...'):
        response = prompt_gpt_json(final_prompt, creativity=0.9, model=4)
    st.text(f"Response Price: {((len(json.dumps(response).split())*1.3) / 1000)*3:.1f} cents")
    sections = [f'__{key}__\n{value}' for key, value in response.items()]
    st.text_area("Response", '\n\n'.join(sections), height=800)
