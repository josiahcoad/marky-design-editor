import random
import time
import requests
import streamlit as st

import asyncio
from typing import Dict, List

import aiohttp
from utils.business_formaters import format_business_context, format_facts

from utils.dto import Canvas

DEV_URL = 'https://psuf5gocxc.execute-api.us-east-1.amazonaws.com/api'
DEV_API_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNTI1YzdmNC00ZTM5LTQ0N2ItODRlMy0xZWE5OWI3ZjA5MGYiLCJpYXQiOjE2OTUwOTQ0ODYsIm5iZiI6MTY5NTA5NDQ4NiwiZXhwIjoxNzI2NjMwNDg2fQ.G-e-NnDenhLs6HsM6ymLfQz_lTHTo8RX4oZB9I5hJI0' # admin@admin.com


TEXT_CONTENT = {
    'title': "I wish I knew this when I started! It would have saved me a lot of time and money.",
    'content': "Start with the minimum viable product. Don't try to build the perfect product from the start. If you do, you'll waste a lot of time and money.",
    'cta': "Get started today! It's free to sign up and you can cancel anytime.",
    'content1': "Start with the minimum viable product. Don't try to build the perfect product from the start. If you do, you'll waste a lot of time and money.",
    'content2': "Start with the minimum viable product. Don't try to build the perfect product from the start. If you do, you'll waste a lot of time and money.",
}


BACKGROUND_URLS = [
    "https://images.unsplash.com/photo-1694459471238-6e55eb657848?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwyfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
    "https://images.unsplash.com/photo-1695331453337-d5f95078f78e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwxfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
    "https://images.unsplash.com/photo-1694472655814-71e6c5a7ade8?crop=entropy&cs=srgb&fm=jpg&ixid=M3w0MTMwMDZ8MHwxfHNlYXJjaHwzfHxqYWNrZWR8ZW58MHx8fHwxNjk5MDM4ODM0fDA&ixlib=rb-4.0.3&q=85",
]

IPSEM_TEXT = "This Python package runs a Markov chain algorithm over the surviving works of the Roman historian Tacitus to generate naturalistic-looking pseudo-Latin gibberish. Useful when you need to generate dummy text as a placeholder in templates, etc. Brigantes femina duce exurere coloniam, expugnare castra, ac nisi felicitas in tali"

SELECTED_PROMPT_ST_KEY = 'selected_prompt'


def fill_canvases(canvases, businesses, use_dummy_data=False):
    image_urls = asyncio.run(fill_canvases_async(canvases, businesses, use_dummy_data))
    return image_urls


async def fill_canvases_async(canvases: List[Canvas], businesses: List[Dict[str, str]], use_dummy_data=False):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for canvas, business in zip(canvases, businesses, strict=True):
            if use_dummy_data:
                payload = fill_canvas_prepare_payload(canvas, business)
                task = asyncio.ensure_future(fill_canvas_make_request_async(session, payload))
            else:
                payload = generate_post_prepare_payload(canvas, business)
                task = asyncio.ensure_future(generate_post_make_request_async(session, payload))
            tasks.append(task)
        image_urls = await asyncio.gather(*tasks)
    return image_urls


async def generate_post_make_request_async(session, payload):
    async with session.post(f"{DEV_URL}/v1/posts/controlled",
                            json=payload,
                            headers={'Authorization': f'Bearer {DEV_API_TOKEN}'}) as response:
        media_urls = (await response.json())['media_urls']
        image_url = list(media_urls.values())[0]
        return image_url


def generate_post_prepare_payload(canvas: Canvas, business):
    payload = {
        # template settings
        'canvas_names': [canvas.name],
        # content settings
        'business_context': format_business_context(business),
        'topic': business['topics'][0]['body'],
        'knowledge': format_facts(business),
        'prompt': st.session_state.get(SELECTED_PROMPT_ST_KEY, "Don't do this!\n{thing audience shouldn't do}"),
        'intention': "inform",
        'cta': business['ctas'][0] if business['ctas'] else "Buy now!",
        'approximate_caption_length_chars': 300,
        'language': "English",
        'caption_suffix': "#CustomHashtag",
        # brand_settings
        'brand_color_hex': business['brand']['color'],
        'background_color_hex': business['brand']['background_color'],
        'text_color_hex': business['brand']['text_color'],
        'logo_url': business['brand']['logo'],
        'avatar_url': business['brand'].get('avatar'),
        'font_url': None
    }
    print('payload', payload)
    return payload



async def fill_canvas_make_request_async(session, payload):
    async with session.post(DEV_URL + '/v1/posts/fill-canvas',
                            json=payload,
                            headers={'Authorization': f'Bearer {DEV_API_TOKEN}'}) as response:
        return (await response.json())['image_url']


def fill_canvas_prepare_payload(canvas: Canvas, business: Dict[str, str]):
    text_content = {x.name: get_filler_text(TEXT_CONTENT.get(x.name), x.max_characters)
                    for x in canvas.text_components}
    fill_values = {
        'logo_url': business['brand']['logo'],
        'avatar_url': business['brand'].get('avatar'),
        'background_image_url': random.choice(BACKGROUND_URLS),
        'background_color': business['brand']['background_color'],
        'accent_color': business['brand']['color'],
        'text_color': business['brand']['text_color'],
    }
    payload = {
        'canvas_name': canvas.name,
        **fill_values,
        'text_content': text_content,
    }
    print('payload', payload)
    return payload


def get_filler_text(value, max_characters):
    if value is None:
        return IPSEM_TEXT[:max_characters]
    value = value[:max_characters]
    if len(value) < max_characters:
        value += IPSEM_TEXT[:max_characters - len(value)]
    return value


def init_create_carousel_post(
        canvas_names,
        business_context,
        topic,
        knowledge,
        prompt,
        intention,
        cta,
        approximate_caption_length_chars,
        language,
        caption_suffix,
        brand_color_hex,
        background_color_hex,
        text_color_hex,
        logo_url,
        avatar_url,
    ):
    response = requests.post(f"{DEV_URL}/v1/posts/async",
                                json={
                                    # template settings
                                    'canvas_names': canvas_names,
                                    # content settings
                                    'business_context': business_context,
                                    'topic': topic,
                                    'knowledge': knowledge,
                                    'prompt': prompt,
                                    'intention': intention,
                                    'cta': cta,
                                    'approximate_caption_length_chars': approximate_caption_length_chars,
                                    'language': language,
                                    'caption_suffix': caption_suffix,
                                    # brand_settings
                                    'brand_color_hex': brand_color_hex,
                                    'background_color_hex': background_color_hex,
                                    'text_color_hex': text_color_hex,
                                    'logo_url': logo_url,
                                    'avatar_url': avatar_url
                                },
                                headers={'Authorization': f'Bearer {DEV_API_TOKEN}'})
    assert response.ok, response.text
    post_id = response.json()['id']
    return post_id


def get_post(post_id):
    response = requests.get(f"{DEV_URL}/v1/posts/{post_id}",
                            headers={'Authorization': f'Bearer {DEV_API_TOKEN}'})
    assert response.ok, response.text
    rjson = response.json()
    assert rjson['posts'] and len(rjson['posts']) == 1, rjson
    post = list(rjson['posts'].values())[0]
    assert post['status'] != 'FAILED', post['failed_reason']
    if post['status'] != 'LOADING':
        return post
    return None
