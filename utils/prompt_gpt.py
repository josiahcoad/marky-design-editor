import json
import re
from typing import Literal
import warnings

import requests

OPENAI_COMPLETIONS_API_URL = 'https://api.openai.com/v1/chat/completions'
OPENAI_KEY = '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'


def prompt_gpt_json(prompt, creativity=0.5, model: Literal[3, 4] = 4):
    response = prompt_gpt(prompt, creativity=creativity, model=model, json_output=True)
    return json.loads(response)


def prompt_gpt(prompt, creativity=0.5, model: Literal[3, 4] = 4, json_output: bool = False) -> str:
    messages = [{"role": "user", "content": prompt}]
    if json_output:
        messages.insert(0, {"role": "system", "content": "Answer in json format"})

    payload = {
        "model": "gpt-3.5-turbo-1106" if model == 3 else "gpt-4-1106-preview",
        "messages": messages,
        "temperature": creativity
    }

    if json_output:
        payload['response_format'] = {'type': 'json_object'}

    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        response = requests.post(OPENAI_COMPLETIONS_API_URL, headers=headers, json=payload, verify=False)

    response_json = response.json()
    completion = response_json['choices'][0]['message']['content']

    completion = remove_characters_suffix(completion)  # weird bug where some strings end in (X characters)
    return completion


def remove_characters_suffix(s):
    return re.sub(r'\(\d+ characters\)$', '', s).strip()
