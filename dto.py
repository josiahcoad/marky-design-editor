
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, model_validator


class ColorType(str, Enum):
    DONT_CHANGE = 'DONT_CHANGE'
    ON_BACKGROUND = 'ON_BACKGROUND'
    ON_ACCENT = 'ON_ACCENT'
    ACCENT = 'ACCENT'


class ComponentType(str, Enum):
    TEXT = 'TEXT'
    IMAGE = 'IMAGE'
    SHAPE = 'SHAPE'


class TextMeta(BaseModel):
    max_characters: int
    all_caps: bool = False
    text_color_type: str = ColorType.DONT_CHANGE
    optional: bool = False


class CanvasComponent(BaseModel):
    type: ComponentType
    key: str

    def is_image_named(self, name, prefix=False):
        return self.type == ComponentType.IMAGE and (self.key == name if not prefix else self.key.startswith(name))

    def is_shape_named(self, name, prefix=False):
        return self.type == ComponentType.SHAPE and (self.key == name if not prefix else self.key.startswith(name))

    def is_background_colored(self):
        return (self.is_shape_named('object1')
                or self.is_image_named('colored-layer-background')
                or self.is_image_named('bc-', prefix=True)
                or self.is_shape_named('bc-', prefix=True))

    def is_accent_colored(self):
        return (self.is_image_named('colored-layer')
                or self.is_image_named('ac-', prefix=True)
                or self.is_shape_named('ac-', prefix=True))


class TextComponent(CanvasComponent, TextMeta):
    type: Literal['TEXT'] = ComponentType.TEXT


class FilledTextComponent(TextComponent):
    content: str
    color: str = None
    font: str = None


class ImageComponent(BaseModel):
    type: Literal['IMAGE'] = ComponentType.IMAGE
    remove_background: bool = False


class FilledImageComponent(ImageComponent):
    url: str
    color: str = None


class ShapeComponent(BaseModel):
    type: Literal['SHAPE'] = ComponentType.SHAPE


class FilledShapeComponent(ShapeComponent):
    color: str


class Canvas(BaseModel):
    name: str
    components: List[TextComponent | ImageComponent | ShapeComponent]

    def get_image_named(self, name):
        return next((x for x in self.components if x.is_image_named(name)), None)

    @property
    def logo(self):
        return self.get_image_named('logo')

    @property
    def logo_bg(self):
        return self.get_image_named('logo-bg')

    @property
    def background_layer(self):
        return [x for x in self.components if x.is_background_colored()]

    @property
    def accent_layer(self):
        return [x for x in self.components if x.is_accent_colored()]

    @property
    def text_components(self):
        return [x for x in self.components if x.type == ComponentType.TEXT]

    @property
    def editable_components(self):
        return (self.background_layer
                + self.accent_layer
                + self.text_components
                + [self.logo] if self.logo else []
                + [self.logo_bg] if self.logo_bg else [])

    @staticmethod
    def component_from_sb(name, type, **component):
        if type == 'text':
            return TextComponent(name=name)
        elif type == 'image':
            color_editable = component['imageSvgFill'] and component['url']['file']['filename'].endswith('svg')
            return ImageComponent(name=name, color_editable=color_editable)
        elif type == 'rectangle':
            return ShapeComponent(name=name)
        else:
            raise ValueError(f'Unknown switchboard component type {type}')

    @classmethod
    def from_sb(cls, name, components):
        return cls(name=name, components=[cls.component_from_sb(**c) for c in components])



class MarkyCanvas(Canvas):
    theme: str = None
    text_meta: Dict[str, TextMeta]

    @model_validator(mode='after')
    def text_meta_matches(self):
        assert self.text_meta.keys() == {x.name for x in self.text_components}, \
            'Text meta does not match text components'

    @property
    def as_db_item(self):
        item = self.model_dump()
        # merge text meta into text components
        for c in item['components']:
            if c['type'] == ComponentType.TEXT:
                c.update(self.text_meta[c['name']])

        return item
    
    @classmethod
    def from_canvas(cls, canvas: Canvas):
        text_meta = {name: TextMeta() for name in canvas.text_components}
        return cls(**canvas.dict(), theme=None, text_meta=text_meta)
    
    @classmethod
    def from_canvas_and_partial_meta(cls, canvas: Canvas, theme: Optional[str] = None, meta: Dict[str, TextMeta]):
        text_meta = {name: meta.get(name, TextMeta()) for name in canvas.text_components}
        return cls(**canvas.dict(), theme=theme, text_meta=text_meta)