import streamlit as st
st.write("This is the prompt editor")

def generate_post(business_context, knowledge, language, canvas_name, prompt, topic, cta, intention, caption_length, color_pallete):
    return image_url, caption, canvas_components

def permutate(business_context, knowledge, language, canvases, prompts, topics, ctas, intentions, caption_lengths, color_palletes):
    for canvas in canvases:
        for prompt in prompts:
            for topic in topics:
                for cta in ctas:
                    for intention in intentions:
                        for caption_length in caption_lengths:
                            for color_pallete in color_palletes:
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


def pallete_picker(init_background, init_accent, init_text):
    col1, col2, col3 = st.columns(3)
    with col1:
        background = st.color_picker("Background", init_background)
    with col2:
        accent = st.color_picker("Accent", init_accent)
    with col3:
        text = st.color_picker("Text", init_text)
    return background, accent, text

def pallete_generator():
    pallets = {
        'pallete1': pallete_picker("#000000", "#ffffff", "#ffffff"),
        'pallete2': pallete_picker("#ffffff", "#000000", "#000000"),
        'pallete3': pallete_picker("#ffffff", "#000000", "#ffffff"),
    }
    return pallets


business_context = st.text_input("Business Context")
knowledge = st.text_input("Knowledge")
language = st.selectbox("Language", ["English", "Spanish"])
canvases = st.multiselect("Canvas", canvas_table().list())
prompts = st.multiselect("Prompt", prompt_table().list())
topics = st.multiselect("Topic", topics)
ctas = st.multiselect("CTA", business.ctas())
intentions = st.multiselect("Intention", ["Sell", "Inform", "Entertain"])
caption_length_min = st.slider("Caption Length Min", 100, 1000, 200, 100)
caption_length_max = st.slider("Caption Length Max", 100, 1000, 500, 100)
pallets = pallete_generator()
pallete_names = pallets.keys()
selected_pallete_names = st.multiselect("Color Pallete", pallete_names)
selected_pallets = [pallets[name] for name in selected_pallete_names]

if st.button("Generate"):
    batch = 10
    for i, post in enumerate(permutate(business_context, knowledge, language, canvases, prompts, topics, ctas, intentions, range(caption_length_min, caption_length_max), selected_pallets)):
        cols = st.columns(8)
        with cols[0]:
            st.write(post["caption_length"])
        with cols[1]:
            st.write(post["intention"])
        with cols[2]:
            st.write(post["canvas"])
        with cols[3]:
            st.write(post["prompt"])
        with cols[4]:
            st.write(post["topic"])
        with cols[5]:
            st.write(post["cta"])
        with cols[6]:
            st.write(post["caption"])
        with cols[7]:
            st.image(post["image_url"])

        if i >= batch:
            break
