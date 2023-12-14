
import json
from typing import Dict, List
import requests
from utils import db

from utils.dto import Canvas, CanvasComponent
from utils.thumbnail import get_thumbnail, save_thumbnail


def update_canvases_with_switchboard(sb_token, sb_cookie):
    db_canvases = {x.name: x for x in db.list_canvases()}

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
    to_update: List[Canvas] = []
    for sb_template in sb_data:
        config = sb_template['configuration']
        if not config:
            continue
        canvas_name = config.pop('template')['name']
        db_canvas = db_canvases.get(canvas_name)
        db_components = {x.name: x.model_dump() for x in db_canvas.components} if db_canvas else {}
        sb_components = list(config.values())
        components = [CanvasComponent.combine_sb_db(c['name'], c, db_components.get(c['name'], {}))
                      for c in sb_components]
        if not db_canvas:
            db_canvas = Canvas(name=canvas_name, components=components)
            to_update.append(db_canvas)
        elif [x.model_dump() for x in components] != [x.model_dump() for x in db_canvas.components]:
            db_canvas.components = components
            to_update.append(db_canvas)

        if not get_thumbnail(canvas_name):
            print(f"Saving thumbnail for {canvas_name}")
            save_thumbnail(canvas_name, sb_template['thumbnailUrl'])

    assert len(to_update) < 35, f"Too many canvases to update ({len(to_update)}): {to_update}"
    db.save_all_canvases(to_update)
    return to_update
