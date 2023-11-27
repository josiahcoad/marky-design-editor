import streamlit as st
from canvas_editor import main as canvas_editor
from prompt_editor import main as prompt_editor

st.set_page_config(layout='wide')


canvas_tab, prompt_tab = st.tabs(["Canvas", "Prompt"])

with canvas_tab:
    canvas_editor()

with prompt_tab:
    prompt_editor()