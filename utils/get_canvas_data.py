
import json
from typing import Dict
import requests
from utils import db

from utils.dto import Canvas, CanvasComponent, TextComponent
from utils.s3utils import list_s3_objects

def get_canvas_data(sb_token, sb_cookie):
    # get s3 data
    my_thumbnails = list_s3_objects()

    db_canvases = db.list_canvases()
    db_data = {x.name: x for x in db_canvases}

    # get switchboard data
    headers = {
        'authority': 'www.switchboard.ai',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': f"Bearer {sb_token}",
        'Cookie': sb_cookie,
    }

    response = requests.get('https://www.switchboard.ai/api/canvas/templates', headers=headers, timeout=10)
    response.raise_for_status()
    sb_data = response.json()
    canvases: Dict[str, Canvas] = {}
    for sb_template in sb_data:
        config = sb_template['configuration']
        if not config:
            continue
        name = config.pop('template')['name']
        sb_components = list(config.values())
        thumbnail_url = my_thumbnails.get(sb_template['apiName'], sb_template['thumbnailUrl'])
        if sb_template['apiName'] == 'tech-template-1':
            print(thumbnail_url)

        db_canvas: dict = db_data[name].model_dump() if name in db_data else {}
        theme = db_canvas.get('theme', None)
        notes = db_canvas.get('notes', '')
        approved = db_canvas.get('approved', False)
        db_components = {x['name']: x for x in db_canvas.get('components', {})}
        id = sb_template['id']

        components = [CanvasComponent.combine_sb_db(c['name'], c, db_components.get(c['name'], {}))
                      for c in sb_components]

        canvas = Canvas(id=id,
                        name=name,
                        components=components,
                        thumbnail_url=thumbnail_url,
                        theme=theme,
                        notes=notes,
                        approved=approved)

        canvases[canvas.name] = canvas

    return canvases
